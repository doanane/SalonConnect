from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    PAYSTACK = "paystack"
    CASH = "cash"
    CARD = "card"

class PaymentBase(BaseModel):
    booking_id: int
    amount: float
    payment_method: PaymentMethod = PaymentMethod.PAYSTACK

class PaymentResponse(PaymentBase):
    id: int
    reference: str
    currency: str
    status: PaymentStatus
    paystack_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class PaymentInitiate(BaseModel):
    booking_id: int
    callback_url: Optional[str] = None


class PaymentVerification(BaseModel):
    reference: str

class WebhookData(BaseModel):
    event: str
    data: dict