from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    booking_date = Column(DateTime, nullable=False)
    duration = Column(Integer)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="GHS")  # CHANGED: NGN to GHS
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    special_requests = Column(Text)
    cancellation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    customer = relationship("User", back_populates="bookings")
    salon = relationship("Salon", back_populates="bookings")
    items = relationship("BookingItem", back_populates="booking")
    payment = relationship("Payment", back_populates="booking", uselist=False)

class BookingItem(Base):
    __tablename__ = "booking_items"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    duration = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    booking = relationship("Booking", back_populates="items")
    service = relationship("Service", back_populates="booking_items")