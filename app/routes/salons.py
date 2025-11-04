from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, and_

from app.database import get_db
from app.schemas.salon import SalonResponse, SalonCreate, ServiceResponse, ServiceCreate, ReviewResponse, ReviewCreate
from app.routes.auth import get_current_user
from app.services.salon_service import SalonService
from app.models.salon import Salon, Service
from app.models.user import user_favorites, User

router = APIRouter()

@router.get("/", response_model=List[SalonResponse])
def get_salons(
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None),
    service_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all salons with advanced search and filtering"""
    query = db.query(Salon).filter(Salon.is_active == True)
    
    # Search by name or description
    if search:
        query = query.filter(
            or_(
                Salon.name.ilike(f"%{search}%"),
                Salon.description.ilike(f"%{search}%")
            )
        )
    
    # Filter by location
    if city:
        query = query.filter(Salon.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(Salon.state.ilike(f"%{state}%"))
    
    # Filter by rating
    if min_rating:
        query = query.filter(Salon.average_rating >= min_rating)
    
    # Filter by service
    if service_name:
        query = query.join(Service).filter(
            Service.name.ilike(f"%{service_name}%"),
            Service.is_active == True
        )
    
    # Pagination
    offset = (page - 1) * limit
    salons = query.offset(offset).limit(limit).all()
    
    # Add is_favorited field
    if current_user:
        favorite_salon_ids = [row.salon_id for row in db.execute(
            user_favorites.select().where(user_favorites.c.user_id == current_user.id)
        ).fetchall()]
        
        for salon in salons:
            salon.is_favorited = salon.id in favorite_salon_ids
    else:
        for salon in salons:
            salon.is_favorited = False
    
    return salons

@router.get("/featured", response_model=List[SalonResponse])
def get_featured_salons(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get featured salons (highest rated)"""
    salons = db.query(Salon).filter(
        Salon.is_active == True,
        Salon.is_verified == True
    ).order_by(
        Salon.average_rating.desc(),
        Salon.total_reviews.desc()
    ).limit(limit).all()
    
    # Add is_favorited field
    if current_user:
        favorite_salon_ids = [row.salon_id for row in db.execute(
            user_favorites.select().where(user_favorites.c.user_id == current_user.id)
        ).fetchall()]
        
        for salon in salons:
            salon.is_favorited = salon.id in favorite_salon_ids
    else:
        for salon in salons:
            salon.is_favorited = False
    
    return salons

@router.get("/nearby", response_model=List[SalonResponse])
def get_nearby_salons(
    latitude: float = Query(..., description="User latitude"),
    longitude: float = Query(..., description="User longitude"),
    radius: float = Query(10, description="Radius in kilometers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get salons near a location"""
    # Simplified - in production, use PostGIS for accurate distance calculation
    salons = SalonService.get_nearby_salons(db, latitude, longitude, radius)
    
    # Add is_favorited field
    if current_user:
        favorite_salon_ids = [row.salon_id for row in db.execute(
            user_favorites.select().where(user_favorites.c.user_id == current_user.id)
        ).fetchall()]
        
        for salon in salons:
            salon.is_favorited = salon.id in favorite_salon_ids
    else:
        for salon in salons:
            salon.is_favorited = False
    
    return salons

@router.post("/", response_model=SalonResponse)
def create_salon(
    salon_data: SalonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new salon (vendor only)"""
    if current_user.role != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendors can create salons"
        )
    return SalonService.create_salon(db, salon_data, current_user.id)

@router.get("/{salon_id}", response_model=SalonResponse)
def get_salon(
    salon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get salon by ID"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    # Check if favorited
    if current_user:
        is_favorited = db.execute(
            user_favorites.select().where(
                and_(
                    user_favorites.c.user_id == current_user.id,
                    user_favorites.c.salon_id == salon_id
                )
            )
        ).first()
        salon.is_favorited = bool(is_favorited)
    else:
        salon.is_favorited = False
    
    return salon

@router.get("/{salon_id}/services", response_model=List[ServiceResponse])
def get_salon_services(salon_id: int, db: Session = Depends(get_db)):
    """Get services for a salon"""
    return SalonService.get_salon_services(db, salon_id)

@router.post("/{salon_id}/services", response_model=ServiceResponse)
def create_service(
    salon_id: int,
    service_data: ServiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new service for a salon (owner only)"""
    salon = SalonService.get_salon_by_id(db, salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    if salon.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create services for this salon")
    
    return SalonService.create_service(db, salon_id, service_data)

@router.get("/{salon_id}/reviews", response_model=List[ReviewResponse])
def get_salon_reviews(salon_id: int, db: Session = Depends(get_db)):
    """Get reviews for a salon"""
    return SalonService.get_salon_reviews(db, salon_id)

@router.post("/{salon_id}/reviews", response_model=ReviewResponse)
def create_review(
    salon_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review for a salon (customer only)"""
    if current_user.role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can create reviews")
    
    return SalonService.create_review(db, salon_id, current_user.id, review_data)