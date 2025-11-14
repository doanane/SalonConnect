from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.services.google_oauth_service import google_oauth_service
from app.services.auth import AuthService
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.core.config import settings
import json

router = APIRouter()

@router.get("/google", tags=["Google OAuth"])
async def google_login(request: Request):
    return await google_oauth_service.get_authorization_url(request)

@router.get("/google/callback", tags=["Google OAuth"])
async def google_callback(
    request: Request, 
    db: Session = Depends(get_db)
):
    try:
        google_user = await google_oauth_service.handle_callback(request)
        
        user = db.query(User).filter(User.email == google_user['email']).first()
        
        if not user:
            user = await AuthService.register_google_user(db, google_user)
        
        access_token = create_access_token(data={"user_id": user.id, "email": user.email, "role": user.role.value})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        user_permissions = AuthService.get_user_role_permissions(user.role)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful - Salon Connect</title>
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
                    max-width: 500px;
                }}
                .success {{
                    color: #28a745;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .user-info {{
                    margin: 20px 0;
                }}
                .avatar {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    margin: 0 auto 15px;
                }}
                .role-badge {{
                    display: inline-block;
                    padding: 5px 15px;
                    background: #007bff;
                    color: white;
                    border-radius: 20px;
                    font-size: 14px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">Success</div>
                <h2>Login Successful!</h2>
                
                <div class="user-info">
                    <img class="avatar" src="{google_user.get('picture', '')}" alt="Profile Picture" onerror="this.style.display='none'">
                    <h3>Welcome, {user.first_name} {user.last_name}!</h3>
                    <p>{user.email}</p>
                    <div class="role-badge">{user.role.value.upper()}</div>
                </div>
                
                <p>You have successfully logged in with Google.</p>
                <p>Role: <strong>{user.role.value}</strong></p>
                
                <script>
                    const authData = {{
                        access_token: "{access_token}",
                        refresh_token: "{refresh_token}",
                        user: {{
                            id: {user.id},
                            email: "{user.email}",
                            first_name: "{user.first_name}",
                            last_name: "{user.last_name}",
                            role: "{user.role.value}",
                            is_verified: {str(user.is_verified).lower()},
                            permissions: {json.dumps(user_permissions)}
                        }}
                    }};
                    
                    console.log('Authentication successful:', authData);
                    
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage({{ type: 'oauth_success', data: authData }}, "{settings.FRONTEND_URL}");
                        setTimeout(() => window.close(), 1000);
                    }} else {{
                        localStorage.setItem('salonconnect_auth', JSON.stringify(authData));
                        setTimeout(() => {{
                            window.location.href = '{settings.FRONTEND_URL}/dashboard';
                        }}, 2000);
                    }}
                </script>
                
                <p><small>Redirecting to application...</small></p>
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
            <title>Login Failed - Salon Connect</title>
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
                .error {{
                    color: #dc3545;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">Error</div>
                <h2>Login Failed</h2>
                <p><strong>Error:</strong> {str(e)}</p>
                <button onclick="window.close()" style="
                    background: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                ">Close Window</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/test-oauth", tags=["Google OAuth"])
async def test_oauth_config():
    return {
        "google_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "admin_emails": settings.ADMIN_EMAILS
    }