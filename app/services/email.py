import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import jwt
from datetime import datetime, timedelta

class EmailService:
    @staticmethod
    def send_password_reset_email(email: str, reset_token: str):
        """Send password reset email to user"""
        try:
            # Email content
            subject = "Password Reset Request - Salon Connect"
            reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
            
            html_content = f"""
            <html>
                <body>
                    <h2>Salon Connect - Password Reset</h2>
                    <p>You requested to reset your password. Click the link below to set a new password:</p>
                    <a href="{reset_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.DEFAULT_FROM_EMAIL
            msg['To'] = email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    @staticmethod
    def generate_reset_token(email: str) -> str:
        """Generate JWT token for password reset"""
        payload = {
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'type': 'password_reset'
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    @staticmethod
    def verify_reset_token(token: str) -> dict:
        """Verify password reset token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('type') != 'password_reset':
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None