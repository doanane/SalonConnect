from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class SalonBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    city: str
    state: str
    country: str = "Ghana"
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
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    is_active: Optional[bool] = None

class SalonResponse(SalonBase):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    average_rating: float
    total_reviews: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: int
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
    currency: str = "GHS"
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    salon_id: int
    customer_id: int
    customer_name: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SalonImageCreate(BaseModel):
    image_url: str
    is_primary: bool = False

class SalonImageResponse(BaseModel):
    id: int
    salon_id: int
    image_url: str
    is_primary: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SalonWithDetailsResponse(SalonResponse):
    services: List[ServiceResponse] = []
    reviews: List[ReviewResponse] = []
    images: List[SalonImageResponse] = []

    model_config = ConfigDict(from_attributes=True)