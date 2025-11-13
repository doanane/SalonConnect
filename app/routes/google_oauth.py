from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService, oauth_configured
from app.services.auth import AuthService
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.core.config import settings
import secrets
import json

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

@router.get("/google", tags=["Google OAuth"])
async def google_login(request: Request):
    """Start Google OAuth login flow"""
    print("👤 User initiating Google login...")
    return await GoogleOAuthService.get_authorization_url(request)

@router.get("/google/callback", tags=["Google OAuth"])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback - redirects to role selection for new users"""
    try:
        print("🔄 Processing Google OAuth callback...")
        
        # Get user info from Google
        google_user = await GoogleOAuthService.handle_callback(request)
        
        # Check if user exists in database
        user = db.query(User).filter(User.email == google_user['email']).first()
        
        if user:
            print(f"👤 Existing user found: {user.email}")
            # Existing user - login directly
            access_token = create_access_token(data={"user_id": user.id, "email": user.email})
            refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
            
            return HTMLResponse(content=f"""
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
                        border-radius: 15px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 500px;
                    }}
                    .success-icon {{
                        font-size: 64px;
                        color: #28a745;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1>Welcome back, {user.first_name}!</h1>
                    <p>Login successful as <strong>{user.role.value}</strong>.</p>
                    
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
                                is_verified: {str(user.is_verified).lower()}
                            }}
                        }};
                        
                        if (window.opener && !window.opener.closed) {{
                            window.opener.postMessage(authData, "*");
                            setTimeout(() => window.close(), 1000);
                        }} else {{
                            localStorage.setItem('salonconnect_auth', JSON.stringify(authData));
                            setTimeout(() => {{
                                window.location.href = '{settings.FRONTEND_URL}/dashboard';
                            }}, 2000);
                        }}
                    </script>
                    
                    <p><small>Redirecting to dashboard...</small></p>
                </div>
            </body>
            </html>
            """)
        else:
            print(f"👤 New user detected: {google_user['email']}")
            # New user - redirect to role selection
            google_user_json = json.dumps(google_user)
            
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Complete Registration</title>
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
                        border-radius: 15px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 500px;
                    }}
                    .info-icon {{
                        font-size: 64px;
                        color: #667eea;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="info-icon">🎯</div>
                    <h1>Complete Your Registration</h1>
                    <p>Welcome, {google_user['first_name']}! Please select how you'll use Salon Connect.</p>
                    <p><small>This helps us personalize your experience.</small></p>
                    
                    <script>
                        // Store Google user data temporarily for role selection
                        const googleUser = {google_user_json};
                        localStorage.setItem('pending_google_user', JSON.stringify(googleUser));
                        
                        // Redirect to role selection
                        setTimeout(() => {{
                            window.location.href = '/api/auth/role-selection';
                        }}, 1500);
                    </script>
                    
                    <p><small>Redirecting to role selection...</small></p>
                </div>
            </body>
            </html>
            """)
        
    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <body>
            <div style="text-align: center; padding: 40px;">
                <h1>Login Failed</h1>
                <p>Error: {str(e)}</p>
                <button onclick="window.close()">Close</button>
            </div>
        </body>
        </html>
        """, status_code=400)

@router.get("/role-selection", tags=["Google OAuth"])
async def role_selection_page():
    """Page for new OAuth users to select their role"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Select Your Role - Salon Connect</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
                width: 100%;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 20px;
            }
            .role-option {
                display: block;
                width: 100%;
                padding: 20px;
                margin: 15px 0;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                background: white;
                color: #333;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                text-align: left;
            }
            .role-option:hover {
                border-color: #667eea;
                background: #f8f9ff;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .role-option.selected {
                border-color: #667eea;
                background: #f0f4ff;
            }
            .role-icon {
                font-size: 32px;
                margin-right: 15px;
                vertical-align: middle;
                float: left;
            }
            .role-content {
                overflow: hidden;
            }
            .role-title {
                font-weight: bold;
                display: block;
                font-size: 18px;
                margin-bottom: 5px;
            }
            .role-description {
                font-size: 14px;
                color: #666;
                line-height: 1.4;
            }
            .continue-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 16px 40px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-top: 25px;
                width: 100%;
                transition: background 0.3s ease;
            }
            .continue-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .continue-btn:hover:not(:disabled) {
                background: #5a6fd8;
            }
            .error-message {
                color: #dc3545;
                margin-top: 10px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">💈 Salon Connect</div>
            <h1>How will you use Salon Connect?</h1>
            <p>Select your role to continue with your Google registration</p>
            
            <form id="roleForm" action="/api/auth/complete-google-registration" method="POST">
                <input type="hidden" name="google_data" id="googleData">
                
                <button type="button" class="role-option" onclick="selectRole('customer')">
                    <span class="role-icon">👤</span>
                    <div class="role-content">
                        <span class="role-title">Customer</span>
                        <span class="role-description">I want to book salon services, manage appointments, and discover beauty professionals in my area.</span>
                    </div>
                </button>
                
                <button type="button" class="role-option" onclick="selectRole('vendor')">
                    <span class="role-icon">💼</span>
                    <div class="role-content">
                        <span class="role-title">Salon Owner / Professional</span>
                        <span class="role-description">I want to manage my salon, offer services, handle bookings, and grow my beauty business.</span>
                    </div>
                </button>
                
                <div class="error-message" id="errorMessage">
                    Please select a role to continue
                </div>
                
                <button type="submit" class="continue-btn" id="continueBtn" disabled>
                    Complete Registration with Google
                </button>
            </form>
        </div>

        <script>
            let selectedRole = null;
            
            // Check if we have Google user data
            const googleData = localStorage.getItem('pending_google_user');
            
            if (!googleData) {
                alert('No registration data found. Please start the Google login process again.');
                window.location.href = '/api/auth/login';
            }
            
            function selectRole(role) {
                selectedRole = role;
                
                // Update UI
                document.querySelectorAll('.role-option').forEach(btn => {
                    btn.classList.remove('selected');
                });
                
                event.target.classList.add('selected');
                
                // Update form data
                const userData = JSON.parse(googleData);
                userData.role = role;
                document.getElementById('googleData').value = JSON.stringify(userData);
                
                // Enable continue button and hide error
                document.getElementById('continueBtn').disabled = false;
                document.getElementById('errorMessage').style.display = 'none';
            }
            
            // Form submission handler
            document.getElementById('roleForm').addEventListener('submit', function(e) {
                if (!selectedRole) {
                    e.preventDefault();
                    document.getElementById('errorMessage').style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.post("/complete-google-registration", tags=["Google OAuth"])
async def complete_google_registration(
    request: Request, 
    db: Session = Depends(get_db)
):
    """Complete Google OAuth registration with selected role"""
    try:
        form_data = await request.form()
        google_data_json = form_data.get('google_data')
        
        if not google_data_json:
            raise HTTPException(status_code=400, detail="No user data provided")
        
        google_data = json.loads(google_data_json)
        
        # Create the user with selected role
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            email=google_data['email'],
            first_name=google_data['first_name'],
            last_name=google_data['last_name'],
            password=f"google_oauth_{secrets.token_urlsafe(12)}",
            role=google_data.get('role', 'customer')  # Use selected role
        )
        
        user = await AuthService.register_google_user(db, user_data, google_data)
        
        # Generate tokens
        access_token = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token = create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=7))
        
        # Success page
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Registration Complete - Salon Connect</title>
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
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #28a745;
                    margin-bottom: 20px;
                }}
                .role-badge {{
                    background: #667eea;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">🎉</div>
                <h1>Registration Complete!</h1>
                <p>Welcome to Salon Connect, <strong>{user.first_name}</strong>!</p>
                
                <div class="role-badge">
                    {user.role.value.title() if hasattr(user.role, 'value') else user.role.title()} Account
                </div>
                
                <p>Your account has been successfully created with Google.</p>
                <p>Check your email for a welcome message with getting started tips!</p>
                
                <script>
                    const authData = {{
                        access_token: "{access_token}",
                        refresh_token: "{refresh_token}",
                        user: {{
                            id: {user.id},
                            email: "{user.email}",
                            first_name: "{user.first_name}",
                            last_name: "{user.last_name}",
                            role: "{user.role.value if hasattr(user.role, 'value') else user.role}",
                            is_verified: {str(user.is_verified).lower()},
                            registration_method: "google"
                        }}
                    }};
                    
                    // Send to opener and redirect
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage(authData, "*");
                    }} else {{
                        localStorage.setItem('salonconnect_auth', JSON.stringify(authData));
                    }}
                    
                    // Clear pending data
                    localStorage.removeItem('pending_google_user');
                    
                    setTimeout(() => {{
                        window.location.href = '{settings.FRONTEND_URL}/dashboard';
                    }}, 3000);
                </script>
                
                <p><small>Redirecting to your dashboard...</small></p>
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        print(f"❌ Google registration error: {e}")
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <body>
            <div style="text-align: center; padding: 40px;">
                <h1>Registration Failed</h1>
                <p>Error: {str(e)}</p>
                <button onclick="window.location.href='/api/auth/login'">Try Again</button>
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
                <p>New to Salon Connect? You'll be able to choose your role after signing in with Google.</p>
                <p>By continuing, you agree to our Terms of Service and Privacy Policy.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)