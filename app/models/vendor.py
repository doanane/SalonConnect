# app/models/vendor.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey  # Added Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class VendorBusinessInfo(Base):
    """Store vendor business information"""
    __tablename__ = "vendor_business_info"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    business_phone = Column(String(20), nullable=False)
    business_address = Column(Text, nullable=False)
    business_city = Column(String(100), nullable=False)
    business_state = Column(String(100), nullable=False)
    business_country = Column(String(100), nullable=False)
    business_description = Column(Text)
    business_website = Column(String(500))
    tax_id = Column(String(100))
    business_registration_number = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VendorDocument(Base):
    """Store vendor verification documents"""
    __tablename__ = "vendor_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_type = Column(String(50))
    document_url = Column(String(500), nullable=False)
    verified = Column(Boolean, default=False)  # Now Boolean is imported
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())