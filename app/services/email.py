import smtplib
import jwt
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.core.config import settings
import os

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SMTP with comprehensive debugging"""
        try:
            print(f"🔧 [EMAIL SERVICE] Starting email send to: {to_email}")
            print(f"🔧 [EMAIL SERVICE] SMTP Config - Host: {settings.SMTP_HOST}, Port: {settings.SMTP_PORT}")
            print(f"🔧 [EMAIL SERVICE] SMTP User: {settings.SMTP_USER}")
            print(f"🔧 [EMAIL SERVICE] From Email: {settings.FROM_EMAIL}")
            print(f"🔧 [EMAIL SERVICE] Running on Render: {'RENDER' in os.environ}")
            
            # Validate SMTP configuration
            if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASS]):
                print("❌ [EMAIL SERVICE] Missing SMTP configuration")
                return False

            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.FROM_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            print(f"🔧 [EMAIL SERVICE] Attempting SMTP connection...")
            
            # Try different connection methods
            try:
                # Method 1: Direct SSL connection (preferred)
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                    print(f"✅ [EMAIL SERVICE] SMTP SSL connection established")
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    print(f"✅ [EMAIL SERVICE] SMTP login successful")
                    server.send_message(msg)
                    print(f"✅ [EMAIL SERVICE] Message sent successfully")
                    
            except Exception as ssl_error:
                print(f"⚠️ [EMAIL SERVICE] SSL connection failed: {ssl_error}")
                print(f"🔧 [EMAIL SERVICE] Trying TLS connection...")
                
                # Method 2: TLS connection
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                    server.starttls()
                    print(f"✅ [EMAIL SERVICE] TLS connection established")
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    print(f"✅ [EMAIL SERVICE] SMTP login successful")
                    server.send_message(msg)
                    print(f"✅ [EMAIL SERVICE] Message sent successfully")
            
            print(f"✅ [EMAIL SERVICE] Email sent successfully to: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ [EMAIL SERVICE] SMTP Authentication failed: {str(e)}")
            print(f"❌ [EMAIL SERVICE] This usually means:")
            print(f"❌ [EMAIL SERVICE] 1. Wrong email password")
            print(f"❌ [EMAIL SERVICE] 2. 2FA is enabled but no app password is used")
            print(f"❌ [EMAIL SERVICE] 3. Less secure apps access is disabled")
            return False
            
        except Exception as e:
            print(f"❌ [EMAIL SERVICE] All connection methods failed: {str(e)}")
            import traceback
            print(f"❌ [EMAIL SERVICE] Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    def generate_verification_token(email: str) -> str:
        """Generate JWT token for email verification"""
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'type': 'email_verification'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        # Ensure token is string, not bytes
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token

    @staticmethod
    def generate_reset_token(email: str) -> str:
        """Generate JWT token for password reset"""
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'password_reset'
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        # Ensure token is string, not bytes
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token

    @staticmethod
    def verify_token(token: str, token_type: str) -> dict:
        """Verify JWT token"""
        try:
            # Clean the token if it has b' prefix
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
        """Verify password reset token"""
        return EmailService.verify_token(token, 'password_reset')

    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def send_verification_email(user, verification_url: str):
        """Send email verification email"""
        subject = "Verify Your Email - Salon Connect"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Salon Connect! 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hello {getattr(user, 'first_name', 'there')},</h2>
                    <p>Thank you for registering with Salon Connect. To complete your registration and start booking appointments, please verify your email address by clicking the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p>This verification link will expire in 24 hours.</p>
                    <p>If you didn't create an account with Salon Connect, please ignore this email.</p>
                    
                    <p>Best regards,<br>The Salon Connect Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 Salon Connect. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        print(f"📧 [EMAIL SERVICE] Sending verification email to: {getattr(user, 'email', 'unknown')}")
        print(f"📧 [EMAIL SERVICE] Verification URL: {verification_url}")
        return EmailService.send_email(getattr(user, 'email', ''), subject, html_content)

    @staticmethod
    def send_password_reset_email(user, reset_url: str):
        """Send password reset email"""
        subject = "Reset Your Password - Salon Connect"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {getattr(user, 'first_name', 'there')},</h2>
                    <p>We received a request to reset your password for your Salon Connect account. Click the button below to create a new password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </div>
                    
                    <p>This reset link will expire in 1 hour.</p>
                    <p>If you didn't request a password reset, please ignore this email. Your account remains secure.</p>
                    
                    <p>Best regards,<br>The Salon Connect Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 Salon Connect. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        print(f"📧 [EMAIL SERVICE] Sending password reset email to: {getattr(user, 'email', 'unknown')}")
        print(f"📧 [EMAIL SERVICE] Reset URL: {reset_url}")
        return EmailService.send_email(getattr(user, 'email', ''), subject, html_content)

    @staticmethod
    def send_otp_email(user, otp: str):
        """Send OTP for login"""
        subject = "Your Login OTP - Salon Connect"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-code {{ background: #333; color: white; padding: 15px; font-size: 32px; font-weight: bold; text-align: center; letter-spacing: 10px; margin: 20px 0; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your Login OTP</h1>
                </div>
                <div class="content">
                    <h2>Hello {getattr(user, 'first_name', 'there')},</h2>
                    <p>Use the following OTP to log in to your Salon Connect account:</p>
                    
                    <div class="otp-code">{otp}</div>
                    
                    <p>This OTP will expire in 10 minutes.</p>
                    <p>If you didn't request this OTP, please ignore this email.</p>
                    
                    <p>Best regards,<br>The Salon Connect Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 Salon Connect. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        print(f"📧 [EMAIL SERVICE] Sending OTP email to: {getattr(user, 'email', 'unknown')}")
        print(f"📧 [EMAIL SERVICE] OTP: {otp}")
        return EmailService.send_email(getattr(user, 'email', ''), subject, html_content)