from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.google_oauth import GoogleOAuthService
from app.schemas.user import Token
from app.core.config import settings

router = APIRouter(prefix="/auth/google", tags=["Google Authentication"])

@router.get("/")
async def start_google_auth():
    """Start Google OAuth flow - redirects to Google login"""
    print("🔗 [GOOGLE AUTH] Generating Google OAuth URL...")
    auth_url = GoogleOAuthService.get_google_auth_url()
    print(f"🔗 [GOOGLE AUTH] Redirecting to Google OAuth...")
    return RedirectResponse(auth_url)

@router.get("/callback", response_model=Token)
async def handle_google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback with authorization code"""
    print("🔄 [GOOGLE CALLBACK] Handling callback...")
    
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    print(f"🔧 [GOOGLE CALLBACK] Code received: {'Yes' if code else 'No'}")
    print(f"🔧 [GOOGLE CALLBACK] Error: {error}")
    
    if error:
        print(f"❌ [GOOGLE CALLBACK] OAuth error: {error}")
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    
    if not code:
        print("❌ [GOOGLE CALLBACK] No authorization code provided")
        raise HTTPException(
            status_code=400, 
            detail="No authorization code received from Google."
        )
    
    try:
        print("🔄 [GOOGLE CALLBACK] Processing authorization code...")
        result = await GoogleOAuthService.handle_google_callback(db, code)
        print("✅ [GOOGLE CALLBACK] Successfully processed callback")
        return result
    except Exception as e:
        print(f"❌ [GOOGLE CALLBACK] Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ADD THESE NEW ENDPOINTS FOR LOCAL TESTING

@router.get("/local-test")
async def local_oauth_test():
    """Local testing endpoint with HTML interface"""
    auth_url = GoogleOAuthService.get_google_auth_url()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth Local Test</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .container {{ background: #f5f5f5; padding: 20px; border-radius: 10px; }}
            .step {{ margin: 15px 0; padding: 10px; background: white; border-radius: 5px; }}
            .button {{ background: #4285f4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            .info {{ background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Google OAuth Local Test</h1>
            <div class="info">
                <strong>Environment:</strong> {'Production' if settings.IS_PRODUCTION else 'Development'}<br>
                <strong>Redirect URI:</strong> {settings.GOOGLE_REDIRECT_URI}
            </div>
            
            <div class="step">
                <h3>🚀 Step 1: Start OAuth Flow</h3>
                <p>Click the button below to start Google OAuth:</p>
                <a class="button" href="{auth_url}" target="_blank">Sign in with Google</a>
            </div>
            
            <div class="step">
                <h3>📋 Step 2: Copy the Authorization Code</h3>
                <p>After logging in with Google, you'll be redirected to a URL that looks like:</p>
                <code>{settings.GOOGLE_REDIRECT_URI}?code=4/0A...</code>
                <p><strong>Copy the entire URL from your browser address bar.</strong></p>
            </div>
            
            <div class="step">
                <h3>🔧 Step 3: Test with the Code</h3>
                <p>Paste the URL here to extract and test the code:</p>
                <form action="/api/users/auth/google/process-url" method="get">
                    <input type="text" name="redirect_url" placeholder="Paste the full redirect URL here" style="width: 100%; padding: 10px; margin: 10px 0;">
                    <button type="submit" style="background: #4285f4; color: white; padding: 10px 20px; border: none; border-radius: 5px;">Test OAuth</button>
                </form>
            </div>
            
            <div class="step">
                <h3>🎯 Direct Code Test</h3>
                <p>Or test directly with a code:</p>
                <form action="/api/users/auth/google/direct-test" method="get">
                    <input type="text" name="code" placeholder="Paste just the code parameter" style="width: 100%; padding: 10px; margin: 10px 0;">
                    <button type="submit" style="background: #0f9d58; color: white; padding: 10px 20px; border: none; border-radius: 5px;">Test with Code</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/process-url")
async def process_redirect_url(request: Request, db: Session = Depends(get_db)):
    """Process a redirect URL and extract the code"""
    redirect_url = request.query_params.get("redirect_url", "")
    
    if not redirect_url:
        return {"error": "No redirect URL provided"}
    
    print(f"🔧 [PROCESS URL] Processing: {redirect_url}")
    
    # Extract code from URL
    from urllib.parse import urlparse, parse_qs
    try:
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        code = query_params.get('code', [None])[0]
        
        if not code:
            return {"error": "No code found in the URL"}
        
        print(f"✅ [PROCESS URL] Extracted code: {code[:20]}...")
        
        # Process the code
        result = await GoogleOAuthService.handle_google_callback(db, code)
        
        return {
            "status": "success",
            "message": "✅ OAuth authentication successful!",
            "code_received": True,
            "tokens": result
        }
        
    except Exception as e:
        print(f"❌ [PROCESS URL] Error: {str(e)}")
        return {"error": f"Failed to process URL: {str(e)}"}

@router.get("/direct-test")
async def direct_code_test(request: Request, db: Session = Depends(get_db)):
    """Test OAuth directly with a code parameter"""
    code = request.query_params.get("code", "")
    
    if not code:
        return {"error": "No code provided"}
    
    print(f"🔧 [DIRECT TEST] Testing with code: {code[:20]}...")
    
    try:
        result = await GoogleOAuthService.handle_google_callback(db, code)
        
        return {
            "status": "success", 
            "message": "✅ OAuth authentication successful!",
            "tokens": result
        }
        
    except Exception as e:
        print(f"❌ [DIRECT TEST] Error: {str(e)}")
        return {"error": f"OAuth failed: {str(e)}"}

@router.get("/manual-test")
async def manual_oauth_test():
    """Manual OAuth test with step-by-step instructions"""
    auth_url = GoogleOAuthService.get_google_auth_url()
    
    return {
        "environment": "development" if settings.DEBUG else "production",
        "base_url": settings.CURRENT_BASE_URL,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "instructions": [
            "1. Visit this URL in your browser:",
            f"   {auth_url}",
            "2. Login with your Google account",
            "3. After login, you'll be redirected to a URL like:",
            f"   {settings.GOOGLE_REDIRECT_URI}?code=4/0A...",
            "4. Copy the ENTIRE redirect URL from your browser address bar",
            "5. Use this endpoint to process it:",
            f"   GET /api/users/auth/google/process-url?redirect_url=YOUR_REDIRECT_URL",
            "6. Or extract just the code and use:",
            f"   GET /api/users/auth/google/direct-test?code=YOUR_CODE"
        ],
        "test_endpoints": {
            "local_test_ui": f"{settings.CURRENT_BASE_URL}/api/users/auth/google/local-test",
            "process_url": f"{settings.CURRENT_BASE_URL}/api/users/auth/google/process-url",
            "direct_test": f"{settings.CURRENT_BASE_URL}/api/users/auth/google/direct-test"
        }
    }

# Keep your existing endpoints...
@router.get("/info")
async def get_oauth_info():
    """Get OAuth configuration info for debugging"""
    return {
        "environment": "production" if settings.IS_PRODUCTION else "development",
        "debug_mode": settings.DEBUG,
        "base_url": settings.CURRENT_BASE_URL,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "client_id_set": bool(settings.GOOGLE_CLIENT_ID),
        "client_secret_set": bool(settings.GOOGLE_CLIENT_SECRET),
    }

@router.get("/mobile-auth-url")
async def get_mobile_auth_url():
    """Get Google OAuth URL for mobile apps"""
    auth_url = GoogleOAuthService.get_google_auth_url()
    return {
        "auth_url": auth_url,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "environment": "production" if settings.IS_PRODUCTION else "development"
    }

@router.post("/mobile-callback", response_model=Token)
async def handle_mobile_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback from mobile apps"""
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    try:
        result = await GoogleOAuthService.handle_google_callback(db, code)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))