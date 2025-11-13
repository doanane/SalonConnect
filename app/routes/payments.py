from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
import json
import hmac
import hashlib
import uuid
from datetime import datetime

from app.database import get_db
from app.schemas.payment import PaymentResponse, PaymentInitiate, PaymentVerification
from app.routes.users import get_current_user
from app.services.payment_service import PaymentService
from app.core.config import settings

router = APIRouter()

# Background task functions - ADD THESE
def process_successful_payment(db: Session, reference: str, data: dict):
    """Process successful payment in background"""
    try:
        print(f" [TEST MODE] Processing successful payment for reference: {reference}")
        
        # Find payment by reference
        from app.models.payment import Payment, PaymentStatus
        from app.models.booking import BookingStatus
        
        payment = db.query(Payment).filter(Payment.reference == reference).first()
        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.paystack_reference = data.get('reference', reference)
            payment.paid_at = datetime.now()
            payment.payment_data = json.dumps(data)
            
            # Update booking status
            if payment.booking:
                payment.booking.status = BookingStatus.CONFIRMED
            
            db.commit()
            print(f" [TEST MODE] Payment {reference} marked as successful")
            
            # Send confirmation email
            from app.services.email import EmailService
            try:
                EmailService.send_payment_confirmation(
                    payment.booking.customer, 
                    payment, 
                    payment.booking
                )
                print(f" [TEST MODE] Payment confirmation email sent for {reference}")
            except Exception as email_error:
                print(f"⚠️ [TEST MODE] Failed to send payment confirmation email: {email_error}")
        else:
            print(f"❌ [TEST MODE] Payment not found for reference: {reference}")
            
    except Exception as e:
        print(f"❌ [TEST MODE] Error processing successful payment: {e}")
        db.rollback()

def process_failed_payment(db: Session, reference: str, data: dict):
    """Process failed payment in background"""
    try:
        print(f"❌ [TEST MODE] Processing failed payment for reference: {reference}")
        
        from app.models.payment import Payment, PaymentStatus
        
        payment = db.query(Payment).filter(Payment.reference == reference).first()
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.payment_data = json.dumps(data)
            db.commit()
            print(f"❌ [TEST MODE] Payment {reference} marked as failed")
        else:
            print(f"❌ [TEST MODE] Payment not found for reference: {reference}")
            
    except Exception as e:
        print(f"❌ [TEST MODE] Error processing failed payment: {e}")
        db.rollback()

# Your existing routes
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
    """Handle Paystack webhook events - TEST MODE VERSION"""
    try:
        # Get the signature from header
        signature = request.headers.get('x-paystack-signature')
        
        # Read the request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        print(f"🔔 [TEST MODE] Webhook received")
        print(f"🔔 [TEST MODE] Body: {body_str}")
        print(f"🔔 [TEST MODE] Signature: {signature}")
        
        # In test mode, Paystack often sends events without signatures
        # For test mode, we'll process events even without signatures
        if not signature:
            print("⚠️ [TEST MODE] No signature - processing as test event")
            # Continue processing without signature verification in test mode
        
        else:
            # Verify signature if provided (for production readiness)
            computed_signature = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
                body,
                hashlib.sha512
            ).hexdigest()
            
            print(f"🔔 [TEST MODE] Computed signature: {computed_signature}")
            
            if not hmac.compare_digest(computed_signature, signature):
                print("❌ [TEST MODE] Invalid signature - but continuing in test mode")
                # In test mode, we continue even with invalid signature
        
        # Parse the webhook data
        try:
            event_data = json.loads(body_str)
        except json.JSONDecodeError:
            print("❌ [TEST MODE] Invalid JSON - but acknowledging")
            return {"status": "success", "message": "Invalid JSON but acknowledged"}
        
        event_type = event_data.get('event')
        data = event_data.get('data', {})
        
        print(f"🔔 [TEST MODE] Event type: {event_type}")
        print(f"🔔 [TEST MODE] Event data: {json.dumps(data, indent=2)}")
        
        # Handle different event types
        if event_type == 'charge.success':
            reference = data.get('reference')
            if reference:
                print(f" [TEST MODE] Processing successful charge: {reference}")
                background_tasks.add_task(
                    process_successful_payment, 
                    db, 
                    reference, 
                    data
                )
                return {"status": "success", "message": "Charge success processed"}
            else:
                print("❌ [TEST MODE] No reference in charge.success event")
        
        elif event_type == 'charge.failed':
            reference = data.get('reference')
            if reference:
                print(f"❌ [TEST MODE] Processing failed charge: {reference}")
                background_tasks.add_task(
                    process_failed_payment,
                    db,
                    reference,
                    data
                )
                return {"status": "success", "message": "Charge failed processed"}
        
        elif event_type in ['transfer.success', 'transfer.failed', 'subscription.create']:
            print(f"ℹ️ [TEST MODE] Unhandled but acknowledged: {event_type}")
            return {"status": "success", "message": f"{event_type} acknowledged"}
        
        elif event_type == 'test' or 'test' in body_str.lower():
            print(" [TEST MODE] Test event received and acknowledged")
            return {"status": "success", "message": "Test event received"}
        
        else:
            print(f"ℹ️ [TEST MODE] Unhandled event type: {event_type}")
            return {"status": "success", "message": "Event acknowledged but not handled"}
        
        # If we get here, return success anyway
        return {"status": "success", "message": "Webhook processed"}
        
    except Exception as e:
        print(f"❌ [TEST MODE] Webhook error: {str(e)}")
        # Always return 200 in test mode to prevent retries
        return {"status": "success", "message": f"Error but acknowledged: {str(e)}"}

@router.get("/webhook/test-connection")
async def test_webhook_connection():
    """Test if webhook endpoint is accessible from Paystack"""
    return {
        "status": "success",
        "message": "Webhook endpoint is accessible",
        "test_mode": True,
        "webhook_url": "https://salonconnect-qzne.onrender.com/api/payments/webhook/paystack",
        "instructions": "Use this URL in Paystack dashboard webhook settings"
    }

@router.post("/webhook/simulate-paystack")
async def simulate_paystack_webhook(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Simulate a Paystack webhook event for testing"""
    # Create a test reference
    test_reference = f"test_{uuid.uuid4().hex[:8]}"
    
    # Simulate Paystack webhook payload
    test_payload = {
        "event": "charge.success",
        "data": {
            "id": 123456789,
            "domain": "test",
            "status": "success",
            "reference": test_reference,
            "amount": 5000,  # 50 GHS in pesewas
            "message": "Successful",
            "gateway_response": "Successful",
            "paid_at": "2024-01-01T12:00:00.000Z",
            "created_at": "2024-01-01T11:00:00.000Z",
            "channel": "card",
            "currency": "GHS",
            "ip_address": "127.0.0.1",
            "metadata": {
                "booking_id": 1,
                "customer_id": 1,
                "test_mode": True
            },
            "fees": 50,
            "customer": {
                "id": 12345,
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            }
        }
    }
    
    print(f"🧪 [TEST MODE] Simulating Paystack webhook: {test_payload}")
    
    # Process the simulated webhook
    background_tasks.add_task(
        process_successful_payment,
        db,
        test_reference,
        test_payload['data']
    )
    
    return {
        "status": "success",
        "message": "Test webhook simulated",
        "reference": test_reference,
        "test_payload": test_payload
    }

@router.get("/webhook/create-test-payment")
async def create_test_payment(db: Session = Depends(get_db)):
    """Create a test payment record for webhook testing"""
    try:
        from app.models.payment import Payment, PaymentStatus, PaymentMethod
        from app.models.booking import Booking
        from app.models.user import User
        
        # Get first user and booking for testing
        test_user = db.query(User).first()
        test_booking = db.query(Booking).first()
        
        if not test_user or not test_booking:
            return {"error": "Need users and bookings in database first"}
        
        # Create test payment
        test_reference = f"test_{uuid.uuid4().hex[:8]}"
        test_payment = Payment(
            booking_id=test_booking.id,
            reference=test_reference,
            amount=50.0,  # 50 GHS
            currency="GHS",
            payment_method=PaymentMethod.PAYSTACK,
            status=PaymentStatus.PENDING
        )
        
        db.add(test_payment)
        db.commit()
        
        return {
            "status": "success",
            "message": "Test payment created",
            "payment_reference": test_reference,
            "booking_id": test_booking.id,
            "user_id": test_user.id,
            "amount": 50.0,
            "currency": "GHS"
        }
        
    except Exception as e:
        return {"error": f"Failed to create test payment: {str(e)}"}