import os
import pickle
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class GoogleCalendarAPI:
    def __init__(self):
        self.client_secret_file = os.getenv('GOOGLE_CLIENT_SECRET_FILE', 'client_secret.json')
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/callback/google')
        self.credentials_dir = 'credentials'
        
        # Create credentials directory if it doesn't exist
        if not os.path.exists(self.credentials_dir):
            os.makedirs(self.credentials_dir)
    
    def get_authorization_url(self):
        """Get Google authorization URL"""
        flow = Flow.from_client_secrets_file(
            self.client_secret_file,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        # Generate a state value (user ID) to track the authorization request
        state = "default_user"  # In production, use a real user ID
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return authorization_url
    
    def exchange_code_for_token(self, code, user_id):
        """Exchange authorization code for tokens"""
        flow = Flow.from_client_secrets_file(
            self.client_secret_file,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save the credentials for this user
        self._save_credentials(credentials, user_id)
    
    def _save_credentials(self, credentials, user_id):
        """Save credentials to a file"""
        credentials_path = os.path.join(self.credentials_dir, f"{user_id}.pickle")
        with open(credentials_path, 'wb') as token:
            pickle.dump(credentials, token)
    
    def _get_credentials(self, user_id):
        """Get stored credentials for user"""
        credentials_path = os.path.join(self.credentials_dir, f"{user_id}.pickle")
        
        credentials = None
        if os.path.exists(credentials_path):
            with open(credentials_path, 'rb') as token:
                credentials = pickle.load(token)
        
        # Check if credentials are expired
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self._save_credentials(credentials, user_id)
        
        return credentials
    
    def has_credentials(self, user_id):
        """Check if we have valid credentials for this user"""
        credentials = self._get_credentials(user_id)
        return credentials is not None
    
    def get_service(self, user_id):
        """Get a Google Calendar service instance"""
        credentials = self._get_credentials(user_id)
        
        if not credentials or not credentials.valid:
            return None
        
        return build('calendar', 'v3', credentials=credentials)
    
    def get_todays_events(self, user_id):
        """Get today's events for a user"""
        service = self.get_service(user_id)
        
        if not service:
            return []
        
        # Calculate time bounds for today
        now = datetime.utcnow()
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + 'Z'
        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
