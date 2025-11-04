import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

def send_email(to_email: str, subject: str, body: str):
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'html'))
        
        # Create server
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        # Send email
        text = msg.as_string()
        server.sendmail(settings.FROM_EMAIL, to_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_welcome_email(email: str, name: str):
    subject = "Welcome to Salon Connect!"
    body = f"""
    <html>
    <body>
        <h2>Welcome to Salon Connect, {name}!</h2>
        <p>Thank you for joining our platform. We're excited to have you on board!</p>
        <p>Get started by exploring salons in your area and booking your first appointment.</p>
        <br>
        <p>Best regards,<br>The Salon Connect Team</p>
    </body>
    </html>
    """
    return send_email(email, subject, body)

def send_booking_confirmation(email: str, booking_details: dict):
    subject = "Booking Confirmation - Salon Connect"
    body = f"""
    <html>
    <body>
        <h2>Booking Confirmed!</h2>
        <p>Your booking has been confirmed successfully.</p>
        <p><strong>Booking Details:</strong></p>
        <ul>
            <li>Salon: {booking_details.get('salon_name')}</li>
            <li>Service: {booking_details.get('service_name')}</li>
            <li>Date: {booking_details.get('booking_date')}</li>
            <li>Time: {booking_details.get('start_time')}</li>
            <li>Total: ${booking_details.get('total_price')}</li>
        </ul>
        <br>
        <p>Thank you for choosing Salon Connect!</p>
    </body>
    </html>
    """
    return send_email(email, subject, body)