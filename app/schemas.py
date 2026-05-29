from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Any, Dict
from datetime import date, time, datetime
from uuid import UUID

# --- User Schemas ---
class UserCreate(BaseModel):
    phone_number: str
    phone_country_code: str
    email: Optional[EmailStr] = None
    full_name: str
    gender: str = Field(..., pattern="^(male|female|other)$")
    birth_date: date
    birth_time: time
    birth_latitude: float
    birth_longitude: float
    birth_place_name: str
    timezone: Optional[str] = "Asia/Kolkata"

class UserResponse(BaseModel):
    id: UUID
    phone_number: str
    full_name: str
    tier: str
    premium_until: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Jathakam Schemas ---
class JathakamRequest(BaseModel):
    user_id: UUID

class JathakamResponse(BaseModel):
    status: str
    tier: str
    time_remaining_seconds: int
    chart_data: Optional[Dict[str, Any]] = None
    pdf_url: Optional[str] = None

# --- Matchmaking Schemas ---
class MatchmakingRequest(BaseModel):
    user_id: Optional[UUID] = None
    boy_name: str
    boy_birth_date: date
    boy_birth_time: time
    boy_birth_lat: float
    boy_birth_lng: float
    girl_name: str
    girl_birth_date: date
    girl_birth_time: time
    girl_birth_lat: float
    girl_birth_lng: float

# --- Chat Schemas ---
class ChatRequest(BaseModel):
    user_id: UUID
    session_id: Optional[UUID] = None
    message: str

class ChatResponse(BaseModel):
    status: str
    session_id: UUID
    astrologer_name: str
    astrologer_title: str
    astrologer_response: str
    provider: str

# --- Coupon Schemas ---
class CouponApplyRequest(BaseModel):
    user_id: UUID
    coupon_code: str
