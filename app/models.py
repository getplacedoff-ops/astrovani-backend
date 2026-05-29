import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Date, Time, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False)
    phone_country_code = Column(String(5), nullable=False)
    email = Column(String(255), unique=True)
    full_name = Column(String(100), nullable=False)
    gender = Column(String(10))
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=False)
    birth_latitude = Column(Numeric(9, 6), nullable=False)
    birth_longitude = Column(Numeric(9, 6), nullable=False)
    birth_place_name = Column(String(150), nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    tier = Column(String(10), default="free")
    premium_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class JathakamGeneration(Base):
    __tablename__ = "jathakam_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    ayanamsa = Column(String(20), default="Lahiri")
    chart_data = Column(JSONB, nullable=False)
    pdf_url = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    view_count = Column(Integer, default=1)

class PanchangamCache(Base):
    __tablename__ = "panchangam_cache"

    calculation_date = Column(Date, primary_key=True)
    tithi_name = Column(String(50), nullable=False)
    tithi_end_time = Column(DateTime(timezone=True), nullable=False)
    vara_name = Column(String(50), nullable=False)
    nakshatra_name = Column(String(50), nullable=False)
    nakshatra_end_time = Column(DateTime(timezone=True), nullable=False)
    yoga_name = Column(String(50), nullable=False)
    yoga_end_time = Column(DateTime(timezone=True), nullable=False)
    karana_name = Column(String(50), nullable=False)
    karana_end_time = Column(DateTime(timezone=True), nullable=False)
    raw_planetary_positions = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

class MatchmakingSession(Base):
    __tablename__ = "matchmaking_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    boy_name = Column(String(100), nullable=False)
    boy_birth_date = Column(Date, nullable=False)
    boy_birth_time = Column(Time, nullable=False)
    boy_birth_lat = Column(Numeric(9, 6), nullable=False)
    boy_birth_lng = Column(Numeric(9, 6), nullable=False)
    girl_name = Column(String(100), nullable=False)
    girl_birth_date = Column(Date, nullable=False)
    girl_birth_time = Column(Time, nullable=False)
    girl_birth_lat = Column(Numeric(9, 6), nullable=False)
    girl_birth_lng = Column(Numeric(9, 6), nullable=False)
    guna_score = Column(Numeric(4, 2), nullable=False)
    compatibility_breakdown = Column(JSONB, nullable=False)
    pdf_url = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=func.now())

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    astrologer_name = Column(String(150), nullable=False)
    astrologer_title = Column(String(50), nullable=False)
    language_used = Column(String(15), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    last_interaction_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    sender = Column(String(10), nullable=False)
    raw_message = Column(String, nullable=False)
    sanitized_message = Column(String)
    flagged = Column(Boolean, default=False)
    flag_reason = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now())

class Coupon(Base):
    __tablename__ = "coupons"

    code = Column(String(50), primary_key=True)
    discount_type = Column(String(20), nullable=False)
    value = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    max_redemptions = Column(Integer, default=100000)
    current_redemptions = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())

class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    coupon_code = Column(String(50), ForeignKey("coupons.code"))
    redeemed_at = Column(DateTime(timezone=True), default=func.now())
