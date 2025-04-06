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
        self.client_secret_file = os.getenv('GOOGLE_CLIENT_SECRET_FILE', 'credentials/client_secret.json')
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/callback/google')
        self.credentials_dir = 'credentials'
        
        # Create credentials directory if it doesn't exist
        if not os.path.exists(self.credentials_dir):
            os.makedirs(self.credentials_dir)
        
        # Verify client secret file exists
        self.client_secret_exists = os.path.exists(self.client_secret_file)
        if not self.client_secret_exists:
            print(f"Warning: Google client secret file not found at {self.client_secret_file}")
            print("Google Calendar integration will not work until this file is provided.")
    
    def get_authorization_url(self, user_id='default_user'):
        """Get Google authorization URL"""
        if not self.client_secret_exists:
            raise FileNotFoundError(f"Google client secret file not found at {self.client_secret_file}")
        
        flow = Flow.from_client_secrets_file(
            self.client_secret_file,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        # Use the provided user_id as state to track the authorization request
        state = user_id
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return authorization_url
    
    def exchange_code_for_token(self, code, user_id):
        """Exchange authorization code for tokens"""
        if not self.client_secret_exists:
            raise FileNotFoundError(f"Google client secret file not found at {self.client_secret_file}")
        
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
    
    def clear_credentials(self, user_id):
        """Clear stored credentials for a user"""
        credentials_path = os.path.join(self.credentials_dir, f"{user_id}.pickle")
        
        if os.path.exists(credentials_path):
            try:
                os.remove(credentials_path)
                return True
            except Exception as e:
                print(f"Error removing credentials file: {e}")
                return False
        return True  # No credentials to remove, so success
    
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
        
        # Calculate time bounds for today using local time instead of UTC
        now = datetime.now()  # Use local time
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)
        
        # Convert to UTC for the API but maintain the same calendar day
        start_of_day_str = start_of_day.isoformat() + 'Z'
        end_of_day_str = end_of_day.isoformat() + 'Z'
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day_str,
            timeMax=end_of_day_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])

    def get_events_for_range(self, user_id, start_date, end_date):
        """Get events for a specified date range
        
        Args:
            user_id: User ID
            start_date: Start date as datetime object
            end_date: End date as datetime object
        
        Returns:
            List of events in the date range
        """
        service = self.get_service(user_id)
        
        if not service:
            return []
        
        # Ensure we have datetime objects with zero time if dates were provided
        if not isinstance(start_date, datetime) or start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0:
            start_date = datetime.combine(start_date.date(), datetime.min.time())
        
        if not isinstance(end_date, datetime) or end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = datetime.combine(end_date.date(), datetime.max.time())
        
        # Format dates for API
        start_date_str = start_date.isoformat() + 'Z'
        end_date_str = end_date.isoformat() + 'Z'
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_date_str,
            timeMax=end_date_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])

    def get_upcoming_events(self, user_id, days=7):
        """Get upcoming events for the next specified number of days
        
        Args:
            user_id: User ID
            days: Number of days to look ahead (default: 7)
        
        Returns:
            List of events in the date range
        """
        # Calculate time bounds using local time
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0)
        end_date = start_of_today + timedelta(days=days, hours=23, minutes=59, seconds=59)
        
        return self.get_events_for_range(user_id, now, end_date)
