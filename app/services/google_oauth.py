from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import HTTPException, Request
from app.core.config import settings

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
        print(" Google OAuth configured successfully")
        print(f" Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
        return True
    except Exception as e:
        print(f"Failed to setup Google OAuth: {e}")
        return False

# Setup OAuth when module loads
oauth_configured = setup_google_oauth()

class GoogleOAuthService:
    @staticmethod
    async def get_authorization_url(request: Request):
        try:
            if not oauth_configured:
                raise HTTPException(status_code=500, detail="Google OAuth not configured properly")
            
            print(f" Starting OAuth flow...")
            
            # Generate a secure state parameter
            state = secrets.token_urlsafe(32)
            
            # Store state in session with timestamp
            request.session['oauth_state'] = state
            request.session['oauth_timestamp'] = time.time()
            request.session['oauth_flow_started'] = True
            
            # Force session save
            # In Starlette, we need to ensure the session is saved
            if hasattr(request.session, '_saver'):
                await request.session._saver()
            
            print(f"Generated state: {state}")
            print(f" Session after setting state: {list(request.session.keys())}")
            print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
            
            # Use the original authlib method but ensure it uses our state
            redirect_response = await oauth.google.authorize_redirect(
                request, 
                settings.GOOGLE_REDIRECT_URI,
                state=state
            )
            
            print(f" Authorization URL generated with state: {state}")
            return redirect_response
            
        except Exception as e:
            print(f"Error generating authorization URL: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to start OAuth: {str(e)}")

    @staticmethod
    async def handle_callback(request: Request):
        try:
            print(" Processing OAuth callback...")
            print(f"Full callback URL: {request.url}")
            print(f" Query parameters: {dict(request.query_params)}")
            
            # Get state from query parameters
            incoming_state = request.query_params.get('state')
            authorization_code = request.query_params.get('code')
            error = request.query_params.get('error')
            
            if error:
                error_description = request.query_params.get('error_description', 'No description')
                print(f"OAuth error from Google: {error} - {error_description}")
                raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
            
            print(f"Incoming state from Google: {incoming_state}")
            print(f" Authorization code received: {bool(authorization_code)}")
            
            # Get stored state from session
            stored_state = request.session.get('oauth_state')
            stored_timestamp = request.session.get('oauth_timestamp')
            
            print(f" Stored state from session: {stored_state}")
            print(f" Stored timestamp: {stored_timestamp}")
            print(f" All session keys: {list(request.session.keys())}")
            
            # Manual state verification
            if not incoming_state:
                raise HTTPException(status_code=400, detail="Missing state parameter from Google")
            
            if not stored_state:
                raise HTTPException(
                    status_code=400, 
                    detail="No OAuth state found in session. This usually happens if: "
                           "(1) You refreshed the page during OAuth flow, "
                           "(2) Used a different browser/tab, or "
                           "(3) The session expired."
                )
            
            if incoming_state != stored_state:
                print(f"STATE MISMATCH DETECTED!")
                print(f"   Incoming from Google: {incoming_state}")
                print(f"   Stored in session: {stored_state}")
                print(f"   Match: {incoming_state == stored_state}")
                
                # Clean up the invalid state
                if 'oauth_state' in request.session:
                    del request.session['oauth_state']
                if 'oauth_timestamp' in request.session:
                    del request.session['oauth_timestamp']
                
                raise HTTPException(
                    status_code=400, 
                    detail="Security verification failed. The OAuth session may have expired or there was a browser issue. Please try logging in again."
                )
            
            # Check if state is too old (10 minutes)
            if stored_timestamp and (time.time() - stored_timestamp) > 600:
                print(f"State too old: {time.time() - stored_timestamp} seconds")
                raise HTTPException(status_code=400, detail="OAuth session expired. Please try logging in again.")
            
            print(" State verification passed!")
            
            # Now proceed with token exchange using authlib
            print(" Exchanging authorization code for access token...")
            token = await oauth.google.authorize_access_token(request)
            print(" Access token received successfully")
            
            # Get user info from Google
            user_info = token.get('userinfo')
            if not user_info:
                print("No user info in token response")
                raise HTTPException(status_code=400, detail="Failed to get user information from Google")
            
            print(f" User authenticated: {user_info.email}")
            
            print(f"🚀 [PRODUCTION] User authenticated: {user_info.email}")
            
            return {
                'email': user_info.email,
                'first_name': user_info.given_name,
                'last_name': user_info.family_name,
                'picture': user_info.picture,
                'google_id': user_info.sub,
                'email_verified': user_info.email_verified
            }
            
        except OAuthError as e:
            print(f"❌ OAuthError: {str(e)}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")
        except Exception as e:
            print(f"OAuth callback error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
