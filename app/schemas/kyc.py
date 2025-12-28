from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class IDType(str, Enum):
    GHANA_CARD = "ghana_card"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"

class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ExtractedIDData(BaseModel):
    """Data extracted from the uploaded ID card via OCR"""
    id_number: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    document_type: Optional[str] = None
    raw_text: Optional[str] = None # Debugging

class KYCSubmission(BaseModel):
    """User confirms this data after auto-fill"""
    id_type: IDType
    id_number: str
    full_name: str
    date_of_birth: str
    
    # URLs returned from the file upload step
    id_front_url: str
    id_back_url: str
    selfie_url: str

class KYCResponse(BaseModel):
    id: int
    vendor_id: int
    status: KYCStatus
    id_type: IDType
    rejection_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True