import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.config import settings
from app.models.user import User, UserProfile
from app.core.security import create_access_token
from app.schemas.user import Token

class GoogleOAuthService:
    # Google OAuth endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    
    @staticmethod
    def get_google_auth_url():
        """Generate Google OAuth URL with auto-detected redirect URI"""
        import urllib.parse
        
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        print(f"🔗 [GOOGLE] Environment: {'Production' if settings.IS_PRODUCTION else 'Development'}")
        print(f"🔗 [GOOGLE] Using redirect URI: {redirect_uri}")
        
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        auth_url = f"{GoogleOAuthService.GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
        print(f"🔗 [GOOGLE] Generated auth URL")
        return auth_url
    
    @staticmethod
    async def get_google_tokens(code: str):
        """Exchange authorization code for access token"""
        print(f"🔄 [GOOGLE] Exchanging code for tokens...")
        
        if not code or len(code) < 10:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        print(f"🔧 [GOOGLE] Using redirect URI: {redirect_uri}")
        
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            
            print(f"🔧 [GOOGLE] Making token request to Google...")
            
            try:
                response = await client.post(GoogleOAuthService.GOOGLE_TOKEN_URL, data=data, timeout=30.0)
                print(f"🔧 [GOOGLE] Token response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    print(f"❌ [GOOGLE] Token error {response.status_code}: {error_detail}")
                    
                    try:
                        error_json = response.json()
                        error_message = error_json.get('error_description', error_json.get('error', 'Unknown error'))
                    except:
                        error_message = error_detail
                    
                    raise HTTPException(status_code=400, detail=f"Google OAuth error: {error_message}")
                
                tokens = response.json()
                print(f"✅ [GOOGLE] Successfully received tokens")
                return tokens
                
            except httpx.TimeoutException:
                print(f"❌ [GOOGLE] Request timeout")
                raise HTTPException(status_code=408, detail="Google OAuth timeout. Please try again.")
            except httpx.HTTPError as e:
                print(f"❌ [GOOGLE] HTTP error: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to connect to Google OAuth service")
    
    @staticmethod
    async def get_google_user_info(access_token: str):
        """Get user info from Google using access token"""
        print(f"🔄 [GOOGLE] Getting user info with access token...")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token available")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            try:
                response = await client.get(GoogleOAuthService.GOOGLE_USER_INFO_URL, headers=headers, timeout=30.0)
                print(f"🔧 [GOOGLE] User info response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ [GOOGLE] User info error: {response.text}")
                    raise HTTPException(status_code=400, detail="Failed to get user information from Google")
                
                user_info = response.json()
                print(f"✅ [GOOGLE] Successfully received user info: {user_info.get('email')}")
                return user_info
                
            except httpx.TimeoutException:
                print(f"❌ [GOOGLE] User info request timeout")
                raise HTTPException(status_code=408, detail="Google user info timeout")
            except httpx.HTTPError as e:
                print(f"❌ [GOOGLE] HTTP error getting user info: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to get user info from Google")
    
    @staticmethod
    def find_or_create_user(db: Session, google_user_info: dict):
        """Find existing user or create new user from Google info"""
        email = google_user_info.get("email")
        print(f"🔄 [GOOGLE] Finding/creating user for email: {email}")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user already exists
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"✅ [GOOGLE] User found: {user.email}")
            # User exists, update Google info if needed
            if not user.is_verified:
                user.is_verified = True
                print(f"🔧 [GOOGLE] Marked user as verified")
            
            # Update profile picture if available from Google
            google_picture = google_user_info.get("picture")
            if google_picture and user.profile:
                user.profile.profile_picture = google_picture
                print(f"🔧 [GOOGLE] Updated profile picture")
            
            db.commit()
            return user
        
        else:
            print(f"🆕 [GOOGLE] Creating new user for: {email}")
            # Create new user - WITHOUT auth_provider field
            user = User(
                email=email,
                first_name=google_user_info.get("given_name", "Google"),
                last_name=google_user_info.get("family_name", "User"),
                is_verified=True,
                is_active=True
                # REMOVED: auth_provider="google"
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create user profile
            profile = UserProfile(
                user_id=user.id,
                profile_picture=google_user_info.get("picture")
            )
            db.add(profile)
            db.commit()
            
            print(f"✅ [GOOGLE] Created new user: {user.email}")
            return user
    
    @staticmethod
    async def handle_google_callback(db: Session, code: str):
        """Handle Google OAuth callback"""
        print("🚀 [GOOGLE] Starting OAuth callback handling...")
        
        # Get tokens from Google
        tokens = await GoogleOAuthService.get_google_tokens(code)
        access_token = tokens.get("access_token")
        
        if not access_token:
            print("❌ [GOOGLE] No access token received")
            raise HTTPException(status_code=400, detail="No access token received from Google")
        
        print(f"✅ [GOOGLE] Received access token")
        
        # Get user info from Google
        user_info = await GoogleOAuthService.get_google_user_info(access_token)
        
        # Find or create user in database
        user = GoogleOAuthService.find_or_create_user(db, user_info)
        
        # Generate JWT tokens
        access_token_jwt = create_access_token(data={"user_id": user.id, "email": user.email})
        refresh_token_jwt = create_access_token(
            data={"user_id": user.id}, 
            expires_delta=timedelta(days=7)
        )
        
        print(f"✅ [GOOGLE] Generated JWT tokens for user: {user.email}")
        
        return Token(
            access_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            token_type="bearer"
        )