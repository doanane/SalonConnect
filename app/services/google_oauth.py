from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import HTTPException, Request
from app.core.config import settings

oauth = OAuth()

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

class GoogleOAuthService:
    @staticmethod
    async def get_authorization_url(request: Request):
        try:
            print(f"🚀 [PRODUCTION] OAuth redirect to: {settings.GOOGLE_REDIRECT_URI}")
            return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)
        except Exception as e:
            print(f"❌ OAuth error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

    @staticmethod
    async def handle_callback(request: Request):
        try:
            print("🚀 [PRODUCTION] Handling OAuth callback...")
            token = await oauth.google.authorize_access_token(request)
            user_info = token.get('userinfo')
            
            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
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
            print(f"❌ Authentication error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")