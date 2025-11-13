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
            
            # Validate configuration
            if not settings.SENDGRID_API_KEY:
                print("[SENDGRID] Missing SENDGRID_API_KEY")
                return False
            
            if not settings.FROM_EMAIL:
                print("[SENDGRID] Missing FROM_EMAIL")
                return False

            # SendGrid API endpoint
            url = "https://api.sendgrid.com/v3/mail/send"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "SalonConnect-API/1.0"
            }
            
            # FIXED: Content order - text/plain must come first
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
            
            # Send request with timeout
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
            <meta name="format-detection" content="telephone=no">
            <meta name="format-detection" content="date=no">
            <meta name="format-detection" content="address=no">
            <meta name="format-detection" content="email=no">
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
                    <p style="margin: 0 0 10px 0;" class="small">
                        Salon Connect | Professional Beauty Services | Ghana
                    </p>
                    <div class="legal">
                        <p style="margin: 0 0 5px 0;">
                            This email was sent to {user_email} because you have an account with Salon Connect or requested this action.
                            If you believe you received this email in error, please contact our support team.
                        </p>
                        <p style="margin: 0;">
                            Our mailing address is: Salon Connect, Accra, Ghana
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
                    <p>Thank you for choosing Salon Connect - your gateway to professional beauty and wellness services.</p>
                    <div class="notice">
                        <h3 style="margin-top: 0; color: #2c3e50;">Complete Your Registration</h3>
                        <p style="margin-bottom: 0;">To activate your account and start booking appointments, please verify your email address by clicking the button below:</p>
                    </div>
                    <div class="text-center">
                        <a href="{action_url}" class="button" style="color: white; text-decoration: none;">Verify Email Address</a>
                    </div>
                    <div class="warning">
                        <strong>Important Security Notice:</strong> This verification link expires in 24 hours. Please verify your email promptly to secure your account.
                    </div>
                    <p class="small">If the button doesn't work, copy and paste this link into your browser:</p>
                    <p class="small" style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{action_url}</p>
                    <div class="spam-alert">
                        <strong>Email Delivery Tip:</strong> To ensure you receive all important communications from Salon Connect, please add <strong>{settings.FROM_EMAIL}</strong> to your contacts or safe senders list.
                    </div>
                    <p class="small">If you didn't create this account, please ignore this email or contact our support team for assistance.</p>
                """
            },
            "password_reset": {
                "subject": "Salon Connect - Password Reset Request",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Password Reset Request</h2>
                    <p>Hello {user_data.get('first_name', 'there')},</p>
                    <div class="warning">
                        <h3 style="margin-top: 0; color: #856404;">Security Notice</h3>
                        <p style="margin-bottom: 0;">We received a request to reset your password for your Salon Connect account. If this wasn't you, please ignore this email.</p>
                    </div>
                    <div class="text-center">
                        <a href="{action_url}" class="button" style="color: white; text-decoration: none;">Reset Password</a>
                    </div>
                    <div class="warning">
                        <strong>Time-sensitive Action:</strong> This reset link expires in 1 hour for security reasons. Please reset your password promptly.
                    </div>
                    <p class="small">If the button doesn't work, copy and paste this link into your browser:</p>
                    <p class="small" style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{action_url}</p>
                    <p class="small">For your security, this password reset link can only be used once and will expire after use.</p>
                    <div class="spam-alert">
                        <strong>Account Security:</strong> If you didn't request this password reset, your account may be at risk. Please contact our support team immediately.
                    </div>
                """
            },
            "otp": {
                "subject": "Your Salon Connect Verification Code",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Login Verification Code</h2>
                    <p>Hello {user_data.get('first_name', 'there')},</p>
                    <div class="notice">
                        <p style="margin-bottom: 15px;">You've requested to log in to your Salon Connect account. Use the following verification code to complete your login:</p>
                    </div>
                    <div class="otp-code">{otp}</div>
                    <div class="warning">
                        <strong>Security Information:</strong> 
                        <ul>
                            <li>This code expires in 10 minutes</li>
                            <li>Do not share this code with anyone</li>
                            <li>Salon Connect will never ask for this code via phone or email</li>
                        </ul>
                    </div>
                    <p>If you didn't request this login code, please secure your account by changing your password immediately.</p>
                    <div class="spam-alert">
                        <strong>Email Delivery:</strong> To ensure you receive all important account notifications, please add <strong>{settings.FROM_EMAIL}</strong> to your safe senders list.
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
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Booking Confirmation - Salon Connect</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .booking-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Booking Confirmed! 🎉</h1>
                        <p>Salon Connect</p>
                    </div>
                    <div class="content">
                        <h2>Hello {user_data['first_name']},</h2>
                        <p>Your booking has been confirmed. Here are your booking details:</p>
                        
                        <div class="booking-details">
                            <h3>Booking Details</h3>
                            <p><strong>Salon:</strong> {getattr(salon, 'name', 'Unknown Salon')}</p>
                            <p><strong>Booking Date:</strong> {booking_date}</p>
                            <p><strong>Booking ID:</strong> #{getattr(booking, 'id', 'N/A')}</p>
                            <p><strong>Status:</strong> {getattr(booking, 'status', 'Confirmed')}</p>
                            <p><strong>Total Amount:</strong> GH₵{getattr(booking, 'total_amount', 0):,.2f}</p>
                            <p><strong>Special Requests:</strong> {getattr(booking, 'special_requests', 'None')}</p>
                        </div>
                        
                        <p>We look forward to serving you! If you need to modify or cancel your booking, please do so at least 2 hours in advance.</p>
                        
                        <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <strong>📍 Salon Address:</strong><br>
                            {getattr(salon, 'address', 'Address not available')}
                        </div>
                    </div>
                    <div class="footer">
                        <p>Thank you for choosing Salon Connect!</p>
                        <p>© 2024 Salon Connect. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "Booking Confirmation - Salon Connect"
            
            print(f"[SENDGRID] Sending booking confirmation to: {user_data['email']}")
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
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>New Booking - Salon Connect</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28a745; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .booking-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>New Booking Received! 📅</h1>
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
                    <div class="footer">
                        <p>Salon Connect Vendor Portal</p>
                        <p>© 2024 Salon Connect. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "New Booking Received - Salon Connect"
            
            print(f"[SENDGRID] Sending booking notification to vendor: {user_data['email']}")
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
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Confirmed - Salon Connect</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28a745; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .payment-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
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
                    <div class="footer">
                        <p>Thank you for choosing Salon Connect!</p>
                        <p>© 2024 Salon Connect. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = "Payment Confirmed - Salon Connect"
            
            print(f"[SENDGRID] Sending payment confirmation to: {user_data['email']}")
            return EmailService.send_email(user_data['email'], subject, html_content)
        except Exception as e:
            print(f"Error sending payment confirmation: {e}")
            return False

    # Token generation methods
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