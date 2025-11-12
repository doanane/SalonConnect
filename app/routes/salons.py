from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.salon import (
    SalonResponse, SalonCreate, SalonUpdate, 
    ServiceResponse, ServiceCreate, ServiceUpdate,
    ReviewResponse, ReviewCreate,
    SalonImageResponse, SalonWithDetailsResponse
)
from app.routes.users import get_current_user
from app.services.salon_service import SalonService
from app.core.cloudinary import upload_image

router = APIRouter()

# Salon Routes
@router.get("/", response_model=List[SalonResponse])
def get_salons(
    city: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all salons with optional city filter"""
    return SalonService.get_all_salons(db, skip, limit, city)

@router.post("/", response_model=SalonResponse)
def create_salon(
    salon_data: SalonCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new salon (vendor only)"""
    if current_user.role.value != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendors can create salons"
        )
    
    return SalonService.create_salon(db, salon_data, current_user.id)

@router.get("/{salon_id}", response_model=SalonWithDetailsResponse)
def get_salon(
    salon_id: int,
    db: Session = Depends(get_db)
):
    """Get salon by ID with all details"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    return salon

@router.put("/{salon_id}", response_model=SalonResponse)
def update_salon(
    salon_id: int,
    salon_data: SalonUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update salon information (owner only)"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    if salon.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this salon"
        )
    
    return SalonService.update_salon(db, salon_id, salon_data)

@router.delete("/{salon_id}")
def delete_salon(
    salon_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a salon (owner only)"""
    return SalonService.delete_salon(db, salon_id, current_user.id)

# Service Routes
@router.post("/{salon_id}/services", response_model=ServiceResponse)
def create_service(
    salon_id: int,
    service_data: ServiceCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new service for a salon (owner only)"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    if salon.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add services to this salon"
        )
    
    return SalonService.create_service(db, salon_id, service_data)

@router.put("/services/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update service information (owner only)"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    salon = SalonService.get_salon_by_id(db, service.salon_id)
    if salon.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this service"
        )
    
    return SalonService.update_service(db, service_id, service_data)

@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a service (owner only)"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    salon = SalonService.get_salon_by_id(db, service.salon_id)
    if salon.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this service"
        )
    
    return SalonService.delete_service(db, service_id)

# Review Routes
@router.post("/{salon_id}/reviews", response_model=ReviewResponse)
def create_review(
    salon_id: int,
    review_data: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review for a salon (customers only)"""
    if current_user.role.value != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create reviews"
        )
    
    return SalonService.create_review(db, salon_id, current_user.id, review_data)

@router.get("/{salon_id}/reviews", response_model=List[ReviewResponse])
def get_salon_reviews(
    salon_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get reviews for a specific salon"""
    return SalonService.get_salon_reviews(db, salon_id, skip, limit)

# Image Routes
@router.post("/{salon_id}/images", response_model=SalonImageResponse)
async def add_salon_image(
    salon_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an image to a salon (owner only)"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    if salon.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add images to this salon"
        )
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        result = upload_image(file.file, folder="salon_connect/salons")
        image_url = result.get('secure_url')
        
        return SalonService.add_salon_image(db, salon_id, image_url, is_primary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

# Vendor-specific Routes
@router.get("/vendor/my-salons", response_model=List[SalonResponse])
def get_vendor_salons(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all salons owned by the current vendor"""
    if current_user.role.value != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendors can access this endpoint"
        )
    
    return SalonService.get_vendor_salons(db, current_user.id)