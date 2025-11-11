from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService
from app.schemas.user import Token

router = APIRouter()

@router.get("/auth/google", tags=["Google OAuth"])
async def start_google_auth():
    """Start Google OAuth login"""
    auth_url = GoogleOAuthService.get_google_auth_url()
    return RedirectResponse(auth_url)

@router.get("/auth/google/callback", response_model=Token, tags=["Google OAuth"])
async def handle_google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback - user logs in here"""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        # Return a proper error page
        html_error = f"""
        <html>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2 style="color: red;">❌ Login Failed</h2>
            <p>Error: {error}</p>
            <a href="/api/auth/google/login" style="background: #4285f4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Try Again</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html_error)
    
    if not code:
        # If no code, redirect back to login
        return RedirectResponse("/api/auth/google/login")
    
    try:
        # Process the Google OAuth and return JWT tokens
        result = await GoogleOAuthService.handle_google_callback(db, code)
        
        # Return success page with tokens
        html_success = f"""
        <html>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2 style="color: green;">✅ Login Successful!</h2>
            <p>Welcome to Salon Connect!</p>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 500px; text-align: left;">
                <h3>Your Access Token:</h3>
                <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px;">{result.access_token}</p>
                <p><strong>Use this token in your Authorization header:</strong></p>
                <p>Authorization: Bearer {result.access_token}</p>
            </div>
            <a href="/docs" style="background: #0f9d58; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to API Docs</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html_success)
        
    except Exception as e:
        html_error = f"""
        <html>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2 style="color: red;">❌ Login Failed</h2>
            <p>Error: {str(e)}</p>
            <a href="/api/auth/google/login" style="background: #4285f4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Try Again</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html_error)
@router.get("/auth/google/debug", tags=["Google OAuth"])
async def debug_google_config():
    """Debug Google OAuth configuration"""
    auth_url = GoogleOAuthService.get_google_auth_url()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth Debug</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            code {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 5px; display: block; overflow-x: auto; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>🔧 Google OAuth Debug</h1>
        
        <div class="info">
            <h3>Current Configuration:</h3>
            <p><strong>Client ID:</strong> {settings.GOOGLE_CLIENT_ID[:30]}...</p>
            <p><strong>Redirect URI:</strong> {settings.GOOGLE_REDIRECT_URI}</p>
            <p><strong>Environment:</strong> {'Development' if settings.DEBUG else 'Production'}</p>
        </div>
        
        <div class="warning">
            <h3>⚠️ Common Issues:</h3>
            <ol>
                <li>Redirect URI in Google Console doesn't match exactly</li>
                <li>Google changes take 5-60 minutes to propagate</li>
                <li>Client ID or Secret is wrong</li>
                <li>OAuth consent screen not configured</li>
            </ol>
        </div>
        
        <h3>Test Links:</h3>
        <ul>
            <li><a href="{auth_url}" target="_blank">Direct Google OAuth Link</a></li>
            <li><a href="/api/auth/google/login">Login Page</a></li>
            <li><a href="https://console.cloud.google.com/apis/credentials" target="_blank">Google Console</a></li>
        </ul>
        
        <h3>Your Redirect URI in Google Console MUST be:</h3>
        <code>{settings.GOOGLE_REDIRECT_URI}</code>
        
        <h3>Full Auth URL:</h3>
        <code>{auth_url}</code>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
    
@router.get("/auth/google/login", tags=["Google OAuth"])
async def google_login_page():
    """Simple login page that redirects to Google OAuth"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login with Google - Salon Connect</title>
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
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 400px;
                width: 90%;
            }
            .google-btn {
                background: #4285f4;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }
            .google-btn:hover {
                background: #357ae8;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>Welcome to Salon Connect</h2>
            <p>Sign in with your Google account to continue</p>
            <a href="/api/auth/google" class="google-btn">Sign in with Google</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)