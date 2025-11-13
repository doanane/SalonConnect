from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Salon(Base):
    __tablename__ = "salons"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    postal_code = Column(String(20))
    phone_number = Column(String(20))
    email = Column(String(255))
    website = Column(String(500))
    opening_hours = Column(Text)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    owner = relationship("User", back_populates="salons")
    services = relationship("Service", back_populates="salon")
    bookings = relationship("Booking", back_populates="salon")
    reviews = relationship("Review", back_populates="salon")
    images = relationship("SalonImage", back_populates="salon")

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    duration = Column(Integer)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="GHS")  # CHANGED: NGN to GHS
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    salon = relationship("Salon", back_populates="services")
    booking_items = relationship("BookingItem", back_populates="service")

class SalonImage(Base):
    __tablename__ = "salon_images"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    salon = relationship("Salon", back_populates="images")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    salon = relationship("Salon", back_populates="reviews")
    customer = relationship("User")