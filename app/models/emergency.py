from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class EmergencyEvent(Base):
    __tablename__ = "emergency_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String)  # blood_pressure_spike, heart_rate_alert, etc.
    vital_data = Column(JSON)  # Original vital readings
    severity = Column(String)  # high, critical
    actions_taken = Column(JSON)  # Record of actions: contacted_caregiver, called_emergency, etc.
    caregiver_contacted = Column(Boolean, default=False)
    emergency_called = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="emergency_events")

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    phone_number = Column(String)
    relationship = Column(String)  # family, friend, caregiver
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="emergency_contacts")