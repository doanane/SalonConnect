from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, OTPLoginRequest, OTPVerifyRequest
from app.services.auth import AuthService
from app.services.email import EmailService
from app.core.security import verify_token, get_password_hash
from app.models.user import User, PasswordReset, PendingUser
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()

templates = Jinja2Templates(directory="app/templates")

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

@router.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user - sends verification email"""
    try:
        result = AuthService.register_user(db, user_data)
        
        # Get the pending user to retrieve the verification token
        pending_user = db.query(PendingUser).filter(PendingUser.email == user_data.email).first()
        
        if pending_user:
            verification_url = f"http://localhost:8000/api/users/verify-email?token={pending_user.verification_token}"
            
            # For development/testing, return the token and URL in the response
            return {
                "message": "Registration successful! Please check your email for verification link.",
                "verification_token": pending_user.verification_token,
                "verification_url": verification_url,
                "instructions": "Use the verification_url above to test email verification, or use verification_token with /api/users/verify-email?token=YOUR_TOKEN"
            }
        else:
            return {
                "message": "Registration successful! But verification token not found.",
                "error": "Pending user record not created"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    """Verify user email and show success page"""
    try:
        user = AuthService.verify_email(db, token)
        return templates.TemplateResponse("email_verified.html", {"request": request})
    except Exception as e:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: red; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="error">❌ Verification Failed</div>
            <p>{str(e)}</p>
            <p><a href="http://localhost:3000/register">Try registering again</a></p>
        </body>
        </html>
        """)

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset - sends email with reset link"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "If the email exists, a password reset link will be sent."}
    
    reset_token = EmailService.generate_reset_token(user.email)
    
    password_reset = PasswordReset(
        user_id=user.id,
        token=reset_token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(password_reset)
    db.commit()
    
    reset_url = f"http://localhost:8000/api/users/reset-password-page?token={reset_token}"
    
    # For development/testing, return the token and URL in the response
    return {
        "message": "Password reset link sent to your email.",
        "reset_token": reset_token,
        "reset_url": reset_url,
        "instructions": "Use the reset_url above to test the password reset page, or use reset_token with /api/users/reset-password-page?token=YOUR_TOKEN"
    }

@router.get("/reset-password-page", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    """Serve the beautiful reset password page with token validation"""
    
    if token.startswith("b'") and token.endswith("'"):
        token = token[2:-1]
    
    payload = EmailService.verify_reset_token(token)
    if not payload:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Invalid or expired reset link. Please request a new password reset.",
            "valid_token": False
        })
    
    password_reset = db.query(PasswordReset).filter(
        PasswordReset.token == token,
        PasswordReset.expires_at > datetime.utcnow(),
        PasswordReset.used == False
    ).first()
    
    if not password_reset:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Invalid or expired reset link. Please request a new password reset.",
            "valid_token": False
        })
    
    return templates.TemplateResponse("reset_password.html", {
        "request": request, 
        "token": token,
        "valid_token": True
    })

@router.post("/reset-password")
def reset_password(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Reset password with token from form"""
    
    payload = EmailService.verify_reset_token(token)
    if not payload:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Invalid or expired reset token",
            "valid_token": False
        })
    
    user = db.query(User).filter(User.email == payload['email']).first()
    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "User not found",
            "valid_token": False
        })
    
    password_reset = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.token == token,
        PasswordReset.expires_at > datetime.utcnow(),
        PasswordReset.used == False
    ).first()
    
    if not password_reset:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Invalid or expired reset token",
            "valid_token": False
        })
    
    if new_password != confirm_password:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Passwords do not match",
            "token": token,
            "valid_token": True
        })
    
    if len(new_password) < 6:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "Password must be at least 6 characters long",
            "token": token,
            "valid_token": True
        })
    
    # Update password
    user.password = get_password_hash(new_password)
    password_reset.used = True
    db.commit()
    
    # Return the success page
    return templates.TemplateResponse("password_reset_success.html", {
        "request": request
    })

@router.post("/resend-verification")
def resend_verification(email: str, db: Session = Depends(get_db)):
    """Resend email verification"""
    pending_user = db.query(PendingUser).filter(PendingUser.email == email).first()
    if not pending_user:
        return {"message": "If you have an account, a verification link has been sent to your email."}
    
    existing_user = db.query(User).filter(User.email == email, User.is_verified == True).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    temp_user = User(
        email=pending_user.email,
        first_name=pending_user.first_name,
        last_name=pending_user.last_name
    )
    verification_url = f"http://localhost:8000/api/users/verify-email?token={pending_user.verification_token}"
    EmailService.send_verification_email(temp_user, verification_url)
    
    return {"message": "Verification email sent successfully"}

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Password login (mainly for admin/vendors)"""
    try:
        return AuthService.password_login(db, user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/login/otp/request")
def request_otp_login(request: OTPLoginRequest, db: Session = Depends(get_db)):
    """Request OTP for login"""
    try:
        return AuthService.request_otp_login(db, request.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login/otp/verify", response_model=Token)
def verify_otp_login(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify OTP and login"""
    try:
        return AuthService.verify_otp_login(db, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify token validity - FIXED: Extract token from credentials"""
    token = credentials.credentials  # Extract the token string from credentials
    payload = verify_token(token)    # Pass the token string to verify_token
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