import requests
import jwt
import random
import string
from datetime import datetime, timedelta
from app.core.config import settings
import os
import re

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid API with comprehensive anti-spam measures"""
        try:
            print(f" [SENDGRID] Starting email send to: {to_email}")
            print(f" [SENDGRID] From: {settings.FROM_EMAIL}")
            print(f" [SENDGRID] Subject: {subject}")
            
            if not settings.FROM_EMAIL:
                print("[SENDGRID] Missing FROM_EMAIL")
                return False

            url = "https://api.sendgrid.com/v3/mail/send"
            
            headers = {
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "SalonConnect-API/1.0"
            }
            
            data = {
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "headers": {
                        "X-Priority": "1",
                        "X-MSMail-Priority": "High",
                        "Importance": "high",
                        "X-Mailer": "SalonConnect",
                        "List-Unsubscribe": f"<mailto:unsubscribe@{settings.FROM_EMAIL.split('@')[1]}?subject=unsubscribe>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                        "Precedence": "bulk",
                        "X-Entity-Ref": "salon-connect-transactional",
                        "X-Report-Abuse": f"Please report abuse to {settings.FROM_EMAIL}",
                    }
                }],
                "from": {
                    "email": settings.FROM_EMAIL, 
                    "name": "Salon Connect"
                },
                "reply_to": {
                    "email": settings.FROM_EMAIL,
                    "name": "Salon Connect Support"
                },
                "subject": subject,
                "content": [
                    {
                        "type": "text/plain",
                        "value": EmailService.extract_plain_text(html_content)
                    },
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ],
                "mail_settings": {
                    "bypass_list_management": {"enable": False},
                    "footer": {"enable": False},
                    "sandbox_mode": {"enable": False},
                    "spam_check": {"enable": False}
                },
                "tracking_settings": {
                    "click_tracking": {"enable": True},
                    "open_tracking": {"enable": True},
                    "subscription_tracking": {"enable": False}
                },
                "categories": ["transactional", "salon_connect", "account_notifications"],
                "custom_args": {
                    "app_name": "Salon Connect",
                    "email_type": "transactional",
                    "user_segment": "active"
                }
            }
            
            print(f" [SENDGRID] Sending email via SendGrid API...")
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 202:
                print(f" [SENDGRID] Email sent successfully! Status: {response.status_code}")
                return True
            else:
                print(f"[SENDGRID] Failed to send email. Status: {response.status_code}")
                error_response = response.json()
                print(f"[SENDGRID] Error details: {error_response}")
                return False
            
        except requests.exceptions.Timeout:
            print(f"[SENDGRID] Request timeout - email might still be sent")
            return True
        except Exception as e:
            print(f"[SENDGRID] Error sending email: {str(e)}")
            import traceback
            print(f"[SENDGRID] Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def extract_plain_text(html_content: str) -> str:
        """Extract plain text from HTML content for better deliverability"""
        text = re.sub(r'<br\s*/?>', '\n', html_content)
        text = re.sub(r'</p>', '\n\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = text.strip()
        
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    @staticmethod
    def create_email_template(template_name: str, user_data: dict, action_url: str = None, otp: str = None):
        """Create professional email templates with anti-spam content"""
        
        base_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body, html {{ margin: 0; padding: 0; font-family: 'Arial', 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; background-color: #f6f9fc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                .content {{ padding: 40px 30px; border-bottom: 1px solid #eaeaea; }}
                .footer {{ padding: 30px; text-align: center; color: #666666; font-size: 12px; background: #f8f9fa; }}
                .button {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 25px 0; font-weight: 600; font-size: 16px; text-align: center; }}
                .otp-code {{ background: #2c3e50; color: white; padding: 20px; font-size: 32px; font-weight: bold; text-align: center; letter-spacing: 12px; margin: 25px 0; border-radius: 8px; font-family: 'Courier New', monospace; }}
                .notice {{ background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 8px; padding: 20px; margin: 25px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 25px 0; color: #856404; }}
                .spam-alert {{ background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 20px; margin: 25px 0; color: #721c24; }}
                .text-center {{ text-align: center; }}
                .mb-20 {{ margin-bottom: 20px; }}
                .mt-20 {{ margin-top: 20px; }}
                .small {{ font-size: 14px; color: #666666; }}
                .legal {{ font-size: 11px; color: #999; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 32px; font-weight: 700;">Salon Connect</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Professional Beauty & Wellness Services</p>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p style="margin: 0 0 10px 0;">© 2024 Salon Connect. All rights reserved.</p>
                    <p style="margin: 0 0 10px 0;" class="small">
                        This is a transactional email from Salon Connect sent to {user_email} regarding your account.
                    </p>
                    <div class="legal">
                        <p style="margin: 0 0 5px 0;">
                            This email was sent to {user_email} because you have an account with Salon Connect or requested this action.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        templates = {
            "verification": {
                "subject": "Verify Your Salon Connect Account",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Welcome to Salon Connect, {user_data.get('first_name', 'there')}!</h2>
                    <p>Thank you for choosing Salon Connect.</p>
                    <div class="notice">
                        <h3 style="margin-top: 0; color: #2c3e50;">Complete Your Registration</h3>
                        <p style="margin-bottom: 0;">Please verify your email address by clicking the button below:</p>
                    </div>
                    <div class="text-center">
                        <a href="{action_url}" class="button" style="color: white; text-decoration: none;">Verify Email Address</a>
                    </div>
                    <div class="warning">
                        <strong>Important:</strong> This link expires in 24 hours.
                    </div>
                """
            },
            "password_reset": {
                "subject": "Salon Connect - Password Reset Request",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Password Reset Request</h2>
                    <p>Hello {user_data.get('first_name', 'there')},</p>
                    <div class="warning">
                        <p style="margin-bottom: 0;">We received a request to reset your password.</p>
                    </div>
                    <div class="text-center">
                        <a href="{action_url}" class="button" style="color: white; text-decoration: none;">Reset Password</a>
                    </div>
                """
            },
            "otp": {
                "subject": "Your Salon Connect Verification Code",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Login Verification Code</h2>
                    <p>Hello {user_data.get('first_name', 'there')},</p>
                    <div class="notice">
                        <p style="margin-bottom: 15px;">Use the following verification code to complete your login:</p>
                    </div>
                    <div class="otp-code">{otp}</div>
                    <div class="warning">
                        <strong>Security Information:</strong> Code expires in 10 minutes.
                    </div>
                """
            },
            "trial_started": {
                "subject": "Your 30-Day Premium Trial Has Started! 🚀",
                "content": f"""
                    <h2 style="color: #2c3e50;">Verification Successful!</h2>
                    <p>Hello {user_data.get('first_name', 'Vendor')},</p>
                    <p>Your identity has been verified. You have officially started your <strong>30-Day Free Trial</strong>.</p>
                    
                    <div class="notice">
                        <h3>Premium Features Unlocked:</h3>
                        <ul style="text-align: left;">
                            <li>Unlimited Service Listings</li>
                            <li>Accept Online Bookings</li>
                            <li>Advanced Sales Analytics</li>
                            <li>Verified Vendor Badge</li>
                        </ul>
                    </div>
                    
                    <p><strong>Trial Expires:</strong> {user_data.get('expiry_date', '30 days')}</p>
                    
                    <div class="text-center">
                        <a href="{action_url}" class="button">Go to Dashboard</a>
                    </div>
                """
            },
            "trial_ending": {
                "subject": "Action Required: Trial Ending in 3 Days ⏳",
                "content": f"""
                    <h2 style="color: #c0392b;">Your Trial is Expiring Soon</h2>
                    <p>Hello {user_data.get('first_name', 'Vendor')},</p>
                    <p>This is a reminder that your free trial ends on <strong>{user_data.get('expiry_date', 'soon')}</strong>.</p>
                    
                    <div class="warning">
                        <p>To avoid losing access to booking features, please choose a subscription plan.</p>
                    </div>
                    
                    <div class="text-center">
                        <a href="{action_url}" class="button">View Subscription Plans</a>
                    </div>
                """
            }
        }
        
        template = templates.get(template_name, templates["verification"])
        user_email = user_data.get('email', 'you')
        
        return base_template.format(
            subject=template["subject"],
            content=template["content"],
            user_email=user_email
        ), template["subject"]

    @staticmethod
    def send_verification_email(user, verification_url: str):
        """Send email verification email"""
        user_data = {
            'email': getattr(user, 'email', ''),
            'first_name': getattr(user, 'first_name', 'there')
        }
        
        html_content, subject = EmailService.create_email_template(
            "verification", user_data, action_url=verification_url
        )
        
        print(f"[SENDGRID] Sending verification email to: {user_data['email']}")
        return EmailService.send_email(user_data['email'], subject, html_content)

    @staticmethod
    def send_password_reset_email(user, reset_url: str):
        """Send password reset email"""
        user_data = {
            'email': getattr(user, 'email', ''),
            'first_name': getattr(user, 'first_name', 'there')
        }
        
        html_content, subject = EmailService.create_email_template(
            "password_reset", user_data, action_url=reset_url
        )
        
        print(f"[SENDGRID] Sending password reset email to: {user_data['email']}")
        return EmailService.send_email(user_data['email'], subject, html_content)

    @staticmethod
    def send_otp_email(user, otp: str):
        """Send OTP for login"""
        user_data = {
            'email': getattr(user, 'email', ''),
            'first_name': getattr(user, 'first_name', 'there')
        }
        
        html_content, subject = EmailService.create_email_template(
            "otp", user_data, otp=otp
        )
        
        print(f"[SENDGRID] Sending OTP email to: {user_data['email']}")
        return EmailService.send_email(user_data['email'], subject, html_content)

    @staticmethod
    def send_booking_confirmation(user, booking, salon):
        """Send booking confirmation email to customer"""
        try:
            user_data = {
                'email': getattr(user, 'email', ''),
                'first_name': getattr(user, 'first_name', 'there')
            }
            
            # Format booking date
            booking_date = getattr(booking, 'booking_date', 'Unknown date')
            if isinstance(booking_date, datetime):
                booking_date = booking_date.strftime("%B %d, %Y at %I:%M %p")
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .booking-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Booking Confirmed! 🎉</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {user_data['first_name']},</h2>
                        <p>Your booking details:</p>
                        <div class="booking-details">
                            <p><strong>Salon:</strong> {getattr(salon, 'name', 'Unknown Salon')}</p>
                            <p><strong>Date:</strong> {booking_date}</p>
                            <p><strong>Total:</strong> GH₵{getattr(booking, 'total_amount', 0):,.2f}</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "Booking Confirmation - Salon Connect"
            return EmailService.send_email(user_data['email'], subject, html_content)
        except Exception as e:
            print(f"Error sending booking confirmation: {e}")
            return False

    @staticmethod
    def send_booking_notification_to_vendor(vendor, booking, customer, salon):
        """Send booking notification email to vendor"""
        try:
            user_data = {
                'email': getattr(vendor, 'email', ''),
                'first_name': getattr(vendor, 'first_name', 'Vendor')
            }
            
            # Format booking date
            booking_date = getattr(booking, 'booking_date', 'Unknown date')
            if isinstance(booking_date, datetime):
                booking_date = booking_date.strftime("%B %d, %Y at %I:%M %p")
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28a745; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .booking-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>New Booking Received!</h1>
                        <p>Salon Connect</p>
                    </div>
                    <div class="content">
                        <h2>Hello {user_data['first_name']},</h2>
                        <p>You have received a new booking for your salon.</p>
                        
                        <div class="booking-details">
                            <h3>Booking Details</h3>
                            <p><strong>Customer:</strong> {getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}</p>
                            <p><strong>Customer Email:</strong> {getattr(customer, 'email', '')}</p>
                            <p><strong>Salon:</strong> {getattr(salon, 'name', 'Your Salon')}</p>
                            <p><strong>Booking Date:</strong> {booking_date}</p>
                            <p><strong>Booking ID:</strong> #{getattr(booking, 'id', 'N/A')}</p>
                            <p><strong>Total Amount:</strong> GH₵{getattr(booking, 'total_amount', 0):,.2f}</p>
                            <p><strong>Special Requests:</strong> {getattr(booking, 'special_requests', 'None')}</p>
                        </div>
                        
                        <p>Please log in to your vendor dashboard to manage this booking.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "New Booking Received - Salon Connect"
            return EmailService.send_email(user_data['email'], subject, html_content)
        except Exception as e:
            print(f"Error sending vendor notification: {e}")
            return False

    @staticmethod
    def send_payment_confirmation(user, payment, booking):
        """Send payment confirmation email"""
        try:
            user_data = {
                'email': getattr(user, 'email', ''),
                'first_name': getattr(user, 'first_name', 'there')
            }
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28a745; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .payment-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Payment Confirmed! </h1>
                        <p>Salon Connect</p>
                    </div>
                    <div class="content">
                        <h2>Hello {user_data['first_name']},</h2>
                        <p>Your payment has been successfully processed. Here are your payment details:</p>
                        
                        <div class="payment-details">
                            <h3>Payment Details</h3>
                            <p><strong>Reference:</strong> {getattr(payment, 'reference', 'N/A')}</p>
                            <p><strong>Amount Paid:</strong> GH₵{getattr(payment, 'amount', 0):,.2f}</p>
                            <p><strong>Booking ID:</strong> #{getattr(booking, 'id', 'N/A')}</p>
                            <p><strong>Payment Method:</strong> {getattr(payment, 'payment_method', 'N/A')}</p>
                            <p><strong>Paid At:</strong> {getattr(payment, 'paid_at', 'N/A')}</p>
                        </div>
                        
                        <p>Your booking is now confirmed. We look forward to serving you!</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "Payment Confirmed - Salon Connect"
            return EmailService.send_email(user_data['email'], subject, html_content)
        except Exception as e:
            print(f"Error sending payment confirmation: {e}")
            return False

    @staticmethod
    def send_vendor_verification_email(user, verification_url, vendor_data):
        """Send vendor-specific verification email"""
        try:
            subject = "Welcome to Salon Connect - Vendor Account Verification"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .info-box {{ background: white; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0; }}
                    .btn {{ display: inline-block; background: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to Salon Connect! 🏢</h1>
                        <p>Business Account Registration</p>
                    </div>
                    <div class="content">
                        <h2>Hello {user.first_name} {user.last_name}!</h2>
                        <p>Thank you for registering as a vendor on Salon Connect. We're excited to help you grow your business!</p>
                        
                        <div class="info-box">
                            <h3>Your Business Information:</h3>
                            <p><strong>Business Name:</strong> {vendor_data.business_name}</p>
                            <p><strong>Contact Phone:</strong> {vendor_data.phone_number}</p>
                            <p><strong>Business Phone:</strong> {vendor_data.business_phone}</p>
                            <p><strong>Business Address:</strong> {vendor_data.business_address}, {vendor_data.business_city}, {vendor_data.business_state}, {vendor_data.business_country}</p>
                        </div>
                        
                        <p>To complete your vendor registration and start listing your salon, please verify your email address:</p>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}" class="btn">Verify Email Address</a>
                        </p>
                        
                        <p>After verification, you can:</p>
                        <ul>
                            <li>Create your salon profile</li>
                            <li>Add services and pricing</li>
                            <li>Set your availability</li>
                            <li>Start accepting bookings from customers</li>
                            <li>Manage your business dashboard</li>
                        </ul>
                        
                        <p>If you have any questions, please contact our vendor support team.</p>
                        
                        <p>Best regards,<br>The Salon Connect Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return EmailService.send_email(user.email, subject, html_content)
            
        except Exception as e:
            print(f"Failed to send vendor verification email: {e}")
            return False

    @staticmethod
    def send_trial_started_email(user, expiry_date):
        """Send email when KYC is approved and trial starts"""
        try:
            expiry_str = expiry_date.strftime("%B %d, %Y")
            user_data = {
                'email': user.email,
                'first_name': user.first_name,
                'expiry_date': expiry_str
            }
            # Update this URL to match your frontend dashboard route
            dashboard_url = f"{settings.FRONTEND_URL}/vendor/dashboard"
            
            html_content, subject = EmailService.create_email_template(
                "trial_started", user_data, action_url=dashboard_url
            )
            return EmailService.send_email(user.email, subject, html_content)
        except Exception as e:
            print(f"Failed to send trial started email: {e}")
            return False

    @staticmethod
    def send_trial_warning_email(user, expiry_date):
        """Send email when trial is about to expire"""
        try:
            expiry_str = expiry_date.strftime("%B %d, %Y")
            user_data = {
                'email': user.email,
                'first_name': user.first_name,
                'expiry_date': expiry_str
            }
            # Update this URL to match your frontend subscription route
            subscription_url = f"{settings.FRONTEND_URL}/vendor/subscription"
            
            html_content, subject = EmailService.create_email_template(
                "trial_ending", user_data, action_url=subscription_url
            )
            return EmailService.send_email(user.email, subject, html_content)
        except Exception as e:
            print(f"Failed to send trial warning email: {e}")
            return False

    @staticmethod
    def generate_verification_token(email: str) -> str:
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'type': 'email_verification'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token

    @staticmethod
    def generate_reset_token(email: str) -> str:
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'password_reset'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token

    @staticmethod
    def verify_token(token: str, token_type: str) -> dict:
        try:
            if token.startswith("b'") and token.endswith("'"):
                token = token[2:-1]
            
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('type') != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def verify_reset_token(token: str) -> dict:
        return EmailService.verify_token(token, 'password_reset')

    @staticmethod
    def generate_otp() -> str:
        return ''.join(random.choices(string.digits, k=6))