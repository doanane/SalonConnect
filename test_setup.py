import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    try:
        from models.user import User, UserProfile
        from models.salon import Salon, Service
        from models.booking import Booking
        from models.payment import Payment
        
        from schemas.user import UserCreate, UserResponse
        from schemas.salon import SalonCreate
        from schemas.booking import BookingCreate
        from schemas.payment import PaymentInitiate
        
        from routes.auth import router as auth_router
        from routes.users import router as users_router
        from routes.salons import router as salons_router
        from routes.bookings import router as bookings_router
        from routes.payments import router as payments_router
        
        from services.auth import AuthService
        from services.salon_service import SalonService
        from services.booking_service import BookingService
        from services.payment_service import PaymentService
        
        from core.config import settings
        from core.security import verify_password, get_password_hash
        from core.cloudinary import upload_image
        
        print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    test_imports()