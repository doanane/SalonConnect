# create_tables.py (separate script)
from app.database import engine
from app.models.user import User, UserProfile
from app.models.salon import Salon, Service, Review, SalonImage
from app.models.booking import Booking, BookingItem
from app.models.payment import Payment

def create_all_tables():
    print("Creating database tables...")
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
        print(" All tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_all_tables()