import secrets
import time
from typing import Dict, Optional

# Simple in-memory session storage for OAuth state
# This works around Render's free tier session limitations
_oauth_sessions: Dict[str, dict] = {}

class OAuthSessionManager:
    @staticmethod
    def create_oauth_session() -> str:
        """Create a new OAuth session and return session ID"""
        session_id = secrets.token_urlsafe(32)
        _oauth_sessions[session_id] = {
            'created_at': time.time(),
            'state': secrets.token_urlsafe(32),
            'used': False
        }
        return session_id
    
    @staticmethod
    def get_oauth_state(session_id: str) -> Optional[str]:
        """Get state for session ID"""
        if session_id not in _oauth_sessions:
            return None
        
        session_data = _oauth_sessions[session_id]
        
        # Check if session is expired (10 minutes)
        if time.time() - session_data['created_at'] > 600:
            del _oauth_sessions[session_id]
            return None
        
        return session_data['state']
    
    @staticmethod
    def validate_oauth_state(session_id: str, state: str) -> bool:
        """Validate state and mark session as used"""
        if session_id not in _oauth_sessions:
            return False
        
        session_data = _oauth_sessions[session_id]
        
        # Check if expired
        if time.time() - session_data['created_at'] > 600:
            del _oauth_sessions[session_id]
            return False
        
        # Check if already used
        if session_data['used']:
            del _oauth_sessions[session_id]
            return False
        
        # Check state match
        if session_data['state'] != state:
            return False
        
        # Mark as used
        session_data['used'] = True
        return True
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, data in _oauth_sessions.items()
            if current_time - data['created_at'] > 600
        ]
        for session_id in expired_sessions:
            del _oauth_sessions[session_id]