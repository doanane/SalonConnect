from pydantic import BaseModel, validator
from typing import Optional, List
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

class SalonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None

class SalonResponse(SalonBase):
    id: int
    owner_id: int
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_active: bool
    is_verified: bool
    average_rating: float
    total_reviews: int
    is_favorited: bool = False
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

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None

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
    customer_name: str
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SalonSearch(BaseModel):
    query: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    min_rating: Optional[float] = None
    service_name: Optional[str] = None