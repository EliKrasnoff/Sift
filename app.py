from flask import Flask, redirect, url_for, request, session, jsonify, render_template_string
from config import Config
from models import db, User
from auth import GoogleOAuth

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """Home page"""
    user = GoogleOAuth.get_current_user()
    
    if user:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sift - Authenticated</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }
                .success {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .button {
                    background: #007bff;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 6px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px 10px 10px 0;
                }
                .logout {
                    background: #dc3545;
                }
                h1 {
                    color: #333;
                }
            </style>
        </head>
        <body>
            <h1>✅ Successfully Connected to Sift!</h1>
            <div class="success">
                <p><strong>Email:</strong> {{ email }}</p>
                <p><strong>Status:</strong> Authenticated and ready to sync</p>
            </div>
            <p>Your Sift calendar will be created automatically and events from your inbox will start syncing.</p>
            <a href="/test-apis" class="button">Test API Access</a>
            <a href="/logout" class="button logout">Logout</a>
        </body>
        </html>
        """
        return render_template_string(html, email=user.email)
    else:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sift - Event Calendar from Your Inbox</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                }
                h1 {
                    color: #333;
                    font-size: 48px;
                    margin-bottom: 10px;
                }
                .tagline {
                    color: #666;
                    font-size: 20px;
                    margin-bottom: 40px;
                }
                .login-button {
                    background: #4285f4;
                    color: white;
                    padding: 16px 32px;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 18px;
                    font-weight: 500;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .login-button:hover {
                    background: #357ae8;
                }
                .features {
                    text-align: left;
                    margin: 40px auto;
                    max-width: 500px;
                }
                .feature {
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <h1>📧 Sift</h1>
            <p class="tagline">Never miss an event buried in your inbox</p>
            
            <a href="/login" class="login-button">
                Connect with Google
            </a>
            
            <div class="features">
                <div class="feature">
                    ✨ AI extracts events from emails automatically
                </div>
                <div class="feature">
                    📅 Creates a separate "Sift" calendar in Google Calendar
                </div>
                <div class="feature">
                    🔄 Syncs in real-time (or every few hours)
                </div>
                <div class="feature">
                    🎯 Add events to your personal calendar in one click
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)


@app.route('/login')
def login():
    """Initiate OAuth flow"""
    authorization_url = GoogleOAuth.get_authorization_url()
    print(f"Session state set: {session.get('state')}")
    print(f"Full session: {dict(session)}")  # ADD THIS
    print(f"Authorization URL: {authorization_url}")  # ADD THIS
    return redirect(authorization_url)


@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback from Google"""
    print("=== CALLBACK ROUTE HIT ===")
    print(f"Request URL: {request.url}")
    print(f"Request args: {request.args}")
    print(f"Session contents: {dict(session)}")  # ADD THIS
    print(f"Session state: {session.get('state')}")  # ADD THIS
    print(f"Cookies: {request.cookies}")  # ADD THIS
    
    try:
        authorization_response = request.url
        user = GoogleOAuth.handle_callback(authorization_response)
        
        print(f"User created/found: {user}")
        print(f"User email: {user.email if user else 'None'}")
        
        if user:
            return redirect(url_for('index'))
        else:
            return "Authentication failed", 400
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"Error during authentication: {str(e)}", 400


@app.route('/logout')
def logout():
    """Logout user"""
    GoogleOAuth.logout()
    return redirect(url_for('index'))


@app.route('/test-apis')
def test_apis():
    """Test endpoint to verify API access"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    try:
        from googleapiclient.discovery import build
        
        # Get credentials
        credentials = GoogleOAuth.get_credentials(user)
        
        # Test Gmail API
        gmail_service = build('gmail', 'v1', credentials=credentials)
        profile = gmail_service.users().getProfile(userId='me').execute()
        
        # Test Calendar API
        calendar_service = build('calendar', 'v3', credentials=credentials)
        calendars = calendar_service.calendarList().list().execute()
        
        response = {
            'status': 'success',
            'gmail': {
                'email': profile['emailAddress'],
                'total_messages': profile['messagesTotal']
            },
            'calendar': {
                'calendars_count': len(calendars.get('items', [])),
                'calendars': [cal['summary'] for cal in calendars.get('items', [])]
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)