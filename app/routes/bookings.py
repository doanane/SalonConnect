from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query  # CHANGED: imported as http_status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.booking import BookingResponse, BookingCreate, BookingUpdate
from app.routes.users import get_current_user
from app.services.booking_service import BookingService

router = APIRouter()

@router.get("/", response_model=List[BookingResponse])
def get_bookings(
    status: Optional[str] = Query(None),  # This parameter name conflicts with the status module
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get bookings for current user"""
    return BookingService.get_user_bookings(db, current_user.id, status, page, limit)

@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_data: BookingCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new booking"""
    if current_user.role.value != "customer":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,  # CHANGED: Use http_status
            detail="Only customers can create bookings"
        )
    
    return BookingService.create_booking(db, booking_data, current_user.id)

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get booking by ID"""
    booking = BookingService.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,  # CHANGED: Use http_status
            detail="Booking not found"
        )
    
    # Authorization check
    if booking.customer_id != current_user.id and (
        current_user.role.value == "vendor" and booking.salon.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,  # CHANGED: Use http_status
            detail="Not authorized to view this booking"
        )
    
    return booking

@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update booking status"""
    booking = BookingService.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,  # CHANGED: Use http_status
            detail="Booking not found"
        )
    
    # Authorization check
    if booking.customer_id != current_user.id and (
        current_user.role.value == "vendor" and booking.salon.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,  # CHANGED: Use http_status
            detail="Not authorized to update this booking"
        )
    
    return BookingService.update_booking(db, booking_id, booking_data)

@router.get("/vendor/bookings", response_model=List[BookingResponse])
def get_vendor_bookings(
    status: Optional[str] = Query(None),  # This parameter name conflicts with the status module
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get bookings for vendor's salons"""
    if current_user.role.value != "vendor":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,  # CHANGED: Use http_status
            detail="Only vendors can access this endpoint"
        )
    
    return BookingService.get_vendor_bookings(db, current_user.id, status, page, limit)