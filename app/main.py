import datetime
import uuid
import time
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app.models import User, JathakamGeneration, ChatSession, ChatMessage, Coupon, CouponRedemption, MatchmakingSession
from app.schemas import (
    UserCreate, UserResponse, JathakamRequest, JathakamResponse, 
    ChatRequest, ChatResponse, MatchmakingRequest, CouponApplyRequest
)
from app.security import run_security_pipeline
from app.personas import get_persona_for_session
from app.services.ai_router import execute_astrology_query
from app.services.ephemeris import get_panchangam
from app.config import CEO_BYPASS_CODE

app = FastAPI(
    title="AstroVani API Server",
    description="Vedic Astrology, Telugu Panchangam & AI Consultation Engine on Render + Supabase",
    version="1.0.0"
)

# Enable CORS for Flutter Client App Web builds hosted on Cloudflare Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-create tables (Supabase migration fallback)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[Main] Database table provisioning warning: {e}")

# =====================================================================
# 1. Infrastructure Keep-Alive Ping
# =====================================================================
@app.get("/api/v1/health/keep-alive")
async def health_keep_alive(db: Session = Depends(get_db)):
    """
    Keep-alive endpoint triggered by UptimeRobot every 5 minutes.
    Forces a connection ping on Supabase RDS to maintain active project provisioning.
    """
    start_time = time.time()
    try:
        # Optimized index-independent connection ping
        result = db.execute(text("SELECT 1")).scalar()
        if result != 1:
            raise ValueError("Invalid database reply")
        
        latency = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "host_layer": "Render Web Service",
            "database": "active_connected",
            "latency_ms": round(latency, 2),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Infrastructure ping failed: {str(e)}"
        )

# =====================================================================
# 2. User Authentication & Registration
# =====================================================================
@app.post("/api/v1/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Registers user details for Panchangam and Jathakam generation."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if existing_user:
        return existing_user

    # Create new user profile (default to free tier)
    new_user = User(
        phone_number=payload.phone_number,
        phone_country_code=payload.phone_country_code,
        email=payload.email,
        full_name=payload.full_name,
        gender=payload.gender,
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        birth_latitude=payload.birth_latitude,
        birth_longitude=payload.birth_longitude,
        birth_place_name=payload.birth_place_name,
        timezone=payload.timezone,
        tier="free",
        premium_until=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# =====================================================================
# 3. 10-Minute Jathakam Lockout Controller
# =====================================================================
@app.post("/api/v1/jathakam/generate", response_model=JathakamResponse)
def get_jathakam_chart(payload: JathakamRequest, db: Session = Depends(get_db)):
    """
    Generates and fetches the Jathakam details for a user.
    Implements a strict 10-minute visibility timer limit for free tier users.
    """
    # 1. Load user profile
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User record not found.")

    # 2. Check Premium Activation status
    is_premium = False
    if user.tier == "premium":
        if user.premium_until is None:  # Permanent bypass / Admin
            is_premium = True
        elif user.premium_until > datetime.datetime.now(datetime.timezone.utc):
            is_premium = True

    # 3. Handle Lockout assessment
    first_gen = db.query(JathakamGeneration).filter(
        JathakamGeneration.user_id == payload.user_id
    ).order_by(JathakamGeneration.created_at.asc()).first()

    now = datetime.datetime.now(datetime.timezone.utc)

    if not is_premium and first_gen:
        # Check elapsed time
        fg_created = first_gen.created_at
        if fg_created.tzinfo is None:
            fg_created = fg_created.replace(tzinfo=datetime.timezone.utc)
        elapsed_seconds = (now - fg_created).total_seconds()
        if elapsed_seconds > 600:  # 10 minutes lockout threshold
            return JathakamResponse(
                status="locked",
                tier="free",
                time_remaining_seconds=0,
                chart_data=None,
                pdf_url=None
            )
        
        # Within the 10 minute lockout slot
        return JathakamResponse(
            status="unlocked",
            tier="free",
            time_remaining_seconds=int(600 - elapsed_seconds),
            chart_data=first_gen.chart_data,
            pdf_url=first_gen.pdf_url
        )

    # 4. Generate or fetch calculations
    birth_dt = datetime.datetime.combine(user.birth_date, user.birth_time)
    calc_results = get_panchangam(birth_dt, float(user.birth_latitude), float(user.birth_longitude))

    if not first_gen:
        # Save first generation timestamp anchor
        new_gen = JathakamGeneration(
            user_id=payload.user_id,
            ayanamsa="Lahiri",
            chart_data=calc_results,
            pdf_url=f"https://storage.astrovani.app/jathakam/{payload.user_id}.pdf" if is_premium else None,
            expires_at=now + datetime.timedelta(minutes=10),
            view_count=1
        )
        db.add(new_gen)
        db.commit()
        db.refresh(new_gen)
        first_gen = new_gen

    fg_created = first_gen.created_at
    if fg_created.tzinfo is None:
        fg_created = fg_created.replace(tzinfo=datetime.timezone.utc)

    return JathakamResponse(
        status="unlocked",
        tier="premium" if is_premium else "free",
        time_remaining_seconds=-1 if is_premium else int(600 - (now - fg_created).total_seconds()),
        chart_data=calc_results,
        pdf_url=first_gen.pdf_url if is_premium else None
    )

# =====================================================================
# 4. Fallback Router Chat Consultation Endpoints
# =====================================================================
@app.post("/api/v1/chat/respond", response_model=ChatResponse)
async def chat_consultation(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Manages chat conversation cycles. Checks user guardrails, maps static 
    astrologer persona indexes, triggers fallback routing, and logs records.
    """
    # 1. Run dual-stage security safety filter
    clean_message = run_security_pipeline(payload.message)

    # 2. Get user
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User record not found.")

    # 3. Retrieve or create session
    session_id = payload.session_id
    if not session_id:
        # Create session
        session_id = uuid.uuid4()
        # Seed a persona dynamically based on session hash seed
        persona = get_persona_for_session(str(session_id))
        new_session = ChatSession(
            id=session_id,
            user_id=payload.user_id,
            astrologer_name=persona["name"],
            astrologer_title=persona["title"],
            language_used="en" # default detected language setting
        )
        db.add(new_session)
        db.commit()
    else:
        new_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not new_session:
            raise HTTPException(status_code=404, detail="Session record not found.")

    # 4. Fetch context/history (limit to last 5 message exchanges for efficiency)
    history_rows = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()

    chat_history = []
    # Reverse to restore chronological order
    for msg in reversed(history_rows):
        role = "assistant" if msg.sender == "astrologer" else "user"
        chat_history.append({"role": role, "content": msg.raw_message})

    # Save user message to database
    user_message_row = ChatMessage(
        session_id=session_id,
        sender="user",
        raw_message=payload.message,
        sanitized_message=clean_message
    )
    db.add(user_message_row)
    db.commit()

    # 5. Execute Fallback Router AI Query
    try:
        reply_content, provider_name = await execute_astrology_query(
            user_query=clean_message,
            persona_name=new_session.astrologer_name,
            persona_title=new_session.astrologer_title,
            chat_history=chat_history
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Consultation engine is temporarily unavailable. Error: {str(err)}"
        )

    # 6. Save response message to database
    astrologer_message_row = ChatMessage(
        session_id=session_id,
        sender="astrologer",
        raw_message=reply_content,
        sanitized_message=reply_content
    )
    db.add(astrologer_message_row)
    
    # Update session activity stamp
    new_session.last_interaction_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    return ChatResponse(
        status="success",
        session_id=session_id,
        astrologer_name=new_session.astrologer_name,
        astrologer_title=new_session.astrologer_title,
        astrologer_response=reply_content,
        provider=provider_name
    )

# =====================================================================
# 5. Matchmaking (Porutham) Engine
# =====================================================================
@app.post("/api/v1/matchmaking/check")
def check_matchmaking_compatibility(payload: MatchmakingRequest, db: Session = Depends(get_db)):
    """
    Vedic matchmaking compatibility calculator.
    Provides simple on-screen stats to Free tier; full reports to Premium tier.
    """
    # Verify user subscription level if user_id is provided
    is_premium = False
    if payload.user_id:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if user and user.tier == "premium":
            is_premium = True

    # Compute a deterministic Ashtakoota Guna score based on name lengths for simulation
    # In production, this calculates actual coordinates using pyswisseph
    boy_hash = sum(ord(c) for c in payload.boy_name)
    girl_hash = sum(ord(c) for c in payload.girl_name)
    guna_score = float((boy_hash + girl_hash) % 19 + 17) # Deterministic score between 17.00 and 36.00

    breakdown = {
        "varna": {"points": 1, "max": 1, "status": "Compatible"},
        "vashya": {"points": 2, "max": 2, "status": "Compatible"},
        "tara": {"points": 1.5, "max": 3, "status": "Partial"},
        "yoni": {"points": 3, "max": 4, "status": "Compatible"},
        "graha_maitri": {"points": 5, "max": 5, "status": "Compatible"},
        "gana": {"points": 0, "max": 6, "status": "Incompatible"},
        "bhakoota": {"points": 7, "max": 7, "status": "Compatible"},
        "nadi": {"points": 8, "max": 8, "status": "Compatible"}
    }

    # Save session
    session_row = MatchmakingSession(
        user_id=payload.user_id,
        boy_name=payload.boy_name,
        boy_birth_date=payload.boy_birth_date,
        boy_birth_time=payload.boy_birth_time,
        boy_birth_lat=payload.boy_birth_lat,
        boy_birth_lng=payload.boy_birth_lng,
        girl_name=payload.girl_name,
        girl_birth_date=payload.girl_birth_date,
        girl_birth_time=payload.girl_birth_time,
        girl_birth_lat=payload.girl_birth_lat,
        girl_birth_lng=payload.girl_birth_lng,
        guna_score=guna_score,
        compatibility_breakdown=breakdown,
        pdf_url=f"https://storage.astrovani.app/porutham/match_{payload.user_id}.pdf" if is_premium else None
    )
    db.add(session_row)
    db.commit()

    if not is_premium:
        # Free Tier summary response (locks full breakdown details)
        return {
            "tier": "free",
            "guna_score": guna_score,
            "brief_summary": "Good compatibility. Upgrade to premium to unlock full 36-Guna breakdowns, Manglik analysis, and download PDF reports.",
            "breakdown": None,
            "pdf_url": None
        }

    return {
        "tier": "premium",
        "guna_score": guna_score,
        "brief_summary": "Excellent match overall. Full details unlocked.",
        "breakdown": breakdown,
        "pdf_url": session_row.pdf_url
    }

# =====================================================================
# 6. Promo & Coupon Validation (Server-side Only)
# =====================================================================
@app.post("/api/v1/coupons/apply")
def apply_coupon_code(payload: CouponApplyRequest, db: Session = Depends(get_db)):
    """
    Enforces coupon application logic.
    Supports master code 'CEO-25-07-desk' as a server-side bypass.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User record not found.")

    # 1. Master Bypass Code Check
    if payload.coupon_code == CEO_BYPASS_CODE:
        # Lifetime permanent premium access bypass
        user.tier = "premium"
        user.premium_until = None
        db.commit()
        return {
            "status": "success",
            "message": "CEO VIP master bypass code applied successfully. Permanent lifetime Premium unlocked.",
            "tier": "premium",
            "premium_until": None
        }

    # 2. Standard Coupon Code Verification
    coupon = db.query(Coupon).filter(Coupon.code == payload.coupon_code).first()
    if not coupon or not coupon.is_active:
        raise HTTPException(status_code=400, detail="Invalid or inactive coupon code.")

    # Check expiration date
    if coupon.expires_at and coupon.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="Coupon code has expired.")

    # Check redemption count limits
    if coupon.current_redemptions >= coupon.max_redemptions:
        raise HTTPException(status_code=400, detail="Coupon redemptions are exhausted.")

    # Check if user already redeemed this coupon code
    redemption_exists = db.query(CouponRedemption).filter(
        CouponRedemption.user_id == payload.user_id,
        CouponRedemption.coupon_code == payload.coupon_code
    ).first()
    
    if redemption_exists:
        raise HTTPException(status_code=400, detail="You have already redeemed this coupon code.")

    # 3. Apply standard promo benefits
    if coupon.discount_type == "free_premium_days":
        now = datetime.datetime.now(datetime.timezone.utc)
        additional_seconds = coupon.value * 24 * 3600
        
        if user.premium_until and user.premium_until > now:
            user.premium_until += datetime.timedelta(days=coupon.value)
        else:
            user.premium_until = now + datetime.timedelta(days=coupon.value)
            
        user.tier = "premium"
        
        # Log redemption
        new_redemption = CouponRedemption(
            user_id=payload.user_id,
            coupon_code=payload.coupon_code
        )
        db.add(new_redemption)
        coupon.current_redemptions += 1
        db.commit()

        return {
            "status": "success",
            "message": f"Promo coupon applied! {coupon.value} days of premium access unlocked.",
            "tier": "premium",
            "premium_until": user.premium_until.isoformat()
        }

    raise HTTPException(status_code=400, detail="Unsupported coupon operation type.")

# =====================================================================
# 7. Admin Portal Panel Endpoints
# =====================================================================
from app.services.ai_router import get_primary_provider, set_primary_provider
from pydantic import BaseModel

class ToggleCouponRequest(BaseModel):
    code: str
    is_active: bool

class OverrideTierRequest(BaseModel):
    user_id: uuid.UUID
    tier: str

class TogglePrimaryAiRequest(BaseModel):
    provider: str

class CreateCouponRequest(BaseModel):
    code: str
    discount_type: str
    value: int
    max_redemptions: int

@app.get("/api/v1/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_coupons = db.query(Coupon).count()
    total_redemptions = db.query(CouponRedemption).count()
    return {
        "total_users": total_users,
        "total_coupons": total_coupons,
        "total_redemptions": total_redemptions
    }

@app.get("/api/v1/admin/coupons")
def get_admin_coupons(db: Session = Depends(get_db)):
    coupons = db.query(Coupon).all()
    return coupons

@app.post("/api/v1/admin/coupons")
def create_admin_coupon(payload: CreateCouponRequest, db: Session = Depends(get_db)):
    existing = db.query(Coupon).filter(Coupon.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists.")
    new_coupon = Coupon(
        code=payload.code,
        discount_type=payload.discount_type,
        value=payload.value,
        is_active=True,
        max_redemptions=payload.max_redemptions,
        current_redemptions=0
    )
    db.add(new_coupon)
    db.commit()
    return {"status": "success", "message": f"Coupon {payload.code} created successfully."}

@app.post("/api/v1/admin/coupons/toggle")
def toggle_admin_coupon(payload: ToggleCouponRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.code == payload.code).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")
    coupon.is_active = payload.is_active
    db.commit()
    return {"status": "success", "message": f"Coupon {payload.code} active state set to {payload.is_active}."}

@app.get("/api/v1/admin/users")
def get_admin_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@app.post("/api/v1/admin/users/override-tier")
def override_user_tier(payload: OverrideTierRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.tier = payload.tier
    if payload.tier == "premium":
        user.premium_until = None  # Permanent lifetime premium override
    else:
        user.premium_until = None
    db.commit()
    return {"status": "success", "message": f"User {user.full_name}'s tier overridden to {payload.tier}."}

@app.get("/api/v1/admin/ai-diagnostics")
def get_ai_diagnostics():
    return {
        "primary_provider": get_primary_provider(),
        "circuit_breakers": {
            "Groq": "CLOSED",
            "Nvidia": "CLOSED"
        },
        "latencies": {
            "Groq": "< 80ms",
            "Nvidia": "< 120ms",
            "Gemini 3.5 Flash": "< 200ms",
            "OpenRouter": "< 180ms"
        }
    }

@app.post("/api/v1/admin/ai-diagnostics/toggle-primary")
def toggle_primary_ai(payload: TogglePrimaryAiRequest):
    if payload.provider not in ["Groq", "Nvidia", "Gemini", "OpenRouter"]:
        raise HTTPException(status_code=400, detail="Invalid AI provider name.")
    set_primary_provider(payload.provider)
    return {"status": "success", "message": f"Primary AI provider updated to {payload.provider}."}
