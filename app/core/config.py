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
    
    # SendGrid Email Configuration
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "anane365221@gmail.com")
    
    # Frontend URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://saloonconnect.vercel.app")
    
    # Backend URL - ADD THIS
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://salonconnect-qzne.onrender.com")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Environment detection
    RENDER_EXTERNAL_URL: str = os.getenv("RENDER_EXTERNAL_URL", "")
    
    @property
    def IS_PRODUCTION(self):
        """Check if we're running in production"""
        return bool(self.RENDER_EXTERNAL_URL)
    
    @property
    def CURRENT_BASE_URL(self):
        """Get current base URL - Use production URL"""
        if self.IS_PRODUCTION and self.RENDER_EXTERNAL_URL:
            return self.RENDER_EXTERNAL_URL.rstrip('/')
        return self.BACKEND_URL.rstrip('/')  # Use BACKEND_URL as fallback
    
    @property
    def GOOGLE_REDIRECT_URI(self):
        """Auto-generate redirect URI"""
        base_url = self.CURRENT_BASE_URL
        redirect_uri = f"{base_url}/api/users/auth/google/callback"
        print(f"🎯 [CONFIG] Using redirect URI: {redirect_uri}")
        return redirect_uri
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Print configuration for debugging
print(f"🎯 [CONFIG] Environment: {'PRODUCTION' if settings.IS_PRODUCTION else 'DEVELOPMENT'}")
print(f"🎯 [CONFIG] Current Base URL: {settings.CURRENT_BASE_URL}")
print(f"🎯 [CONFIG] Backend URL: {settings.BACKEND_URL}")
print(f"🎯 [CONFIG] Frontend URL: {settings.FRONTEND_URL}")