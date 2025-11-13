import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-key-for-development")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    PAYSTACK_BASE_URL: str = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")
    
    # SendGrid
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "anane365221@gmail.com")
    
    # URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://saloonconnect.vercel.app")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://salonconnect-qzne.onrender.com")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Render
    RENDER_EXTERNAL_URL: str = os.getenv("RENDER_EXTERNAL_URL", "")
    RENDER: bool = os.getenv("RENDER", "False").lower() == "true"
    
    @property
    def IS_PRODUCTION(self):
        return self.RENDER or bool(self.RENDER_EXTERNAL_URL)
    
    @property
    def CURRENT_BASE_URL(self):
        if self.IS_PRODUCTION and self.RENDER_EXTERNAL_URL:
            return self.RENDER_EXTERNAL_URL.rstrip('/')
        return self.BACKEND_URL.rstrip('/')
    
    @property
    def GOOGLE_REDIRECT_URI(self):
        """Get the correct Google OAuth redirect URI - MUST point to backend"""
        if self.IS_PRODUCTION:
            return "https://salonconnect-qzne.onrender.com/api/auth/google/callback"
        else:
            return "http://localhost:8000/api/auth/google/callback"

settings = Settings()

print(f" [PRODUCTION] Environment: {'PRODUCTION' if settings.IS_PRODUCTION else 'DEVELOPMENT'}")
print(f" [PRODUCTION] Backend URL: {settings.CURRENT_BASE_URL}")
print(f" [PRODUCTION] Google Redirect: {settings.GOOGLE_REDIRECT_URI}")