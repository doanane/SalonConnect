from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService
from app.services.auth import AuthService
from app.core.security import create_access_token
from app.models.user import User
import json

router = APIRouter()

@router.get("/google")
async def google_login(request: Request):
    return await GoogleOAuthService.get_authorization_url(request)

@router.get("/google/callback")
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
                password="google_oauth",
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
                .user-avatar {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    margin: 0 auto 15px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h2>Login Successful!</h2>
                <div>
                    <img class="user-avatar" src="{google_user.get('picture', '')}" alt="User Avatar">
                    <h3>Welcome, {user.first_name}!</h3>
                    <p>You have successfully logged in with Google.</p>
                </div>
                <p>You can close this window and return to the app.</p>
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
                <div class="error-icon">✗</div>
                <h2>Login Failed</h2>
                <p>Error: {str(e)}</p>
                <button onclick="window.close()">Close</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/login-page")
async def login_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Salon Connect - Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 350px;
            }
            .logo {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 30px;
            }
            .google-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                background: white;
                color: #757575;
                border: 2px solid #dadce0;
                padding: 12px 24px;
                border-radius: 4px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.3s;
                width: 100%;
            }
            .google-btn:hover {
                background: #f8f9fa;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .google-icon {
                background: url('https://developers.google.com/identity/images/g-logo.png') center/contain no-repeat;
                width: 18px;
                height: 18px;
                margin-right: 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Salon Connect</div>
            <h2>Welcome Back</h2>
            <p>Sign in to continue to Salon Connect</p>
            <a href="/api/auth/google" class="google-btn">
                <div class="google-icon"></div>
                <span>Sign in with Google</span>
            </a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)