from .auth import router as auth_router
from .users import router as users_router
from .salons import router as salons_router
from .bookings import router as bookings_router
from .payments import router as payments_router
from .vendor import router as vendor_router

__all__ = [
    "auth_router",
    "users_router", 
    "salons_router",
    "bookings_router",
    "payments_router",
    "vendor_router"
]