from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class SalonBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    city: str
    state: str
    country: str
    postal_code: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None

class SalonCreate(SalonBase):
    pass

class SalonResponse(SalonBase):
    id: int
    owner_id: int
    is_active: bool
    is_verified: bool
    average_rating: float
    total_reviews: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: Optional[int] = None
    price: float

class ServiceCreate(ServiceBase):
    pass

class ServiceResponse(ServiceBase):
    id: int
    salon_id: int
    currency: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    rating: int
    comment: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewCreate(ReviewBase):
    salon_id: int

class ReviewResponse(ReviewBase):
    id: int
    salon_id: int
    customer_id: int
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True