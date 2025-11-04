from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class BookingItemBase(BaseModel):
    service_id: int
    quantity: int = 1

class BookingBase(BaseModel):
    salon_id: int
    booking_date: datetime
    special_requests: Optional[str] = None

class BookingCreate(BookingBase):
    items: List[BookingItemBase]

class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None
    special_requests: Optional[str] = None
    cancellation_reason: Optional[str] = None

class BookingItemResponse(BookingItemBase):
    id: int
    booking_id: int
    price: float
    duration: int
    service_name: Optional[str] = None  # Make optional
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BookingResponse(BookingBase):
    id: int
    customer_id: int
    customer_name: Optional[str] = None  # Make optional
    salon_name: Optional[str] = None     # Make optional
    duration: int
    total_amount: float
    currency: str
    status: BookingStatus
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[BookingItemResponse]

    model_config = ConfigDict(from_attributes=True)