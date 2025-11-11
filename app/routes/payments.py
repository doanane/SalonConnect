from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
import json
import hmac
import hashlib

from app.database import get_db
from app.schemas.payment import PaymentResponse, PaymentInitiate, PaymentVerification
from app.routes.users import get_current_user
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
        current_user.role.value == "vendor" and payment.booking.salon.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return payment

@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Paystack webhook events"""
    try:
        # Get the signature from header
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            print("❌ Webhook error: Missing x-paystack-signature header")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Read the request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        print(f"🔔 Webhook received: {body_str}")
        print(f"🔔 Signature: {signature}")
        
        # Verify signature
        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        print(f"🔔 Computed signature: {computed_signature}")
        
        if not hmac.compare_digest(computed_signature, signature):
            print("❌ Webhook error: Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse the webhook data
        event_data = json.loads(body_str)
        event_type = event_data.get('event')
        data = event_data.get('data', {})
        
        print(f"🔔 Webhook event: {event_type}")
        print(f"🔔 Webhook data: {data}")
        
        # Process different webhook events
        if event_type == 'charge.success':
            # Handle successful payment
            reference = data.get('reference')
            if reference:
                # Process in background to avoid timeout
                background_tasks.add_task(
                    process_successful_payment, 
                    db, 
                    reference, 
                    data
                )
                return {"status": "success", "message": "Webhook processed"}
        
        elif event_type == 'charge.failed':
            # Handle failed payment
            reference = data.get('reference')
            if reference:
                background_tasks.add_task(
                    process_failed_payment,
                    db,
                    reference,
                    data
                )
                return {"status": "success", "message": "Webhook processed"}
        
        # Return success for other events we don't handle
        return {"status": "success", "message": "Event not handled but acknowledged"}
        
    except json.JSONDecodeError:
        print("❌ Webhook error: Invalid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

# Background task functions
def process_successful_payment(db: Session, reference: str, data: dict):
    """Process successful payment in background"""
    try:
        print(f"✅ Processing successful payment for reference: {reference}")
        
        # Find payment by reference
        from app.models.payment import Payment, PaymentStatus
        from app.models.booking import BookingStatus
        
        payment = db.query(Payment).filter(Payment.reference == reference).first()
        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.paystack_reference = data.get('paystack_reference', reference)
            payment.paid_at = data.get('paid_at')
            payment.payment_data = json.dumps(data)
            
            # Update booking status
            if payment.booking:
                payment.booking.status = BookingStatus.CONFIRMED
            
            db.commit()
            print(f"✅ Payment {reference} marked as successful")
            
            # Send confirmation email
            from app.services.email import EmailService
            try:
                EmailService.send_payment_confirmation(
                    payment.booking.customer, 
                    payment, 
                    payment.booking
                )
                print(f"✅ Payment confirmation email sent for {reference}")
            except Exception as email_error:
                print(f"⚠️ Failed to send payment confirmation email: {email_error}")
        else:
            print(f"❌ Payment not found for reference: {reference}")
            
    except Exception as e:
        print(f"❌ Error processing successful payment: {e}")
        db.rollback()

def process_failed_payment(db: Session, reference: str, data: dict):
    """Process failed payment in background"""
    try:
        print(f"❌ Processing failed payment for reference: {reference}")
        
        from app.models.payment import Payment, PaymentStatus
        
        payment = db.query(Payment).filter(Payment.reference == reference).first()
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.payment_data = json.dumps(data)
            db.commit()
            print(f"❌ Payment {reference} marked as failed")
        else:
            print(f"❌ Payment not found for reference: {reference}")
            
    except Exception as e:
        print(f"❌ Error processing failed payment: {e}")
        db.rollback()

@router.post("/webhook/test")
async def test_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Test webhook endpoint (for development only)"""
    # Create a test payment first
    from app.models.payment import Payment, PaymentStatus, PaymentMethod
    from app.models.booking import Booking, BookingStatus
    from app.models.user import User
    
    # Create a test user and booking if they don't exist
    test_user = db.query(User).first()
    if not test_user:
        return {"error": "No users in database"}
    
    test_booking = db.query(Booking).first()
    if not test_booking:
        return {"error": "No bookings in database"}
    
    # Create test payment
    import uuid
    test_reference = f"test_{uuid.uuid4().hex[:8]}"
    test_payment = Payment(
        booking_id=test_booking.id,
        reference=test_reference,
        amount=100.0,
        currency="GHS",
        payment_method=PaymentMethod.PAYSTACK,
        status=PaymentStatus.PENDING
    )
    db.add(test_payment)
    db.commit()
    
    # Simulate webhook data
    webhook_data = {
        "event": "charge.success",
        "data": {
            "reference": test_reference,
            "amount": 10000,  # in pesewas
            "currency": "GHS",
            "status": "success",
            "paid_at": "2024-01-01T12:00:00Z",
            "paystack_reference": f"ps_{uuid.uuid4().hex[:8]}"
        }
    }
    
    # Process the test webhook
    background_tasks.add_task(
        process_successful_payment,
        db,
        test_reference,
        webhook_data['data']
    )
    
    return {
        "message": "Test webhook triggered",
        "test_reference": test_reference,
        "test_booking_id": test_booking.id
    }