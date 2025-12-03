# # create_tables.py
# import sys
# import os

# # Add the parent directory to the Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from app.database import engine, Base
# from app.models.user import User, UserProfile, PasswordReset, PendingUser, UserOTP
# from app.models.salon import Salon, Service, SalonImage, Review
# from app.models.booking import Booking, BookingItem
# from app.models.payment import Payment
# import traceback

# def create_all_tables():
#     try:
#         print("Creating database tables...")
        
#         # Import all models to ensure they're registered with Base.metadata
#         from app import models
        
#         # Create all tables at once using Base.metadata
#         Base.metadata.create_all(bind=engine)
        
#         print("All tables created successfully!")
#         print("Tables created:")
#         for table_name in Base.metadata.tables.keys():
#             print(f"   - {table_name}")
#         return True
#     except Exception as e:
#         print(f" Error creating tables: {e}")
#         traceback.print_exc()
#         return False

# if __name__ == "__main__":
#     success = create_all_tables()
#     if success:
#         print("Database setup completed!")
#         sys.exit(0)
#     else:
#         print("Database setup failed!")
#         sys.exit(1)