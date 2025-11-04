from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta

from app.models.user import User, UserProfile, UserRole
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, UserProfileUpdate
from app.core.security import get_password_hash, verify_password, create_access_token, verify_token

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserCreate):
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            password=hashed_password,
            phone_number=user_data.phone_number,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        
        return UserResponse.from_orm(user)

    @staticmethod
    def login_user(db: Session, user_data: UserLogin):
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is deactivated")
        
        # Create access token only (no refresh token)
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        
        return Token(
            access_token=access_token,
            refresh_token=access_token,  # For compatibility, but we'll use only access token
            token_type="bearer"
        )

    @staticmethod
    def refresh_token(db: Session, refresh_token: str):
        """For compatibility, but we're using access tokens only"""
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Create new access token
        new_access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_access_token,  # Same as access token
            token_type="bearer"
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_profile(db: Session, user_id: int):
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    @staticmethod
    def update_user_profile(db: Session, user_id: int, profile_data: UserProfileUpdate):
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_customer_dashboard(db: Session, user_id: int):
        from app.models.booking import Booking, BookingStatus
        
        total_bookings = db.query(Booking).filter(Booking.customer_id == user_id).count()
        pending_bookings = db.query(Booking).filter(
            Booking.customer_id == user_id,
            Booking.status == BookingStatus.PENDING
        ).count()
        completed_bookings = db.query(Booking).filter(
            Booking.customer_id == user_id,
            Booking.status == BookingStatus.COMPLETED
        ).count()
        
        return {
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "completed_bookings": completed_bookings
        }

    @staticmethod
    def get_vendor_dashboard(db: Session, user_id: int):
        from app.models.salon import Salon
        from app.models.booking import Booking
        
        salons = db.query(Salon).filter(Salon.owner_id == user_id).all()
        salon_ids = [salon.id for salon in salons]
        
        total_bookings = db.query(Booking).filter(Booking.salon_id.in_(salon_ids)).count() if salon_ids else 0
        
        return {
            "total_salons": len(salons),
            "total_bookings": total_bookings
        }