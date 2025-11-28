import os
from dotenv import load_dotenv

load_dotenv()



class Config:
    # Flask
    # Prefer SECRET_KEY, fall back to FLASK_SECRET_KEY, and in dev use a default.
    SECRET_KEY = (
        os.getenv('SECRET_KEY')
        or os.getenv('FLASK_SECRET_KEY')
        or 'dev-secret-key-change-me'  # change this to something random for local dev
    )

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///sift.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/oauth/callback')
    
    # OAuth Scopes
    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/calendar'
    ]
    
    # Azure OpenAI (for later)
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
    AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT')


    