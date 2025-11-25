from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from cryptography.fernet import Fernet
import os
import base64

db = SQLAlchemy()

# Simple encryption key (in production, use a proper key management system)
# For now, we'll generate one if it doesn't exist
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())

def encrypt_token(token):
    """Encrypt sensitive tokens before storing"""
    if not token:
        return None
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    """Decrypt tokens when needed"""
    if not encrypted_token:
        return None
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_token.encode()).decode()


class User(db.Model):
    """Store user OAuth credentials and calendar info"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    
    # Encrypted OAuth tokens
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_expiry = db.Column(db.DateTime)
    
    # Sift calendar ID in user's Google Calendar
    sift_calendar_id = db.Column(db.String(255))
    
    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sync = db.Column(db.DateTime)
    
    # Relationships
    processed_emails = db.relationship('ProcessedEmail', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_access_token(self, token):
        """Encrypt and store access token"""
        self.access_token = encrypt_token(token)
    
    def get_access_token(self):
        """Decrypt and return access token"""
        return decrypt_token(self.access_token)
    
    def set_refresh_token(self, token):
        """Encrypt and store refresh token"""
        self.refresh_token = encrypt_token(token)
    
    def get_refresh_token(self):
        """Decrypt and return refresh token"""
        return decrypt_token(self.refresh_token)


class ProcessedEmail(db.Model):
    """Track emails that have been processed"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)    
    email_id = db.Column(db.String(100), nullable=False)
    email_subject = db.Column(db.String(500))
    email_date = db.Column(db.DateTime)
    
    # Processing info
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    event_created = db.Column(db.Boolean, default=False)
    events_count = db.Column(db.Integer, default=0)
    processing_status = db.Column(db.String(50), default='success')  # success, error, partial
    error_message = db.Column(db.Text)
    
    # Relationship to events
    calendar_events = db.relationship('CalendarEvent', backref='source_email', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'email_id', name='unique_user_email'),
    )

class SyncCost(db.Model):
    """Track API costs for each sync"""
    __tablename__ = 'sync_costs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Sync info
    sync_date = db.Column(db.DateTime, default=datetime.utcnow)
    emails_processed = db.Column(db.Integer, default=0)
    events_extracted = db.Column(db.Integer, default=0)
    
    # Token usage
    openai_input_tokens = db.Column(db.Integer, default=0)
    openai_output_tokens = db.Column(db.Integer, default=0)
    
    # Costs (in USD)
    openai_cost = db.Column(db.Float, default=0.0)
    gmail_api_calls = db.Column(db.Integer, default=0)
    calendar_api_calls = db.Column(db.Integer, default=0)
    total_cost = db.Column(db.Float, default=0.0)
    
    # Metadata
    model_used = db.Column(db.String(50))  # e.g., "gpt-4", "gpt-3.5-turbo"
    
    user = db.relationship('User', backref=db.backref('sync_costs', lazy=True))
    
class CalendarEvent(db.Model):
    """Track calendar events we've created"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    processed_email_id = db.Column(db.Integer, db.ForeignKey('processed_email.id'), nullable=True)
    
    # Google Calendar info
    gcal_event_id = db.Column(db.String(500), nullable=False)
    gcal_calendar_id = db.Column(db.String(500))
    
    # Event details (for quick lookup)
    event_title = db.Column(db.String(500))
    start_datetime = db.Column(db.DateTime)
    end_datetime = db.Column(db.DateTime)
    location = db.Column(db.String(500))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_canceled = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User actions
    user_deleted = db.Column(db.Boolean, default=False)  # Track if user manually deleted
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'gcal_event_id', name='unique_user_gcal_event'),
    )