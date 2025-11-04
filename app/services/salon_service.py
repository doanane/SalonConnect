from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import and_

from app.models.salon import Salon, Service, Review
from app.schemas.salon import SalonCreate, ServiceCreate, ReviewCreate

# Salon Service
class SalonService:
    @staticmethod
    def get_salons(db: Session, city: str = None, page: int = 1, limit: int = 10):
        """Get all salons with optional filtering"""
        query = db.query(Salon).filter(Salon.is_active == True)
        
        if city:
            query = query.filter(Salon.city.ilike(f"%{city}%"))

        
        # Pagination
        offset = (page - 1) * limit
        salons = query.offset(offset).limit(limit).all()
        return salons

    @staticmethod
    def get_nearby_salons(db: Session, latitude: float, longitude: float, radius: float = 10):
        """Get salons near a location (simplified version)"""
        # This is a simplified version - in production, use PostGIS or similar
        return db.query(Salon).filter(Salon.is_active == True).all()

    @staticmethod
    def create_salon(db: Session, salon_data: SalonCreate, owner_id: int):
        """Create a new salon"""
        salon = Salon(**salon_data.dict(), owner_id=owner_id)
        db.add(salon)
        db.commit()
        db.refresh(salon)
        return salon

    @staticmethod
    def get_salon_by_id(db: Session, salon_id: int):
        """Get salon by ID"""
        return db.query(Salon).filter(Salon.id == salon_id).first()

    @staticmethod
    def update_salon(db: Session, salon_id: int, salon_data: dict):
        """Update salon information"""
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        for field, value in salon_data.items():
            if hasattr(salon, field) and value is not None:
                setattr(salon, field, value)
        
        db.commit()
        db.refresh(salon)
        return salon

    @staticmethod
    def get_salon_services(db: Session, salon_id: int):
        """Get services for a salon"""
        return db.query(Service).filter(
            Service.salon_id == salon_id,
            Service.is_active == True
        ).all()

    @staticmethod
    def create_service(db: Session, salon_id: int, service_data: ServiceCreate):
        """Create a new service for a salon"""
        service = Service(**service_data.dict(), salon_id=salon_id)
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def get_salon_reviews(db: Session, salon_id: int):
        """Get reviews for a salon"""
        return db.query(Review).filter(
            Review.salon_id == salon_id,
            Review.is_approved == True
        ).all()

    @staticmethod
    def create_review(db: Session, salon_id: int, customer_id: int, review_data: ReviewCreate):
        """Create a review for a salon"""
        # Check if salon exists
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        # Check if user has already reviewed this salon
        existing_review = db.query(Review).filter(
            Review.salon_id == salon_id,
            Review.customer_id == customer_id
        ).first()
        
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this salon"
            )
        
        review = Review(**review_data.dict(), salon_id=salon_id, customer_id=customer_id)
        db.add(review)
        
        # Update salon rating
        salon_reviews = db.query(Review).filter(Review.salon_id == salon_id).all()
        total_rating = sum([r.rating for r in salon_reviews]) + review_data.rating
        salon.total_reviews = len(salon_reviews) + 1
        salon.average_rating = total_rating / salon.total_reviews
        
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def get_user_salons(db: Session, user_id: int):
        """Get salons owned by a user"""
        return db.query(Salon).filter(Salon.owner_id == user_id).all()