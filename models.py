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
    """Track which emails we've already processed to avoid duplicates"""
    __tablename__ = 'processed_emails'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Gmail message ID
    email_id = db.Column(db.String(255), nullable=False)
    
    # Event extracted (if any)
    event_created = db.Column(db.Boolean, default=False)
    calendar_event_id = db.Column(db.String(255))  # Google Calendar event ID
    
    # Tracking
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'email_id', name='_user_email_uc'),)