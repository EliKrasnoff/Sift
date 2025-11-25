from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from flask import session, redirect, url_for, request
from config import Config
from models import db, User
from datetime import datetime
import os

# Disable HTTPS requirement for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


class GoogleOAuth:
    """Handle Google OAuth 2.0 flow"""
    
    @staticmethod
    def create_flow():
        """Create OAuth flow instance"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": Config.GOOGLE_CLIENT_ID,
                    "client_secret": Config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [Config.REDIRECT_URI]
                }
            },
            scopes=Config.SCOPES,
            redirect_uri=Config.REDIRECT_URI
        )
        return flow
    
    @staticmethod
    def get_authorization_url():
        """Generate the authorization URL to redirect user to"""
        flow = GoogleOAuth.create_flow()
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to ensure we get refresh token
        )
        
        # Store state in session for security
        session['state'] = state
        
        return authorization_url
    
    @staticmethod
    def handle_callback(authorization_response):
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:
            authorization_response: The full callback URL
            
        Returns:
            User object or None if failed
        """
        # Verify state to prevent CSRF
        state = session.get('state')
        if not state:
            raise ValueError("No state in session")
        
        # Create flow and fetch token
        flow = GoogleOAuth.create_flow()
        flow.fetch_token(authorization_response=authorization_response)
        
        # Get credentials
        credentials = flow.credentials
        
        # Get user info from Google using People API
        from googleapiclient.discovery import build

        # First, make sure we have valid credentials
        if not credentials or not credentials.token:
            raise ValueError("Failed to obtain credentials from Google")

        # Build the oauth2 service with the credentials
        oauth2_service = build('oauth2', 'v2', credentials=credentials)

        # Get user info
        try:
            user_info = oauth2_service.userinfo().get().execute()
        except Exception as e:
            print(f"Error getting user info: {e}")
            print(f"Credentials token: {credentials.token}")
            print(f"Credentials valid: {credentials.valid}")
            raise
        
        # Create or update user in database
        user = User.query.filter_by(google_id=user_info['id']).first()
        
        if not user:
            user = User(
                google_id=user_info['id'],
                email=user_info['email']
            )
            db.session.add(user)
        
        # Update tokens
        user.set_access_token(credentials.token)
        user.set_refresh_token(credentials.refresh_token)
        user.token_expiry = credentials.expiry
        
        db.session.commit()
        
        # Store user ID in session
        session['user_id'] = user.id
        
        return user
    
    @staticmethod
    def get_credentials(user):
        """
        Get valid credentials for a user, refreshing if necessary
        
        Args:
            user: User object
            
        Returns:
            Credentials object
        """
        credentials = Credentials(
            token=user.get_access_token(),
            refresh_token=user.get_refresh_token(),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            scopes=Config.SCOPES
        )
        
        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # Update stored tokens
            user.set_access_token(credentials.token)
            user.token_expiry = credentials.expiry
            db.session.commit()
        
        return credentials
    
    @staticmethod
    def get_current_user():
        """Get current logged-in user from session"""
        user_id = session.get('user_id')
        if user_id:
            return User.query.get(user_id)
        return None
    
    @staticmethod
    def logout():
        """Clear user session"""
        session.pop('user_id', None)
        session.pop('state', None)