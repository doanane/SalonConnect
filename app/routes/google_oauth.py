from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService
from app.services.auth import AuthService
from app.core.security import create_access_token
from app.models.user import User
from app.core.config import settings
import secrets

router = APIRouter()

@router.get("/google", tags=["Google OAuth"])
async def google_login(request: Request):
    return await GoogleOAuthService.get_authorization_url(request)

@router.get("/google/callback", tags=["Google OAuth"])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        google_user = await GoogleOAuthService.handle_callback(request)
        
        user = db.query(User).filter(User.email == google_user['email']).first()
        
        if not user:
            from app.schemas.user import UserCreate
            user_data = UserCreate(
                email=google_user['email'],
                first_name=google_user['first_name'],
                last_name=google_user['last_name'],
                password=f"google_oauth_{secrets.token_urlsafe(8)}",
                role="customer"
            )
            user = await AuthService.register_google_user(db, user_data, google_user)
        
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 48px;
                    color: #28a745;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">Success</div>
                <h2>Login Successful!</h2>
                <p>Welcome, {user.first_name}!</p>
                <p>You have successfully logged in with Google.</p>
                <script>
                    const authData = {{
                        access_token: "{access_token}",
                        refresh_token: "{refresh_token}",
                        user: {{
                            id: {user.id},
                            email: "{user.email}",
                            first_name: "{user.first_name}",
                            last_name: "{user.last_name}",
                            role: "{user.role}"
                        }}
                    }};
                    
                    if (window.opener) {{
                        window.opener.postMessage(authData, "*");
                        window.close();
                    }} else {{
                        localStorage.setItem('auth_data', JSON.stringify(authData));
                        setTimeout(() => {{
                            window.location.href = '{settings.FRONTEND_URL}';
                        }}, 2000);
                    }}
                </script>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Failed</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .error-icon {{
                    font-size: 48px;
                    color: #dc3545;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">Error</div>
                <h2>Login Failed</h2>
                <p>Error: {str(e)}</p>
                <button onclick="window.close()">Close</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)