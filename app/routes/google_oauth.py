from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService, oauth_configured
from app.services.auth import AuthService
from app.core.security import create_access_token
from app.models.user import User
from app.core.config import settings
import secrets

router = APIRouter()

@router.get("/debug", tags=["Google OAuth"])
async def debug_oauth_config():
    """Debug endpoint to check OAuth configuration"""
    config_info = {
        "google_client_id_set": bool(settings.GOOGLE_CLIENT_ID),
        "google_client_secret_set": bool(settings.GOOGLE_CLIENT_SECRET),
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "current_base_url": settings.CURRENT_BASE_URL,
        "is_production": settings.IS_PRODUCTION,
        "frontend_url": settings.FRONTEND_URL,
        "oauth_configured": oauth_configured
    }
    
    
    if settings.GOOGLE_CLIENT_ID:
        config_info["google_client_id_preview"] = settings.GOOGLE_CLIENT_ID[:10] + "..."
    
    return config_info

@router.get("/google", tags=["Google OAuth"])
async def google_login(request: Request):
    """Start Google OAuth login flow"""
    print(" User initiating Google login...")
    return await GoogleOAuthService.get_authorization_url(request)
@router.get("/debug-session", tags=["Google OAuth"])
async def debug_session(request: Request):
    """Debug session state for OAuth"""
    session_data = {
        "session_working": True,
        "oauth_state": request.session.get('oauth_state'),
        "oauth_timestamp": request.session.get('oauth_timestamp'),
        "oauth_flow_started": request.session.get('oauth_flow_started'),
        "all_session_keys": list(request.session.keys())
    }
    return session_data
@router.get("/session-test", tags=["Google OAuth"])
async def session_test(request: Request):
    """Test if sessions are working"""
    if 'test_count' not in request.session:
        request.session['test_count'] = 1
    else:
        request.session['test_count'] += 1
    
    return {
        "session_id": "present" if hasattr(request, 'session') else "missing",
        "test_count": request.session.get('test_count'),
        "all_keys": list(request.session.keys())
    }
@router.get("/google/callback", tags=["Google OAuth"])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        print(" Processing Google OAuth callback...")
        
        
        google_user = await GoogleOAuthService.handle_callback(request)
        
        
        user = db.query(User).filter(User.email == google_user['email']).first()
        
        if not user:
            print(f" Creating new user: {google_user['email']}")
            
            from app.schemas.user import UserCreate
            user_data = UserCreate(
                email=google_user['email'],
                first_name=google_user['first_name'],
                last_name=google_user['last_name'],
                password=f"google_oauth_{secrets.token_urlsafe(8)}",  
                role="customer"
            )
            user = await AuthService.register_google_user(db, user_data, google_user)
        else:
            print(f" Existing user found: {user.email}")
        
        
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email}
        )
        refresh_token = create_access_token(
            data={"user_id": user.id}, 
            expires_delta=timedelta(days=7)
        )
        
        print(f" Login successful for user: {user.email}")
        
        return HTMLResponse(content=f"""
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
                    color: white;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    color: #333;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #28a745;
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
                    border: 3px solid #28a745;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon"></div>
                <h1>Login Successful!</h1>
                
                <div class="user-info">
                    <img class="avatar" src="{google_user.get('picture', '')}" alt="Profile Picture" onerror="this.style.display='none'">
                    <h2>Welcome, {user.first_name} {user.last_name}!</h2>
                    <p>{user.email}</p>
                </div>
                
                <p>You have successfully logged in with Google.</p>
                
                <script>
                    // Send auth data to opener window if exists
                    const authData = {{
                        access_token: "{access_token}",
                        refresh_token: "{refresh_token}",
                        user: {{
                            id: {user.id},
                            email: "{user.email}",
                            first_name: "{user.first_name}",
                            last_name: "{user.last_name}",
                            role: "{user.role}",
                            is_verified: {str(user.is_verified).lower()}
                        }}
                    }};
                    
                    console.log("Auth data:", authData);
                    
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage(authData, "*");
                        setTimeout(() => window.close(), 1000);
                    }} else {{
                        // Store in localStorage and redirect
                        localStorage.setItem('salonconnect_auth', JSON.stringify(authData));
                        setTimeout(() => {{
                            window.location.href = '{settings.FRONTEND_URL}';
                        }}, 3000);
                    }}
                </script>
                
                <p><small>This window will close automatically...</small></p>
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return HTMLResponse(content=f"""
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
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 400px;
                }}
                .error-icon {{
                    font-size: 64px;
                    color: #dc3545;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">❌</div>
                <h1>Login Failed</h1>
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
        """, status_code=400)

@router.get("/login", tags=["Google OAuth"])
async def login_page():
    """Serve Google OAuth login page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Salon Connect - Sign In</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                background: white;
                padding: 50px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 400px;
                width: 90%;
            }
            .logo {
                font-size: 32px;
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
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.3s ease;
                width: 100%;
                margin: 20px 0;
            }
            .google-btn:hover {
                background: #f8f9fa;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transform: translateY(-2px);
            }
            .google-icon {
                width: 20px;
                height: 20px;
                margin-right: 12px;
                background: url('https://developers.google.com/identity/images/g-logo.png') center/contain no-repeat;
            }
            .info {
                margin-top: 30px;
                font-size: 14px;
                color: #666;
                line-height: 1.5;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">💈 Salon Connect</div>
            <h1>Welcome Back</h1>
            <p>Sign in to manage your salon appointments</p>
            
            <a href="/api/auth/google" class="google-btn">
                <div class="google-icon"></div>
                <span>Continue with Google</span>
            </a>
            
            <div class="info">
                <p>By continuing, you agree to our Terms of Service and Privacy Policy.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)