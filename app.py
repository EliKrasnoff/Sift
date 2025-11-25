from flask import Flask, redirect, url_for, request, session, jsonify, render_template_string
from config import Config
from models import db, User, ProcessedEmail, CalendarEvent
from auth import GoogleOAuth
from datetime import datetime


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
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                }
                .button:hover {
                    background: #0056b3;
                }
                .sync-button {
                    background: #28a745;
                }
                .sync-button:hover {
                    background: #218838;
                }
                .calendar-button {
                    background: #6f42c1;
                }
                .calendar-button:hover {
                    background: #5a32a3;
                }
                .reset-button {
                    background: #ffc107;
                    color: #000;
                }
                .reset-button:hover {
                    background: #e0a800;
                }
                .clear-button {
                    background: #fd7e14;
                }
                .clear-button:hover {
                    background: #e8590c;
                }
                .logout {
                    background: #dc3545;
                }
                .logout:hover {
                    background: #c82333;
                }
                h1 {
                    color: #333;
                }
                .actions {
                    margin: 30px 0;
                }
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    margin-top: 30px;
                    margin-bottom: 10px;
                    color: #555;
                }
                #status {
                    margin-top: 20px;
                    padding: 15px;
                    border-radius: 6px;
                    display: none;
                }
                #status.loading {
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    color: #856404;
                    display: block;
                }
                #status.success {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    display: block;
                }
                #status.error {
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                    display: block;
                }
                .info-box {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 15px 0;
                }
                .date-input {
                    padding: 8px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    margin-right: 10px;
                    font-size: 14px;
                }
                .clear-events-section {
                    margin: 20px 0;
                    padding: 15px;
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    border-radius: 6px;
                }
            </style>
        </head>
        <body>
            <h1>✅ Successfully Connected to Sift!</h1>
            <div class="success">
                <p><strong>Email:</strong> {{ email }}</p>
                <p><strong>Status:</strong> Authenticated and ready to sync</p>
            </div>
            
            <div class="section-title">📧 Email & Calendar Actions</div>
            <div class="actions">
                <button onclick="runSync()" class="button sync-button">🔄 Sync Emails Now</button>
                <button onclick="viewCalendar()" class="button calendar-button">📅 View Calendar Info</button>
                <a href="/test-apis" class="button">🔧 Test API Access</a>
            </div>
            
            <div id="status"></div>
            
            <div class="info-box">
                <p><strong>💡 How it works:</strong></p>
                <ul>
                    <li>Click "Sync Emails Now" to scan your inbox for events</li>
                    <li>Events are extracted using AI and added to your "Sift - Inbox Events" calendar</li>
                    <li>View the calendar in your Google Calendar app</li>
                    <li>You can add events to your personal calendar from there</li>
                </ul>
            </div>
            
            <div class="section-title">⚙️ Advanced</div>
            
            <div class="clear-events-section">
                <p><strong>🗑️ Clear Events by Date Range</strong></p>
                <p style="font-size: 12px; color: #666; margin: 5px 0;">Remove all events from your Sift calendar within a specific date range.</p>
                <div style="margin-top: 10px;">
                    <input type="date" id="clearStartDate" class="date-input" placeholder="Start Date">
                    <input type="date" id="clearEndDate" class="date-input" placeholder="End Date">
                    <button onclick="clearEvents()" class="button clear-button">🗑️ Clear Events</button>
                </div>
            </div>
            
            <button onclick="resetProcessed()" class="button reset-button">🔄 Reset Processed Emails</button>
            <p style="font-size: 12px; color: #666; margin-top: 5px;">Use this to reprocess all emails from scratch (useful for testing)</p>
            
            <div class="section-title">Account</div>
            <a href="/logout" class="button logout">Logout</a>
            
            <script>
                function showStatus(message, type) {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = type;
                    statusDiv.innerHTML = message;
                }
                
                function runSync() {
                    showStatus('⏳ Syncing emails... This may take a minute.', 'loading');
                    
                    fetch('/sync')
                        .then(response => response.json())
                        .then(data => {
                            let message = `
                                <strong>✅ Sync Complete!</strong><br>
                                📧 Emails scanned: ${data.emails_scanned}<br>
                                📝 Emails processed: ${data.emails_processed}<br>
                                🎉 Events extracted: ${data.events_extracted}<br>
                                📅 Events added to calendar: ${data.events_added}
                            `;
                            
                            if (data.duplicates_skipped) {
                                message += `<br>⏭️ Duplicate events skipped: ${data.duplicates_skipped}`;
                            }
                            
                            // NEW: Show warning for large emails
                            if (data.large_emails && data.large_emails.length > 0) {
                                message += '<br><br><strong>⚠️ Large Emails Detected:</strong><ul>';
                                data.large_emails.forEach(email => {
                                    message += `<li>${email.subject}: ${email.total_events} events (added first ${email.capped_at})</li>`;
                                });
                                message += '</ul>';
                                message += '<p style="font-size: 12px;">Contact support if you need all events from these emails.</p>';
                            }
                            
                            if (data.errors && data.errors.length > 0) {
                                message += `<br><br>⚠️ ${data.errors.length} error(s) occurred`;
                            }
                            
                            showStatus(message, 'success');
                        })
                        .catch(error => {
                            showStatus('❌ Error during sync: ' + error.message, 'error');
                        });
                }
                
                function viewCalendar() {
                    showStatus('⏳ Loading calendar info...', 'loading');
                    
                    fetch('/calendar-info')
                        .then(response => response.json())
                        .then(data => {
                            let eventsHtml = '';
                            if (data.events && data.events.length > 0) {
                                eventsHtml = '<br><br><strong>Recent events:</strong><ul>';
                                data.events.forEach(event => {
                                    eventsHtml += `<li>${event.summary} - ${event.start || 'No date'}</li>`;
                                });
                                eventsHtml += '</ul>';
                            } else {
                                eventsHtml = '<br><br>No events yet. Try running a sync!';
                            }
                            
                            let message = `
                                <strong>📅 Calendar Info</strong><br>
                                Calendar ID: ${data.calendar_id}<br>
                                Total events: ${data.event_count}
                                ${eventsHtml}
                                <br><br>
                                <a href="https://calendar.google.com" target="_blank" style="color: #007bff;">Open Google Calendar →</a>
                            `;
                            
                            showStatus(message, 'success');
                        })
                        .catch(error => {
                            showStatus('❌ Error loading calendar: ' + error.message, 'error');
                        });
                }
                
                function resetProcessed() {
                    if (!confirm('Are you sure you want to reset? This will allow all emails to be reprocessed.')) {
                        return;
                    }
                    
                    showStatus('⏳ Resetting processed emails...', 'loading');
                    
                    fetch('/reset-processed')
                        .then(response => response.json())
                        .then(data => {
                            showStatus('✅ ' + data.message + '<br><br>You can now run a sync to reprocess all emails.', 'success');
                        })
                        .catch(error => {
                            showStatus('❌ Error resetting: ' + error.message, 'error');
                        });
                }
                
                function clearEvents() {
                    const startDate = document.getElementById('clearStartDate').value;
                    const endDate = document.getElementById('clearEndDate').value;
                    
                    if (!startDate || !endDate) {
                        showStatus('❌ Please select both start and end dates', 'error');
                        return;
                    }
                    
                    if (!confirm(`Are you sure you want to delete all events from ${startDate} to ${endDate}?`)) {
                        return;
                    }
                    
                    showStatus('⏳ Clearing events...', 'loading');
                    
                    fetch('/clear-events', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            start_date: startDate,
                            end_date: endDate
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showStatus('✅ ' + data.message, 'success');
                        } else {
                            showStatus('❌ ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        showStatus('❌ Error clearing events: ' + error.message, 'error');
                    });
                }
            </script>
        </body>
        </html>
        """
        return render_template_string(html, email=user.email)
    else:
        # ... non-authenticated HTML (no changes)    else:
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

@app.route('/reset-processed')
def reset_processed():
    """Clear all processed emails so we can re-sync"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    from models import ProcessedEmail
    
    # Delete all processed emails for this user
    ProcessedEmail.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'All processed emails cleared. Run sync again to reprocess.'
    })

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

@app.route('/sync')
def run_sync():
    """Manually trigger a sync"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    from sync_worker import SyncWorker
    
    worker = SyncWorker(user)
    results = worker.run_sync()
    
    return jsonify(results)


@app.route('/calendar-info')
def calendar_info():
    """Show info about the Sift calendar"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    from calendar_service import CalendarService
    
    cal_service = CalendarService(user)
    
    if not user.sift_calendar_id:
        calendar_id = cal_service.create_sift_calendar()
    else:
        calendar_id = user.sift_calendar_id
    
    events = cal_service.list_events(max_results=20)
    
    return jsonify({
        'calendar_id': calendar_id,
        'calendar_name': 'Sift - Inbox Events',
        'event_count': len(events),
        'events': [
            {
                'summary': e.get('summary'),
                'start': e.get('start', {}).get('dateTime'),
                'location': e.get('location')
            }
            for e in events
        ]
    })


@app.route('/clear-events', methods=['POST'])
def clear_events():
    """Clear events from the Sift calendar within a date range"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    try:
        from calendar_service import CalendarService
        import dateutil.parser
        
        # Get date range from request
        data = request.get_json()
        start_date = data.get('start_date')  # Format: YYYY-MM-DD
        end_date = data.get('end_date')      # Format: YYYY-MM-DD
        
        if not start_date or not end_date:
            return jsonify({'status': 'error', 'message': 'Start and end dates required'}), 400
        
        cal_service = CalendarService(user)
        
        if not user.sift_calendar_id:
            return jsonify({'status': 'error', 'message': 'No Sift calendar found'}), 404
        
        # Get all events in the date range
        events_result = cal_service.service.events().list(
            calendarId=user.sift_calendar_id,
            timeMin=f"{start_date}T00:00:00-08:00",
            timeMax=f"{end_date}T23:59:59-08:00",
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        deleted_count = 0
        
        # Delete each event
        for event in events:
            try:
                cal_service.service.events().delete(
                    calendarId=user.sift_calendar_id,
                    eventId=event['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting event {event.get('summary')}: {e}")
        
        # Also clear processed emails in that date range so they can be re-synced
        # (Optional - comment out if you don't want this)
        from models import ProcessedEmail
        ProcessedEmail.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted_count} event(s) from {start_date} to {end_date}',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        print(f"Error clearing events: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/costs')
def view_costs():
    """View cost tracking for current user"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    from models import SyncCost
    from sqlalchemy import func
    
    # Get recent syncs
    recent_syncs = SyncCost.query.filter_by(user_id=user.id)\
        .order_by(SyncCost.sync_date.desc())\
        .limit(20).all()
    
    # Calculate totals
    total_cost = db.session.query(func.sum(SyncCost.total_cost))\
        .filter_by(user_id=user.id).scalar() or 0
    
    total_tokens = db.session.query(
        func.sum(SyncCost.openai_input_tokens + SyncCost.openai_output_tokens)
    ).filter_by(user_id=user.id).scalar() or 0
    
    return jsonify({
        'total_cost': round(total_cost, 4),
        'total_tokens': total_tokens,
        'recent_syncs': [{
            'date': sync.sync_date.isoformat(),
            'emails_processed': sync.emails_processed,
            'events_extracted': sync.events_extracted,
            'input_tokens': sync.openai_input_tokens,
            'output_tokens': sync.openai_output_tokens,
            'cost': round(sync.total_cost, 4),
            'model': sync.model_used
        } for sync in recent_syncs]
    })


@app.route('/costs/summary')
def costs_summary():
    """Get cost summary stats"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    from models import SyncCost
    from sqlalchemy import func
    from datetime import timedelta
    
    # Last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    monthly_cost = db.session.query(func.sum(SyncCost.total_cost))\
        .filter(SyncCost.user_id == user.id)\
        .filter(SyncCost.sync_date >= thirty_days_ago)\
        .scalar() or 0
    
    monthly_syncs = db.session.query(func.count(SyncCost.id))\
        .filter(SyncCost.user_id == user.id)\
        .filter(SyncCost.sync_date >= thirty_days_ago)\
        .scalar() or 0
    
    avg_cost_per_sync = monthly_cost / monthly_syncs if monthly_syncs > 0 else 0
    
    return jsonify({
        'last_30_days': {
            'total_cost': round(monthly_cost, 4),
            'syncs_count': monthly_syncs,
            'avg_cost_per_sync': round(avg_cost_per_sync, 4)
        },
        'projected_monthly': round(monthly_cost, 2) if monthly_syncs > 0 else 0
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)