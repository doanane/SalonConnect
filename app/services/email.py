import requests
import jwt
import random
import string
from datetime import datetime, timedelta
from app.core.config import settings
import os

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid API with comprehensive anti-spam measures"""
        try:
            print(f"🔧 [SENDGRID] Starting email send to: {to_email}")
            print(f"🔧 [SENDGRID] From: {settings.FROM_EMAIL}")
            print(f"🔧 [SENDGRID] Subject: {subject}")
            
            # Validate configuration
            if not settings.SENDGRID_API_KEY:
                print("❌ [SENDGRID] Missing SENDGRID_API_KEY")
                return False
            
            if not settings.FROM_EMAIL:
                print("❌ [SENDGRID] Missing FROM_EMAIL")
                return False

            # SendGrid API endpoint
            url = "https://api.sendgrid.com/v3/mail/send"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "SalonConnect-API/1.0"
            }
            
            # Enhanced request body with all anti-spam measures
            data = {
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "headers": {
                        "X-Priority": "1",
                        "X-MSMail-Priority": "High",
                        "Importance": "high",
                        "X-Mailer": "SalonConnect",
                        "List-Unsubscribe": f"<mailto:unsubscribe@{settings.FROM_EMAIL.split('@')[1]}>",
                        "Precedence": "bulk"
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
                "content": [{
                    "type": "text/html",
                    "value": html_content
                }],
                "mail_settings": {
                    "bypass_list_management": {"enable": False},
                    "footer": {"enable": False},
                    "sandbox_mode": {"enable": False},
                    "spam_check": {"enable": False}  # ← FIXED: Disabled spam check
                },
                "tracking_settings": {
                    "click_tracking": {"enable": False},
                    "open_tracking": {"enable": False},
                    "subscription_tracking": {"enable": False}
                },
                "categories": ["transactional", "salon_connect"]
            }
            
            print(f"🔧 [SENDGRID] Sending email via SendGrid API...")
            
            # Send request with timeout
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 202:
                print(f"✅ [SENDGRID] Email sent successfully! Status: {response.status_code}")
                return True
            else:
                print(f"❌ [SENDGRID] Failed to send email. Status: {response.status_code}")
                error_response = response.json()
                print(f"❌ [SENDGRID] Error details: {error_response}")
                return False
            
        except requests.exceptions.Timeout:
            print(f"❌ [SENDGRID] Request timeout - email might still be sent")
            return True
        except Exception as e:
            print(f"❌ [SENDGRID] Error sending email: {str(e)}")
            import traceback
            print(f"❌ [SENDGRID] Traceback: {traceback.format_exc()}")
            return False
            
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
                /* Reset and base styles */
                body, html {{ margin: 0; padding: 0; font-family: 'Arial', 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; background-color: #f6f9fc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 32px; font-weight: 700;">Salon Connect</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Beauty & Wellness Services</p>
                </div>
                
                <div class="content">
                    {content}
                </div>
                
                <div class="footer">
                    <p style="margin: 0 0 10px 0;">© 2024 Salon Connect. All rights reserved.</p>
                    <p style="margin: 0 0 10px 0;" class="small">
                        This email was sent to {user_email} because you have an account with Salon Connect.
                    </p>
                    <p style="margin: 0;" class="small">
                        Salon Connect | Beauty & Wellness Services | Ghana
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        templates = {
            "verification": {
                "subject": "Verify Your Email Address - Salon Connect",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Welcome to Salon Connect, {user_data.get('first_name', 'there')}! 👋</h2>
                    
                    <div class="notice">
                        <h3 style="margin-top: 0; color: #2c3e50;">Complete Your Registration</h3>
                        <p style="margin-bottom: 0;">Thank you for choosing Salon Connect. To activate your account and start booking appointments, please verify your email address.</p>
                    </div>
                    
                    <div class="text-center">
                        <a href="{action_url}" class="button">Verify Email Address</a>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong> This verification link expires in 24 hours.
                    </div>
                    
                    <div class="spam-alert">
                        <strong>📧 Email not in inbox?</strong><br>
                        If you don't see this email in your inbox within 5 minutes, please:
                        <ul>
                            <li>Check your <strong>spam</strong> or <strong>junk</strong> folder</li>
                            <li>Mark this email as <strong>"Not Spam"</strong></li>
                            <li>Add <strong>{settings.FROM_EMAIL}</strong> to your contacts</li>
                        </ul>
                    </div>
                    
                    <p class="small">If you didn't create this account, please ignore this email or contact our support team.</p>
                """
            },
            "password_reset": {
                "subject": "Reset Your Password - Salon Connect",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Password Reset Request</h2>
                    
                    <div class="warning">
                        <h3 style="margin-top: 0; color: #856404;">Security Notice</h3>
                        <p style="margin-bottom: 0;">We received a request to reset your password for your Salon Connect account.</p>
                    </div>
                    
                    <div class="text-center">
                        <a href="{action_url}" class="button">Reset Password</a>
                    </div>
                    
                    <div class="warning">
                        <strong>⏰ Time-sensitive:</strong> This reset link expires in 1 hour for security reasons.
                    </div>
                    
                    <div class="spam-alert">
                        <strong>📧 Can't find this email?</strong><br>
                        Please check your spam folder and mark this email as "Not Spam" to ensure you receive important account notifications.
                    </div>
                    
                    <p class="small">If you didn't request this password reset, please ignore this email. Your account remains secure.</p>
                """
            },
            "otp": {
                "subject": "Your Login Code - Salon Connect",
                "content": f"""
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">Your Login Verification Code</h2>
                    
                    <div class="notice">
                        <p style="margin-bottom: 15px;">Hello {user_data.get('first_name', 'there')}, use the following One-Time Password to log in to your Salon Connect account:</p>
                    </div>
                    
                    <div class="otp-code">{otp}</div>
                    
                    <div class="warning">
                        <strong>⏰ Expires in 10 minutes</strong><br>
                        This code will expire for security reasons. Do not share this code with anyone.
                    </div>
                    
                    <div class="spam-alert">
                        <strong>📧 Not seeing our emails?</strong><br>
                        To ensure you receive all important communications, please add <strong>{settings.FROM_EMAIL}</strong> to your safe senders list.
                    </div>
                    
                    <p class="small">If you didn't request this login code, please ignore this email and consider changing your password.</p>
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
        
        print(f"📧 [SENDGRID] Sending verification email to: {user_data['email']}")
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
        
        print(f"📧 [SENDGRID] Sending password reset email to: {user_data['email']}")
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
        
        print(f"📧 [SENDGRID] Sending OTP email to: {user_data['email']}")
        return EmailService.send_email(user_data['email'], subject, html_content)

    # Keep the token generation methods the same
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