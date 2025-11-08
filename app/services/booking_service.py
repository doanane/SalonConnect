from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from fastapi import HTTPException, status
from datetime import datetime, date
from typing import Optional

from app.models.booking import Booking, BookingItem, BookingStatus
from app.models.salon import Service, Salon
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.email import EmailService

class BookingService:
    @staticmethod
    def create_booking(db: Session, booking_data: BookingCreate, customer_id: int):
        salon = db.query(Salon).filter(Salon.id == booking_data.salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salon not found"
            )
        
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
        
        # Reload booking with relationships for response
        booking = db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.salon),
            joinedload(Booking.items).joinedload(BookingItem.service)
        ).filter(Booking.id == booking.id).first()
        
        # Send booking confirmation email to customer
        EmailService.send_booking_confirmation(booking.customer, booking, salon)
        
        # Send booking notification to vendor
        vendor = db.query(User).filter(User.id == salon.owner_id).first()
        if vendor:
            EmailService.send_booking_notification_to_vendor(vendor, booking, booking.customer, salon)
        
        return booking


    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int):
        return db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.salon),
            joinedload(Booking.items).joinedload(BookingItem.service)
        ).filter(Booking.id == booking_id).first()

    @staticmethod
    def get_user_bookings(db: Session, user_id: int, status: str = None, page: int = 1, limit: int = 10):
        query = db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.salon),
            joinedload(Booking.items).joinedload(BookingItem.service)
        ).filter(Booking.customer_id == user_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        offset = (page - 1) * limit
        return query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_vendor_bookings(db: Session, vendor_id: int, status: str = None, page: int = 1, limit: int = 10):
        query = db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.salon),
            joinedload(Booking.items).joinedload(BookingItem.service)
        ).join(Salon).filter(Salon.owner_id == vendor_id)
        
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