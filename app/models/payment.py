from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"

class PaymentMethod(str, enum.Enum):
    PAYSTACK = "paystack"
    CASH = "cash"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    reference = Column(String(100), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="GHS")  # CHANGED: NGN to GHS
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.PAYSTACK)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    paystack_reference = Column(String(100))
    payment_data = Column(Text)
    paid_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    booking = relationship("Booking", back_populates="payment")