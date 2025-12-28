from .user import User, UserProfile, PasswordReset, UserRole, user_favorites, PendingUser, UserOTP
from .salon import Salon, Service, SalonImage, Review
from .booking import Booking, BookingItem, BookingStatus
from .payment import Payment, PaymentStatus, PaymentMethod
from .vendor import VendorBusinessInfo, VendorKYC, IDType, KYCStatus  # <--- Added this line

from sqlalchemy.orm import configure_mappers
configure_mappers()

__all__ = [
    "User", "UserProfile", "PasswordReset", "UserRole", "user_favorites", "PendingUser", "UserOTP",
    "Salon", "Service", "SalonImage", "Review",
    "Booking", "BookingItem", "BookingStatus", 
    "Payment", "PaymentStatus", "PaymentMethod",
    "VendorBusinessInfo", "VendorKYC", "IDType", "KYCStatus" 
]