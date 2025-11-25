from googleapiclient.discovery import build
from auth import GoogleOAuth
from models import db


class CalendarService:
    """Handle Google Calendar operations"""
    
    def __init__(self, user):
        """
        Initialize calendar service for a user
        
        Args:
            user: User object from database
        """
        self.user = user
        self.credentials = GoogleOAuth.get_credentials(user)
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    def create_sift_calendar(self):
        """
        Create the 'Sift - Inbox Events' calendar
        
        Returns:
            calendar_id (str): The ID of the created or existing calendar
        """
        # Check if calendar already exists
        if self.user.sift_calendar_id:
            try:
                # Verify it still exists
                self.service.calendars().get(calendarId=self.user.sift_calendar_id).execute()
                print(f"Sift calendar already exists: {self.user.sift_calendar_id}")
                return self.user.sift_calendar_id
            except Exception as e:
                print(f"Sift calendar not found, creating new one: {e}")
        
        # Create new calendar
        calendar = {
            'summary': 'Sift - Inbox Events',
            'description': 'Events automatically extracted from your email inbox by Sift',
            'timeZone': 'America/Los_Angeles'  # You can make this dynamic later
        }
        
        created_calendar = self.service.calendars().insert(body=calendar).execute()
        calendar_id = created_calendar['id']
        
        print(f"Created Sift calendar: {calendar_id}")
        
        # Save to database
        self.user.sift_calendar_id = calendar_id
        db.session.commit()
        
        return calendar_id
    
    def add_event(self, event_data):
        """
        Add an event to the Sift calendar
        
        Args:
            event_data (dict): Event details with keys:
                - summary (str): Event title
                - start (dict): Start time {'dateTime': 'ISO string', 'timeZone': 'America/Los_Angeles'}
                - end (dict): End time {'dateTime': 'ISO string', 'timeZone': 'America/Los_Angeles'}
                - description (str, optional): Event description
                - location (str, optional): Event location
                
        Returns:
            event_id (str): Google Calendar event ID
        """
        calendar_id = self.user.sift_calendar_id
        if not calendar_id:
            calendar_id = self.create_sift_calendar()
        
        event = self.service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
        
        print(f"Created event: {event.get('summary')} - {event.get('id')}")
        return event.get('id')
    
    def update_event(self, event_id, event_data):
        """
        Update an existing event
        
        Args:
            event_id (str): Google Calendar event ID
            event_data (dict): Updated event details
        """
        calendar_id = self.user.sift_calendar_id
        
        updated_event = self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()
        
        return updated_event.get('id')
    
    def delete_event(self, event_id):
        """Delete an event from the Sift calendar"""
        calendar_id = self.user.sift_calendar_id
        
        self.service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        print(f"Deleted event: {event_id}")
    
    def list_events(self, max_results=10):
        """
        List events in the Sift calendar
        
        Args:
            max_results (int): Maximum number of events to return
            
        Returns:
            list: List of event objects
        """
        calendar_id = self.user.sift_calendar_id
        if not calendar_id:
            return []
        
        from datetime import datetime
        
        try:
            # Get upcoming events (from now onwards)
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except Exception as e:
            print(f"Error listing events: {e}")
            return []