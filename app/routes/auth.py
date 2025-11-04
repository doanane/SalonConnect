from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # Add this import
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from app.services.auth import AuthService
from app.services.email import EmailService
from app.core.security import verify_token, get_password_hash
from app.models.user import User, PasswordReset
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("user_id")
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        return AuthService.register_user(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    try:
        return AuthService.login_user(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token
    reset_token = EmailService.generate_reset_token(user.email)
    
    # Save to database
    password_reset = PasswordReset(
        user_id=user.id,
        token=reset_token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(password_reset)
    db.commit()
    
    # Send email
    EmailService.send_password_reset_email(user.email, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token"""
    # Verify token
    payload = EmailService.verify_reset_token(request.token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Find user and valid reset token
    user = db.query(User).filter(User.email == payload['email']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    password_reset = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.token == request.token,
        PasswordReset.expires_at > datetime.utcnow(),
        PasswordReset.used == False
    ).first()
    
    if not password_reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password
    user.password = get_password_hash(request.new_password)
    password_reset.used = True
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    from app.core.security import verify_password
    
    if not verify_password(request.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.password = get_password_hash(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.post("/token/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token"""
    try:
        return AuthService.refresh_token(db, refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.get("/token/verify")
def verify_token_endpoint(token: str = Depends(security)):
    """Verify token validity"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return {"valid": True, "user_id": payload.get("user_id")}

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should remove tokens)"""
    return {"message": "Successfully logged out"}