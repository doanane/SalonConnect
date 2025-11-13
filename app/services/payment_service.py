from sqlalchemy.orm import Session
from fastapi import HTTPException
import requests
import uuid
from datetime import datetime

from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.booking import Booking, BookingStatus
from app.core.config import settings
from app.services.email import EmailService

class PaymentService:

    @staticmethod
    def initiate_payment(db: Session, booking_id: int, customer_id: int):
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.customer_id == customer_id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Create payment record
        payment_reference = str(uuid.uuid4())
        payment = Payment(
            booking_id=booking_id,
            reference=payment_reference,
            amount=booking.total_amount,
            currency="GHS",
            payment_method=PaymentMethod.PAYSTACK
        )
        
        db.add(payment)
        db.commit()
        
        # Initialize Paystack payment - TEST MODE
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            # For test mode, use a simple callback URL
            callback_url = f"{settings.FRONTEND_URL}/payment/success"
            
            payload = {
                "email": booking.customer.email,
                "amount": int(booking.total_amount * 100),  # Convert GHS to pesewas
                "reference": payment_reference,
                "callback_url": callback_url,
                "currency": "GHS",
                "metadata": {
                    "booking_id": booking_id,
                    "customer_id": customer_id,
                    "test_mode": True  # Mark as test mode
                }
            }
            
            print(f"🧪 [TEST MODE] Initializing Paystack payment: {payload}")
            
            response = requests.post(
                f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f" [TEST MODE] Payment initialized: {data}")
                return {
                    "payment_reference": payment_reference,
                    "authorization_url": data['data']['authorization_url'],
                    "access_code": data['data']['access_code'],
                    "amount": booking.total_amount,
                    "currency": "GHS",
                    "test_mode": True
                }
            else:
                print(f"❌ [TEST MODE] Paystack error: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to initialize payment")
                
        except Exception as e:
            db.rollback()
            print(f"❌ [TEST MODE] Payment initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")    
    @staticmethod
    def verify_payment(db: Session, reference: str, customer_id: int):
        payment = db.query(Payment).filter(Payment.reference == reference).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Verify payment with Paystack
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['data']['status'] == 'success':
                    payment.status = PaymentStatus.SUCCESSFUL
                    payment.paystack_reference = data['data']['reference']
                    payment.paid_at = datetime.now()
                    
                    # Update booking status
                    payment.booking.status = BookingStatus.CONFIRMED
                    
                    db.commit()
                    db.refresh(payment)
                    
                    # Send payment confirmation email
                    EmailService.send_payment_confirmation(
                        payment.booking.customer, 
                        payment, 
                        payment.booking
                    )
                    
                    return payment
                else:
                    payment.status = PaymentStatus.FAILED
                    db.commit()
                    raise HTTPException(status_code=400, detail="Payment verification failed")
            else:
                raise HTTPException(status_code=400, detail="Failed to verify payment")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: int):
        return db.query(Payment).filter(Payment.id == payment_id).first()