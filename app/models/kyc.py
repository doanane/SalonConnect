from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class VendorKYC(Base):
    """KYC verification for vendors"""
    __tablename__ = "vendor_kyc"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Document Information
    id_type = Column(String(50))  # ghana_card, passport, drivers_license
    id_number = Column(String(100))
    full_name = Column(String(200))
    date_of_birth = Column(DateTime)
    
    # Document URLs
    id_front_url = Column(String(500))
    id_back_url = Column(String(500))
    selfie_url = Column(String(500))
    
    # Verification Results
    face_match_score = Column(Float)  # 0-1 similarity score
    face_match_status = Column(String(20))  # pending, verified, failed
    document_verification_status = Column(String(20))  # pending, verified, rejected
    ocr_extracted_data = Column(JSON)  # Raw OCR data
    
    # AI/ML Analysis
    is_document_valid = Column(Boolean, default=False)
    is_live_selfie = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)  # 0-1 risk assessment
    ai_analysis = Column(JSON)  # Detailed AI analysis
    
    # Status & Timestamps
    status = Column(String(20), default="pending")  # pending, processing, approved, rejected
    rejection_reason = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor = relationship("User", foreign_keys=[vendor_id], back_populates="kyc_data")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

class KYCAuditLog(Base):
    """Audit log for KYC actions"""
    __tablename__ = "kyc_audit_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    kyc_id = Column(Integer, ForeignKey("vendor_kyc.id"))
    action = Column(String(50))  # submitted, verified, rejected, etc.
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    details = Column(JSON)
    
    # Relationships
    kyc = relationship("VendorKYC")
    user = relationship("User", foreign_keys=[performed_by])