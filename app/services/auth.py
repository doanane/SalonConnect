from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import jwt  # ADD THIS IMPORT
from app.core.config import settings  # ADD THIS IMPORT

from app.models.user import User, UserProfile, UserRole, PendingUser, UserOTP
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, UserProfileUpdate, OTPLoginRequest, OTPVerifyRequest
from app.core.security import get_password_hash, verify_password, create_access_token, verify_token
from app.services.email import EmailService

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserCreate):
        # Check if email already exists in users or pending users
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_pending = db.query(PendingUser).filter(PendingUser.email == user_data.email).first()
        if existing_pending:
            # Resend verification email
            verification_url = f"https://salonconnect-qzne.onrender.com/api/users/verify-email?token={existing_pending.verification_token}"
            temp_user = User(
                email=existing_pending.email,
                first_name=existing_pending.first_name,
                last_name=existing_pending.last_name
            )
            EmailService.send_verification_email(temp_user, verification_url)
            raise HTTPException(status_code=400, detail="Verification email already sent. Please check your email.")
        
        # Check phone number only if provided
        if user_data.phone_number:
            existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
            if existing_phone:
                raise HTTPException(status_code=400, detail="Phone number already registered")

        hashed_password = get_password_hash(user_data.password)
        
        # Create pending user (not saved to users table yet)
        verification_token = EmailService.generate_verification_token(user_data.email)
        pending_user = PendingUser(
            email=user_data.email,
            phone_number=user_data.phone_number,
            password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            verification_token=verification_token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.add(pending_user)
        db.commit()
        db.refresh(pending_user)
        
        # Send verification email
        temp_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        verification_url = f"https://salonconnect-qzne.onrender.com/api/users/verify-email?token={verification_token}"
        EmailService.send_verification_email(temp_user, verification_url)
        
        return {"message": "Registration successful! Please check your email for verification link."}

    @staticmethod
    def verify_email(db: Session, token: str):
        """Verify user email and create actual user"""
        payload = EmailService.verify_token(token, 'email_verification')
        if not payload:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        # Find pending user by email (not by token since token is regenerated each time)
        pending_user = db.query(PendingUser).filter(
            PendingUser.email == payload['email'],
            PendingUser.expires_at > datetime.utcnow()
        ).first()
        
        if not pending_user:
            raise HTTPException(status_code=404, detail="Verification token not found or expired")
        
        # Verify the token matches
        try:
            # Decode the token from pending user to verify it matches
            pending_payload = jwt.decode(pending_user.verification_token, settings.SECRET_KEY, algorithms=['HS256'])
            if pending_payload.get('email') != payload['email']:
                raise HTTPException(status_code=400, detail="Token mismatch")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Create actual user
        user = User(
            email=pending_user.email,
            phone_number=pending_user.phone_number,
            password=pending_user.password,
            first_name=pending_user.first_name,
            last_name=pending_user.last_name,
            role=pending_user.role,
            is_verified=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create user profile
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        
        # Delete pending user
        db.delete(pending_user)
        db.commit()
        
        return user 
    
    @staticmethod
    def request_otp_login(db: Session, email: str):
        """Request OTP for login"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if user exists
            return {"message": "If the email exists, an OTP has been sent"}
        
        if not user.is_verified:
            raise HTTPException(status_code=400, detail="Please verify your email first")
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Account is deactivated")
        
        # Generate OTP
        otp = EmailService.generate_otp()
        
        # Save OTP to database
        user_otp = UserOTP(
            user_id=user.id,
            otp=otp,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        
        # Deactivate previous OTPs
        db.query(UserOTP).filter(
            UserOTP.user_id == user.id,
            UserOTP.used == False
        ).update({"used": True})
        
        db.add(user_otp)
        db.commit()
        
        # Send OTP email
        EmailService.send_otp_email(user, otp)
        
        return {"message": "OTP sent to your email"}

    @staticmethod
    def verify_otp_login(db: Session, otp_data: OTPVerifyRequest):
        """Verify OTP and login user"""
        user = db.query(User).filter(User.email == otp_data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find valid OTP
        user_otp = db.query(UserOTP).filter(
            UserOTP.user_id == user.id,
            UserOTP.otp == otp_data.otp,
            UserOTP.expires_at > datetime.utcnow(),
            UserOTP.used == False
        ).first()
        
        if not user_otp:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        # Mark OTP as used
        user_otp.used = True
        db.commit()
        
        # Generate tokens
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    @staticmethod
    def password_login(db: Session, user_data: UserLogin):
        """Traditional password login (for admin/vendors)"""
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is deactivated")
        
        if not user.is_verified:
            raise HTTPException(
                status_code=401, 
                detail="Please verify your email before logging in. Check your inbox for verification link."
            )
        
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    @staticmethod
    def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def refresh_token(db: Session, refresh_token: str):
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("user_id")
        user = AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        new_access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        return Token(access_token=new_access_token, refresh_token=refresh_token, token_type="bearer")

    @staticmethod
    def update_user_profile(db: Session, user_id: int, profile_data: UserProfileUpdate):
        """Update user profile - returns UserProfile object"""
        # Get or create user profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            # Create profile if it doesn't exist
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        # Update profile fields
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(profile)
        
        return profile  # Return UserProfile object, not User object

    @staticmethod
    def get_user_profile(db: Session, user_id: int):
        """Get user profile - returns UserProfile object"""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            # Create default profile if it doesn't exist
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        return profile  # Return UserProfile object

    @staticmethod
    def get_customer_dashboard(db: Session, user_id: int):
        """Get customer dashboard data"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get recent bookings count
        from app.models.booking import Booking
        recent_bookings_count = db.query(Booking).filter(
            Booking.customer_id == user_id
        ).count()
        
        # Get favorites count
        favorites_count = len(user.favorite_salons) if user.favorite_salons else 0
        
        return {
            "user_id": user_id,
            "user_name": f"{user.first_name} {user.last_name}",
            "total_bookings": recent_bookings_count,
            "favorite_salons_count": favorites_count,
            "recent_activity": [],
            "upcoming_appointments": []
        }

    @staticmethod
    def get_vendor_dashboard(db: Session, user_id: int):
        """Get vendor dashboard data"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get vendor's salons
        from app.models.salon import Salon
        from app.models.booking import Booking
        
        salons = db.query(Salon).filter(Salon.owner_id == user_id).all()
        total_salons = len(salons)
        
        # Get total bookings across all salons
        total_bookings = 0
        total_revenue = 0
        for salon in salons:
            salon_bookings = db.query(Booking).filter(Booking.salon_id == salon.id).all()
            total_bookings += len(salon_bookings)
            # Calculate revenue (you'll need to implement this based on your payment model)
        
        return {
            "user_id": user_id,
            "vendor_name": f"{user.first_name} {user.last_name}",
            "total_salons": total_salons,
            "total_bookings": total_bookings,
            "total_revenue": total_revenue,
            "recent_bookings": [],
            "salon_performance": []
        }