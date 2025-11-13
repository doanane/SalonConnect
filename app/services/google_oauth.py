from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from app.core.config import settings
import secrets
import time
import httpx

# Initialize OAuth
oauth = OAuth()

def setup_google_oauth():
    """Setup Google OAuth configuration"""
    try:
        # Make sure we have the required credentials
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            print("Google OAuth credentials not found!")
            return False
            
        oauth.register(
            name='google',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'email profile openid',
                'redirect_uri': settings.GOOGLE_REDIRECT_URI
            }
        )
        print("Google OAuth configured successfully")
        print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
        return True
    except Exception as e:
        print(f"Failed to setup Google OAuth: {e}")
        return False

# Setup OAuth when module loads
oauth_configured = setup_google_oauth()

class GoogleOAuthService:
    @staticmethod
    async def get_authorization_url(request: Request):
        """Generate Google OAuth authorization URL - COMPLETELY MANUAL"""
        try:
            if not oauth_configured:
                raise HTTPException(status_code=500, detail="Google OAuth not configured properly")
            
            print(f"Starting OAuth flow...")
            
            # Generate a secure state parameter
            state = secrets.token_urlsafe(32)
            nonce = secrets.token_urlsafe(32)
            
            # Store state in session
            request.session['oauth_state'] = state
            request.session['oauth_timestamp'] = time.time()
            
            print(f"Generated state: {state}")
            print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
            
            # Build the Google OAuth URL MANUALLY to ensure control
            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={settings.GOOGLE_CLIENT_ID}&"
                f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
                "response_type=code&"
                "scope=email%20profile%20openid&"
                f"state={state}&"
                f"nonce={nonce}&"
                "access_type=offline&"
                "prompt=select_account"
            )
            
            print(f"Manual OAuth URL generated")
            print(f"Final OAuth URL: {auth_url}")
            
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=auth_url)
            
        except Exception as e:
            print(f"Error generating authorization URL: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to start OAuth: {str(e)}")

    @staticmethod
    async def handle_callback(request: Request):
        """Handle Google OAuth callback"""
        try:
            print("Processing OAuth callback...")
            print(f"Full callback URL: {request.url}")
            print(f"All query parameters: {dict(request.query_params)}")
            
            # Check for OAuth errors from Google first
            error = request.query_params.get('error')
            if error:
                error_description = request.query_params.get('error_description', 'No description')
                print(f"OAuth error from Google: {error} - {error_description}")
                raise HTTPException(status_code=400, detail=f"Google OAuth error: {error_description}")
            
            # Get the authorization code and state
            code = request.query_params.get('code')
            incoming_state = request.query_params.get('state')
            
            print(f"Incoming state from Google: {incoming_state}")
            print(f"Authorization code from Google: {code}")
            
            # If no code or state, this might be the initial redirect
            if not code and not incoming_state:
                print("No authorization code or state received from Google")
                print(" This usually means:")
                print("   - Redirect URI mismatch in Google Console")
                print("   - OAuth consent screen not configured")
                print("   - Google app not published or in testing mode")
                raise HTTPException(
                    status_code=400, 
                    detail="No authorization data received from Google. Please check your OAuth configuration."
                )
            
            if not code:
                raise HTTPException(status_code=400, detail="No authorization code received from Google")
            
            if not incoming_state:
                raise HTTPException(status_code=400, detail="No state parameter received from Google")
            
            # Get stored state from session
            stored_state = request.session.get('oauth_state')
            stored_timestamp = request.session.get('oauth_timestamp')
            
            print(f"Stored state from session: {stored_state}")
            print(f"Stored timestamp: {stored_timestamp}")
            
            # Verify state
            if not stored_state:
                raise HTTPException(status_code=400, detail="No OAuth session found. Please start the login process again.")
            
            if incoming_state != stored_state:
                print(f"STATE MISMATCH!")
                print(f"   Incoming: {incoming_state}")
                print(f"   Stored: {stored_state}")
                raise HTTPException(status_code=400, detail="Security verification failed")
            
            # Check if state is too old
            if stored_timestamp and (time.time() - stored_timestamp) > 600:
                raise HTTPException(status_code=400, detail="Session expired")
            
            print("State verification passed!")
            
            # MANUAL token exchange
            print("Exchanging authorization code for access token...")
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        'client_id': settings.GOOGLE_CLIENT_ID,
                        'client_secret': settings.GOOGLE_CLIENT_SECRET,
                        'code': code,
                        'grant_type': 'authorization_code',
                        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                    }
                )
                
                if token_response.status_code != 200:
                    print(f"Token exchange failed: {token_response.text}")
                    raise HTTPException(status_code=400, detail="Failed to exchange authorization code for token")
                
                token_data = token_response.json()
                print("Access token received")
            
            # Get user info manually
            async with httpx.AsyncClient() as client:
                userinfo_response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                
                if userinfo_response.status_code != 200:
                    raise HTTPException(status_code=400, detail="Failed to get user information")
                
                user_info = userinfo_response.json()
                print(f"User info received: {user_info['email']}")
            
            # Clean up session
            if 'oauth_state' in request.session:
                del request.session['oauth_state']
            if 'oauth_timestamp' in request.session:
                del request.session['oauth_timestamp']
            
            return {
                'email': user_info['email'],
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
                'picture': user_info.get('picture', ''),
                'google_id': user_info['sub'],
                'email_verified': user_info.get('email_verified', False)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"OAuth callback error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")