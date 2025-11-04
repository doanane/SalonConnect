from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import json
import hmac
import hashlib

from app.database import get_db
from app.schemas.payment import PaymentResponse, PaymentInitiate, PaymentVerification
from app.routes.auth import get_current_user
from app.services.payment_service import PaymentService
from app.core.config import settings

router = APIRouter()

@router.post("/initiate", response_model=dict)
def initiate_payment(
    payment_data: PaymentInitiate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate payment for a booking"""
    return PaymentService.initiate_payment(db, payment_data.booking_id, current_user.id)

@router.post("/verify", response_model=PaymentResponse)
def verify_payment(
    verification_data: PaymentVerification,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify payment status"""
    return PaymentService.verify_payment(db, verification_data.reference, current_user.id)

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment by ID"""
    payment = PaymentService.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if user is authorized to view this payment
    if payment.booking.customer_id != current_user.id and (
        current_user.role == "vendor" and payment.booking.salon.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return payment

@router.post("/webhook/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Paystack webhook events"""
    # Verify webhook signature
    signature = request.headers.get('x-paystack-signature')
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    body = await request.body()
    
    # Verify signature
    computed_signature = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(computed_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process webhook event
    event_data = json.loads(body)
    return PaymentService.handle_webhook_event(db, event_data)