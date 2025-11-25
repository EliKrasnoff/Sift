from googleapiclient.discovery import build
from auth import GoogleOAuth
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText


class GmailService:
    """Handle Gmail API operations"""
    
    def __init__(self, user):
        """
        Initialize Gmail service for a user
        
        Args:
            user: User object from database
        """
        self.user = user
        self.credentials = GoogleOAuth.get_credentials(user)
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def get_recent_emails(self, days=1, max_results=25, exclude_categories=True):
        """
        Get emails from the last N days (excluding archived/deleted)
        
        Args:
            days (int): Number of days to look back
            max_results (int): Maximum number of emails to retrieve
            exclude_categories (bool): If True, exclude Promotions, Social, Updates, Forums
        
        Returns:
            list: List of email objects
        """
        after_date = datetime.now() - timedelta(days=days)
        after_date_str = after_date.strftime('%Y/%m/%d')
        
        # Build query to exclude Gmail categories
        query = f'after:{after_date_str} -in:trash -is:archived'
        
        if exclude_categories:
            # Exclude Gmail's automatic categories
            query += ' -category:promotions -category:social'
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            print(f"Found {len(messages)} emails in last {days} days")
            
            emails = []
            for msg in messages:
                email_data = self.get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []  # Always return empty list on error, not None
    def get_email_details(self, message_id):
        """
        Get full details of a specific email
        
        Args:
            message_id (str): Gmail message ID
            
        Returns:
            dict: Email details including id, subject, body, date, sender, snippet
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Get email body
            body = self._get_email_body(message['payload'])
            
            # Get snippet (preview text)
            snippet = message.get('snippet', '')
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': date_str,
                'body': body,
                'snippet': snippet
            }
            
        except Exception as e:
            print(f"Error getting email {message_id}: {e}")
            return None
    
    def _get_email_body(self, payload):
        """
        Extract email body from message payload
        
        Args:
            payload: Gmail message payload
            
        Returns:
            str: Email body text
        """
        body = ""
        
        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        # Check for multipart emails
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        # Fallback to HTML if no plain text
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    # Recursively check nested parts
                    body = self._get_email_body(part)
                    if body:
                        break
        
        return body
    
    def search_emails(self, query, max_results=50):
        """
        Search emails with a custom query
        
        Args:
            query (str): Gmail search query
            max_results (int): Maximum number of results
            
        Returns:
            list: List of email objects
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                email_data = self.get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"Error searching emails: {e}")
            return []