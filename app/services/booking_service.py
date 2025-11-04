from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
from datetime import datetime, date
from typing import Optional

from app.models.booking import Booking, BookingItem, BookingStatus
from app.models.salon import Service, Salon
from app.schemas.booking import BookingCreate, BookingUpdate

class BookingService:
    @staticmethod
    def create_booking(db: Session, booking_data: BookingCreate, customer_id: int):
        # Check if salon exists
        salon = db.query(Salon).filter(Salon.id == booking_data.salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
        # Validate services and calculate total
        total_amount = 0
        total_duration = 0
        booking_items = []
        
        for item in booking_data.items:
            service = db.query(Service).filter(
                Service.id == item.service_id,
                Service.salon_id == booking_data.salon_id,
                Service.is_active == True
            ).first()
            
            if not service:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Service with ID {item.service_id} not found"
                )
            
            item_total = service.price * item.quantity
            total_amount += item_total
            total_duration += service.duration * item.quantity
            
            booking_items.append(BookingItem(
                service_id=item.service_id,
                quantity=item.quantity,
                price=service.price,
                duration=service.duration
            ))
        
        # Create booking
        booking = Booking(
            customer_id=customer_id,
            salon_id=booking_data.salon_id,
            booking_date=booking_data.booking_date,
            duration=total_duration,
            total_amount=total_amount,
            special_requests=booking_data.special_requests
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Create booking items
        for item in booking_items:
            item.booking_id = booking.id
            db.add(item)
        
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int):
        return db.query(Booking).filter(Booking.id == booking_id).first()

    @staticmethod
    def get_user_bookings(db: Session, user_id: int, status: str = None, page: int = 1, limit: int = 10):
        query = db.query(Booking).filter(Booking.customer_id == user_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        offset = (page - 1) * limit
        return query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_vendor_bookings(db: Session, vendor_id: int, status: str = None, page: int = 1, limit: int = 10):
        query = db.query(Booking).join(Salon).filter(Salon.owner_id == vendor_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        offset = (page - 1) * limit
        return query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def update_booking(db: Session, booking_id: int, booking_data: BookingUpdate):
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        update_data = booking_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def get_vendor_bookings(db: Session, vendor_id: int, status: str = None, salon_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Get bookings for vendor's salons with advanced filtering"""
        query = db.query(Booking).join(Salon).filter(Salon.owner_id == vendor_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        if salon_id:
            query = query.filter(Booking.salon_id == salon_id)
            
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
            
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        
        return query.order_by(Booking.created_at.desc()).all()