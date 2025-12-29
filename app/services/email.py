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
            
            if not settings.SENDGRID_API_KEY:
                print("[SENDGRID] Missing SENDGRID_API_KEY")
                return False
                
            if not settings.FROM_EMAIL:
                print("[SENDGRID] Missing FROM_EMAIL")
                return False

            url = "https://api.sendgrid.com/v3/mail/send"
            
            headers = {
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "SalonConnect-API/1.0"
            }
            
            # Add DKIM/SPF friendly headers
            from_domain = settings.FROM_EMAIL.split('@')[1] if '@' in settings.FROM_EMAIL else "salonconnect.com"
            
            data = {
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "headers": {
                        "X-Priority": "3",
                        "X-MSMail-Priority": "Normal",
                        "Importance": "normal",
                        "X-Mailer": "SalonConnect",
                        "List-Unsubscribe": f"<mailto:unsubscribe@{from_domain}?subject=unsubscribe>, <https://saloonconnect.vercel.app/unsubscribe>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                        "Precedence": "bulk",
                        "X-Entity-Ref": f"salon-connect-{to_email}",
                        "X-Report-Abuse": f"Please report abuse to {settings.FROM_EMAIL}",
                        "X-Auto-Response-Suppress": "All",
                        "Auto-Submitted": "auto-generated"
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
                    "footer": {"enable": True, 
                              "text": "This is a transactional email from Salon Connect.",
                              "html": "<p>This is a transactional email from Salon Connect.</p>"},
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
                    "user_id": to_email.split('@')[0],
                    "timestamp": str(datetime.utcnow().timestamp())
                }
            }
            
            print(f" [SENDGRID] Sending email via SendGrid API...")
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 202:
                print(f" [SENDGRID] Email sent successfully! Status: {response.status_code}")
                return True
            else:
                print(f"[SENDGRID] Failed to send email. Status: {response.status_code}")
                try:
                    error_response = response.json()
                    print(f"[SENDGRID] Error details: {error_response}")
                except:
                    print(f"[SENDGRID] Error text: {response.text}")
                return False
            
        except requests.exceptions.Timeout:
            print(f"[SENDGRID] Request timeout - email might still be sent")
            return False
        except Exception as e:
            print(f"[SENDGRID] Error sending email: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def extract_plain_text(html_content: str) -> str:
        """Extract plain text from HTML content for better deliverability"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Replace HTML entities
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&#13;', '\n', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def create_email_template(template_name: str, user_data: dict, action_url: str = None, otp: str = None):
        """Create professional email templates"""
        
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
                .content {{ padding: 40px 30px; }}
                .footer {{ padding: 30px; text-align: center; color: #666666; font-size: 12px; background: #f8f9fa; }}
                .button {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 25px 0; font-weight: 600; font-size: 16px; text-align: center; }}
                .otp-code {{ background: #2c3e50; color: white; padding: 20px; font-size: 32px; font-weight: bold; text-align: center; letter-spacing: 12px; margin: 25px 0; border-radius: 8px; font-family: 'Courier New', monospace; }}
                .notice {{ background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 8px; padding: 20px; margin: 25px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 25px 0; color: #856404; }}
                .text-center {{ text-align: center; }}
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
                    <div class="legal">
                        <p style="margin: 0 0 5px 0;">
                            This email was sent to {user_email} because you have an account with Salon Connect.
                        </p>
                        <p style="margin: 0 0 5px 0;">
                            If you didn't request this email, please ignore it.
                        </p>
                        <p style="margin: 0;">
                            <a href="https://saloonconnect.vercel.app/unsubscribe" style="color: #666;">Unsubscribe</a> | 
                            <a href="https://saloonconnect.vercel.app/privacy" style="color: #666;">Privacy Policy</a>
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
                "subject": "Reset Your Salon Connect Password",
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
    def send_verification_email(email: str, first_name: str, verification_url: str):
        """Send email verification email - USING USERNAME NOT PHONE"""
        user_data = {
            'email': email,
            'first_name': first_name
        }
        
        html_content, subject = EmailService.create_email_template(
            "verification", user_data, action_url=verification_url
        )
        
        print(f"[SENDGRID] Sending verification email to: {email}")
        return EmailService.send_email(email, subject, html_content)

    @staticmethod
    def send_password_reset_email(email: str, first_name: str, reset_url: str):
        """Send password reset email - USING USERNAME NOT PHONE"""
        user_data = {
            'email': email,
            'first_name': first_name
        }
        
        html_content, subject = EmailService.create_email_template(
            "password_reset", user_data, action_url=reset_url
        )
        
        print(f"[SENDGRID] Sending password reset email to: {email}")
        return EmailService.send_email(email, subject, html_content)

    @staticmethod
    def send_otp_email(email: str, first_name: str, otp: str):
        """Send OTP for login - USING USERNAME NOT PHONE"""
        user_data = {
            'email': email,
            'first_name': first_name
        }
        
        html_content, subject = EmailService.create_email_template(
            "otp", user_data, otp=otp
        )
        
        print(f"[SENDGRID] Sending OTP email to: {email}")
        return EmailService.send_email(email, subject, html_content)

    # ... [Keep other methods but update them to use email and first_name instead of User object] ...

    @staticmethod
    def generate_verification_token(email: str) -> str:
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'type': 'email_verification'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token

    @staticmethod
    def generate_reset_token(email: str) -> str:
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'password_reset'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token

    @staticmethod
    def verify_token(token: str, token_type: str) -> dict:
        try:
            # Handle bytes token if present
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            elif token.startswith("b'") and token.endswith("'"):
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