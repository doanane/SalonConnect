from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from hashlib import sha256
from passlib.context import CryptContext
import bcrypt
from app.core.config import settings

# Try to use bcrypt if available, otherwise use SHA256
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    BC_AVAILABLE = True
except:
    BC_AVAILABLE = False
    print("⚠️  bcrypt not available, using SHA256")

def verify_password(plain_password: str, hashed_password: str):
    """Verify password - supports both bcrypt and SHA256"""
    if hashed_password.startswith('$2b$'):  # bcrypt hash
        if BC_AVAILABLE:
            return pwd_context.verify(plain_password, hashed_password)
        else:
            # Fallback: try bcrypt directly
            try:
                return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
            except:
                return False
    else:
        # SHA256 hash
        return sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str):
    """Hash password using SHA256 (for new users)"""
    return sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create access token only (no refresh token)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None