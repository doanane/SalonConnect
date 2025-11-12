from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy import func, and_

from app.models.salon import Salon, Service, Review, SalonImage
from app.models.user import User
from app.schemas.salon import SalonCreate, SalonUpdate, ServiceCreate, ServiceUpdate, ReviewCreate

class SalonService:
    @staticmethod
    def create_salon(db: Session, salon_data: SalonCreate, owner_id: int):
        """Create a new salon"""
        try:
            salon = Salon(
                **salon_data.dict(),
                owner_id=owner_id
            )
            
            db.add(salon)
            db.commit()
            db.refresh(salon)
            return salon
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating salon: {str(e)}"
            )

    @staticmethod
    def get_salon_by_id(db: Session, salon_id: int):
        """Get salon by ID with all relationships"""
        return db.query(Salon).options(
            joinedload(Salon.owner),
            joinedload(Salon.services),
            joinedload(Salon.reviews).joinedload(Review.customer),
            joinedload(Salon.images)
        ).filter(Salon.id == salon_id).first()

    @staticmethod
    def get_all_salons(db: Session, skip: int = 0, limit: int = 100, city: Optional[str] = None):
        """Get all salons with filtering"""
        query = db.query(Salon).options(
            joinedload(Salon.owner),
            joinedload(Salon.services),
            joinedload(Salon.images)
        ).filter(Salon.is_active == True)
        
        if city:
            query = query.filter(Salon.city.ilike(f"%{city}%"))
        
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_salon(db: Session, salon_id: int, salon_data: SalonUpdate):
        """Update salon information"""
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        update_data = salon_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(salon, field, value)
        
        db.commit()
        db.refresh(salon)
        return salon

    @staticmethod
    def delete_salon(db: Session, salon_id: int, owner_id: int):
        """Soft delete a salon"""
        salon = db.query(Salon).filter(
            Salon.id == salon_id,
            Salon.owner_id == owner_id
        ).first()
        
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        salon.is_active = False
        db.commit()
        return {"message": "Salon deleted successfully"}

    @staticmethod
    def create_service(db: Session, salon_id: int, service_data: ServiceCreate):
        """Create a new service for a salon"""
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        try:
            service = Service(
                **service_data.dict(),
                salon_id=salon_id,
                currency="GHS"
            )
            
            db.add(service)
            db.commit()
            db.refresh(service)
            return service
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating service: {str(e)}"
            )

    @staticmethod
    def update_service(db: Session, service_id: int, service_data: ServiceUpdate):
        """Update service information"""
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        update_data = service_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)
        
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def delete_service(db: Session, service_id: int):
        """Soft delete a service"""
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        service.is_active = False
        db.commit()
        return {"message": "Service deleted successfully"}

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
        
        # Validate rating
        if review_data.rating < 1 or review_data.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        
        try:
            # Create review - explicitly pass all fields
            review = Review(
                salon_id=salon_id,
                customer_id=customer_id,
                rating=review_data.rating,
                comment=review_data.comment
            )
            
            db.add(review)
            db.commit()
            db.refresh(review)
            
            # Update salon's average rating and total reviews
            SalonService.update_salon_ratings(db, salon_id)
            
            return review
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating review: {str(e)}"
            )

    @staticmethod
    def update_salon_ratings(db: Session, salon_id: int):
        """Update salon's average rating and total reviews count"""
        try:
            # Calculate new average rating and total reviews
            result = db.query(
                func.avg(Review.rating).label('avg_rating'),
                func.count(Review.id).label('total_reviews')
            ).filter(
                Review.salon_id == salon_id,
                Review.is_approved == True
            ).first()
            
            salon = db.query(Salon).filter(Salon.id == salon_id).first()
            if salon and result.avg_rating:
                salon.average_rating = round(float(result.avg_rating), 2)
                salon.total_reviews = result.total_reviews
                db.commit()
                
        except Exception as e:
            print(f"Error updating salon ratings: {e}")
            db.rollback()

    @staticmethod
    def get_salon_reviews(db: Session, salon_id: int, skip: int = 0, limit: int = 50):
        """Get reviews for a specific salon"""
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        return db.query(Review).options(
            joinedload(Review.customer)
        ).filter(
            Review.salon_id == salon_id,
            Review.is_approved == True
        ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def add_salon_image(db: Session, salon_id: int, image_url: str, is_primary: bool = False):
        """Add an image to a salon"""
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        try:
            # If setting as primary, unset existing primary images
            if is_primary:
                db.query(SalonImage).filter(
                    SalonImage.salon_id == salon_id,
                    SalonImage.is_primary == True
                ).update({"is_primary": False})
            
            image = SalonImage(
                salon_id=salon_id,
                image_url=image_url,
                is_primary=is_primary
            )
            
            db.add(image)
            db.commit()
            db.refresh(image)
            return image
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding image: {str(e)}"
            )

    @staticmethod
    def get_vendor_salons(db: Session, vendor_id: int):
        """Get all salons owned by a vendor"""
        return db.query(Salon).options(
            joinedload(Salon.services),
            joinedload(Salon.images),
            joinedload(Salon.reviews)
        ).filter(
            Salon.owner_id == vendor_id,
            Salon.is_active == True
        ).order_by(Salon.created_at.desc()).all()

    @staticmethod
    def search_salons(db: Session, query: str, city: Optional[str] = None, skip: int = 0, limit: int = 50):
        """Search salons by name, description, or service"""
        search_query = f"%{query}%"
        
        # Search in salon names, descriptions, and service names
        salon_results = db.query(Salon).options(
            joinedload(Salon.services),
            joinedload(Salon.images)
        ).filter(
            Salon.is_active == True,
            and_(
                Salon.is_active == True,
                or_(
                    Salon.name.ilike(search_query),
                    Salon.description.ilike(search_query),
                    Salon.city.ilike(search_query)
                )
            )
        )
        
        if city:
            salon_results = salon_results.filter(Salon.city.ilike(f"%{city}%"))
        
        return salon_results.offset(skip).limit(limit).all()