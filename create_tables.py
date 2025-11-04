from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import os

from app.database import engine
from app.models.user import User, UserProfile
from app.models.salon import Salon, Service, Review, SalonImage
from app.models.booking import Booking, BookingItem
from app.models.payment import Payment

from app.routes import auth, users, salons, bookings, payments, vendor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only create tables in development
    if os.getenv("DEBUG", "False").lower() == "true":
        print("🛠️ Development mode - creating database tables...")
        try:
            User.metadata.create_all(bind=engine)
            UserProfile.metadata.create_all(bind=engine)
            Salon.metadata.create_all(bind=engine)
            Service.metadata.create_all(bind=engine)
            Review.metadata.create_all(bind=engine)
            SalonImage.metadata.create_all(bind=engine)
            Booking.metadata.create_all(bind=engine)
            BookingItem.metadata.create_all(bind=engine)
            Payment.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
    else:
        print("🚀 Production mode - using existing database tables")
    yield

security_scheme = HTTPBearer()

app = FastAPI(
    title="Salon Connect API",
    description="A platform connecting salons with customers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/users", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(salons.router, prefix="/api/salons", tags=["Salons"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(vendor.router, prefix="/api/vendor", tags=["Vendor Management"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Salon Connect API", 
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Salon Connect API is running"}

# For health checks
@app.get("/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)