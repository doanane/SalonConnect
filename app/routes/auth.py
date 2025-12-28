from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth import AuthService  
from app.schemas.user import CustomerRegister, VendorRegister
from app.models.vendor import VendorBusinessInfo
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.google_oauth import GoogleOAuthService
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, OTPLoginRequest, OTPVerifyRequest
from app.services.email import EmailService
from app.core.security import verify_token, get_password_hash, create_access_token, verify_password
from app.models.user import User, PasswordReset, PendingUser, UserOTP
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()

templates = Jinja2Templates(directory="app/templates")


BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://salonconnect-qzne.onrender.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://saloonconnect.vercel.app")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user
from app.schemas.user import CustomerRegister, VendorRegister

@router.post("/register/customer")
def register_customer(customer_data: CustomerRegister, db: Session = Depends(get_db)):
    """Register a new customer"""
    return AuthService.register_customer(db, customer_data)

@router.post("/register/vendor")
def register_vendor(vendor_data: VendorRegister, db: Session = Depends(get_db)):
    """Register a new vendor with business information"""
    return AuthService.register_vendor(db, vendor_data)

@router.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user - sends verification email"""
    try:
        print(f" [AUTH] Registration attempt for: {user_data.email}")
        
        
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_pending = db.query(PendingUser).filter(PendingUser.email == user_data.email).first()
        if existing_pending:
        
            verification_url = f"{BASE_URL}/api/users/verify-email?token={existing_pending.verification_token}"
            temp_user = User(
                email=existing_pending.email,
                first_name=existing_pending.first_name,
                last_name=existing_pending.last_name
            )
            email_sent = EmailService.send_verification_email(temp_user, verification_url)
            raise HTTPException(status_code=400, detail="Verification email already sent. Please check your email.")
        
    
        if user_data.phone_number:
            existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
            if existing_phone:
                raise HTTPException(status_code=400, detail="Phone number already registered")

        hashed_password = get_password_hash(user_data.password)
        
    
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
        
    
        temp_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        verification_url = f"{BASE_URL}/api/users/verify-email?token={verification_token}"
        email_sent = EmailService.send_verification_email(temp_user, verification_url)
        
        return {
            "message": "Registration successful! Please check your email for verification link.",
            "email_sent": email_sent,
            "debug_info": {
                "verification_url": verification_url,
                "email": user_data.email
            } if os.getenv("DEBUG") == "True" else None
        }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )

@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    """Verify user email and show success page"""
    try:
        print(f" [AUTH] Email verification attempt with token: {token[:50]}...")
        
        payload = EmailService.verify_token(token, 'email_verification')
        if not payload:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
    
        pending_user = db.query(PendingUser).filter(
            PendingUser.email == payload['email'],
            PendingUser.expires_at > datetime.utcnow()
        ).first()
        
        if not pending_user:
            raise HTTPException(status_code=404, detail="Verification token not found or expired")
        
    
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
        
    
    
        if user.role == UserRole.VENDOR:
        
            from app.models.vendor import VendorBusinessInfo
            business_info = db.query(VendorBusinessInfo).filter(
                VendorBusinessInfo.email == user.email
            ).first()
            
            if business_info:
            
                from app.models.salon import Salon
                initial_salon = Salon(
                    owner_id=user.id,
                    name=business_info.business_name,
                    address=business_info.business_address,
                    city=business_info.business_city,
                    state=business_info.business_state,
                    country=business_info.business_country,
                    phone_number=business_info.business_phone,
                    email=user.email,
                    is_active=True
                )
                db.add(initial_salon)
                db.commit()
                
                print(f"Created initial salon for vendor: {user.email}")
        
    
        db.delete(pending_user)
        db.commit()
    
        
        print(f" [AUTH] Email verified successfully for: {user.email}")
        return templates.TemplateResponse("email_verified.html", {"request": request})
        
    except Exception as e:
        print(f"[AUTH] Email verification error: {str(e)}")
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
            <div class="error">Verification Failed</div>
            <p>{str(e)}</p>
            <p><a href="{FRONTEND_URL}/register">Try registering again</a></p>
        </body>
        </html>
        """)

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset - sends email with reset link"""
    try:
        print(f" [AUTH] Forgot password attempt for: {request.email}")
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            print(f" [AUTH] User not found for email: {request.email}")
            return {"message": "If the email exists, a password reset link will be sent."}
        
        reset_token = EmailService.generate_reset_token(user.email)
        
        
        password_reset = PasswordReset(
            user_id=user.id,
            token=reset_token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(password_reset)
        db.commit()
        
        reset_url = f"{BASE_URL}/api/users/reset-password-page?token={reset_token}"
        
        
        email_sent = EmailService.send_password_reset_email(user, reset_url)
        print(f"[AUTH] Password reset email sent status: {email_sent}")
        
        return {
            "message": "Password reset link sent to your email.",
            "email_sent": email_sent,
            "debug_info": {
                "reset_url": reset_url,
                "email": request.email
            } if os.getenv("DEBUG") == "True" else None
        }
            
    except Exception as e:
        print(f"[AUTH] Forgot password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reset-password-page", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    """Serve the beautiful reset password page with token validation"""
    try:
        print(f" [AUTH] Reset password page access with token: {token[:50]}...")
        
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
        
    except Exception as e:
        print(f"[AUTH] Reset password page error: {str(e)}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "An error occurred. Please try again.",
            "valid_token": False
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
    try:
        print(f" [AUTH] Password reset attempt with token: {token[:50]}...")
        
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
        
        
        user.password = get_password_hash(new_password)
        password_reset.used = True
        db.commit()
        
        print(f" [AUTH] Password reset successful for user: {user.email}")
        
        
        return templates.TemplateResponse("password_reset_success.html", {
            "request": request
        })
        
    except Exception as e:
        print(f"[AUTH] Password reset error: {str(e)}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "error": "An error occurred. Please try again.",
            "valid_token": False
        })

@router.post("/resend-verification")
def resend_verification(email: str, db: Session = Depends(get_db)):
    """Resend email verification"""
    try:
        print(f" [AUTH] Resend verification attempt for: {email}")
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
        verification_url = f"{BASE_URL}/api/users/verify-email?token={pending_user.verification_token}"
        
        
        email_sent = EmailService.send_verification_email(temp_user, verification_url)
        print(f"[AUTH] Resend verification email sent status: {email_sent}")
        
        return {
            "message": "Verification email sent successfully",
            "email_sent": email_sent
        }
    except Exception as e:
        print(f"[AUTH] Resend verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Password login"""
    try:
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
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Login failed")

@router.post("/login/otp/request")
def request_otp_login(request: OTPLoginRequest, db: Session = Depends(get_db)):
    """Request OTP for login"""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            
            return {"message": "If the email exists, an OTP has been sent"}
        
        if not user.is_verified:
            raise HTTPException(status_code=400, detail="Please verify your email first")
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Account is deactivated")
        
        
        otp = EmailService.generate_otp()
        
        
        user_otp = UserOTP(
            user_id=user.id,
            otp=otp,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        
        
        db.query(UserOTP).filter(
            UserOTP.user_id == user.id,
            UserOTP.used == False
        ).update({"used": True})
        
        db.add(user_otp)
        db.commit()
        
        
        email_sent = EmailService.send_otp_email(user, otp)
        
        return {
            "message": "OTP sent to your email",
            "email_sent": email_sent
        }
    except Exception as e:
        print(f"[AUTH] OTP request error: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to send OTP")

@router.post("/login/otp/verify", response_model=Token)
def verify_otp_login(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify OTP and login"""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        
        user_otp = db.query(UserOTP).filter(
            UserOTP.user_id == user.id,
            UserOTP.otp == request.otp,
            UserOTP.expires_at > datetime.utcnow(),
            UserOTP.used == False
        ).first()
        
        if not user_otp:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        
        user_otp.used = True
        db.commit()
        
        
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    except Exception as e:
        print(f"[AUTH] OTP verify error: {str(e)}")
        raise HTTPException(status_code=400, detail="OTP verification failed")

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    try:
        if not verify_password(request.current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        current_user.password = get_password_hash(request.new_password)
        db.commit()
        
        return {"message": "Password changed successfully"}
    except Exception as e:
        print(f"[AUTH] Change password error: {str(e)}")
        raise HTTPException(status_code=400, detail="Password change failed")

@router.post("/token/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token"""
    try:
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        new_access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        return Token(access_token=new_access_token, refresh_token=refresh_token, token_type="bearer")
    except Exception as e:
        print(f"[AUTH] Token refresh error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token refresh failed")

@router.get("/token/verify")
def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify token validity"""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return {"valid": True, "user_id": payload.get("user_id")}
    except Exception as e:
        print(f"[AUTH] Token verify error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should remove tokens)"""
    return {"message": "Successfully logged out"}
@router.get("/debug-env")
def debug_environment():
    """Debug environment variables on Render"""
    import os
    
    env_vars = {
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_PORT": os.getenv("SMTP_PORT"), 
        "SMTP_USER": os.getenv("SMTP_USER"),
        "FROM_EMAIL": os.getenv("FROM_EMAIL"),
        "SMTP_PASS_SET": bool(os.getenv("SMTP_PASS")),
        "SMTP_PASS_LENGTH": len(os.getenv("SMTP_PASS", "")),
        "DEBUG": os.getenv("DEBUG"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT"),
        "RENDER": os.getenv("RENDER"),
        "RENDER_EXTERNAL_URL": os.getenv("RENDER_EXTERNAL_URL")
    }
    
    print(f" [ENV DEBUG] Environment variables: {env_vars}")
    
    return env_vars

@router.get("/debug-email")
def debug_email_config():
    """Debug endpoint to check email configuration"""
    import os
    from app.core.config import settings
    
    config_info = {
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "SMTP_USER": settings.SMTP_USER,
        "FROM_EMAIL": settings.FROM_EMAIL,
        "SMTP_PASS_SET": bool(settings.SMTP_PASS),
        "DEBUG": settings.DEBUG,
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "unknown")
    }
    
    print(f" [DEBUG] Email Configuration: {config_info}")
    
    
    try:
        import smtplib
        print(f" [DEBUG] Testing SMTP connection to {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            print(f" [DEBUG] SMTP connection successful")
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            print(f" [DEBUG] SMTP login successful")
            config_info["smtp_test"] = "SUCCESS"
    except Exception as e:
        print(f"[DEBUG] SMTP test failed: {str(e)}")
        config_info["smtp_test"] = f"FAILED: {str(e)}"
    
    return config_info


