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
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()

# Print configuration for debugging (without showing API keys)
print(f"🔧 [CONFIG] DEBUG: {settings.DEBUG}")
print(f"🔧 [CONFIG] DATABASE_URL: {settings.DATABASE_URL[:50]}...")
print(f"🔧 [CONFIG] SENDGRID_API_KEY set: {bool(settings.SENDGRID_API_KEY)}")
print(f"🔧 [CONFIG] FROM_EMAIL: {settings.FROM_EMAIL}")
print(f"🔧 [CONFIG] FRONTEND_URL: {settings.FRONTEND_URL}")