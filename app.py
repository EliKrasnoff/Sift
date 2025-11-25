from flask import Flask, redirect, url_for, request, session, jsonify, render_template_string, Response
from config import Config
from models import db, User, ProcessedEmail, CalendarEvent
from auth import GoogleOAuth
from datetime import datetime
import json


app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()


# Simple progress tracker
class ProgressTracker:
    def __init__(self):
        self.listeners = []
        self.current_status = {
            'stage': 'idle',
            'progress': 0,
            'message': 'Ready',
            'total': 0,
            'current': 0
        }
    
    def update(self, stage, current, total, message):
        self.current_status = {
            'stage': stage,
            'progress': int((current / total * 100)) if total > 0 else 0,
            'message': message,
            'total': total,
            'current': current
        }
    
    def get_status(self):
        return self.current_status

progress_tracker = ProgressTracker()


@app.route('/')
def index():
    """Home page"""
    user = GoogleOAuth.get_current_user()
    
    if user:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sift - Email Calendar Sync</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                    color: #333;
                }
                
                .container {
                    max-width: 900px;
                    margin: 0 auto;
                }
                
                .card {
                    background: white;
                    border-radius: 16px;
                    padding: 32px;
                    margin-bottom: 24px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                }
                
                h1 {
                    font-size: 32px;
                    font-weight: 700;
                    color: #1a202c;
                    margin-bottom: 8px;
                }
                
                .subtitle {
                    font-size: 16px;
                    color: #718096;
                    margin-bottom: 24px;
                }
                
                .user-info {
                    background: #f7fafc;
                    border-left: 4px solid #667eea;
                    padding: 16px;
                    border-radius: 8px;
                    margin-bottom: 24px;
                }
                
                .user-info strong {
                    color: #2d3748;
                    display: block;
                    margin-bottom: 4px;
                }
                
                .user-info span {
                    color: #4a5568;
                    font-size: 14px;
                }
                
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 16px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .how-it-works {
                    background: #edf2f7;
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 32px;
                }
                
                .how-it-works h2 {
                    font-size: 20px;
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 16px;
                }
                
                .how-it-works ol {
                    list-style: none;
                    counter-reset: step-counter;
                }
                
                .how-it-works li {
                    counter-increment: step-counter;
                    position: relative;
                    padding-left: 40px;
                    margin-bottom: 12px;
                    line-height: 1.6;
                    color: #4a5568;
                }
                
                .how-it-works li::before {
                    content: counter(step-counter);
                    position: absolute;
                    left: 0;
                    top: 0;
                    background: #667eea;
                    color: white;
                    width: 28px;
                    height: 28px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .button {
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 8px 8px 8px 0;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    transition: all 0.2s;
                    font-family: 'Inter', sans-serif;
                }
                
                .button:hover {
                    background: #5568d3;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }
                
                .button:active {
                    transform: translateY(0);
                }
                
                .button-secondary {
                    background: #48bb78;
                }
                
                .button-secondary:hover {
                    background: #38a169;
                    box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
                }
                
                .button-warning {
                    background: #ed8936;
                }
                
                .button-warning:hover {
                    background: #dd6b20;
                    box-shadow: 0 4px 12px rgba(237, 137, 54, 0.4);
                }
                
                .button-danger {
                    background: #f56565;
                }
                
                .button-danger:hover {
                    background: #e53e3e;
                    box-shadow: 0 4px 12px rgba(245, 101, 101, 0.4);
                }
                
                .button-outline {
                    background: white;
                    color: #667eea;
                    border: 2px solid #667eea;
                }
                
                .button-outline:hover {
                    background: #667eea;
                    color: white;
                }
                
                .progress-container {
                    display: none;
                    margin: 24px 0;
                }
                
                .progress-bar-wrapper {
                    width: 100%;
                    height: 48px;
                    background: #edf2f7;
                    border-radius: 24px;
                    overflow: hidden;
                    position: relative;
                    box-shadow: inset 0 2px 4px rgba(0,0,0,0.06);
                }
                
                .progress-bar-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                    transition: width 0.4s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 600;
                    font-size: 14px;
                    border-radius: 24px;
                }
                
                .progress-message {
                    margin-top: 12px;
                    font-size: 14px;
                    color: #4a5568;
                    text-align: center;
                    font-weight: 500;
                }
                
                .status-box {
                    margin-top: 24px;
                    padding: 20px;
                    border-radius: 12px;
                    display: none;
                    animation: slideIn 0.3s ease;
                }
                
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .status-box.success {
                    background: #c6f6d5;
                    border: 1px solid #9ae6b4;
                    color: #22543d;
                    display: block;
                }
                
                .status-box.error {
                    background: #fed7d7;
                    border: 1px solid #fc8181;
                    color: #742a2a;
                    display: block;
                }
                
                .status-box.loading {
                    background: #fefcbf;
                    border: 1px solid #f6e05e;
                    color: #744210;
                    display: block;
                }
                
                .calendar-info-box {
                    background: #f7fafc;
                    border-radius: 12px;
                    padding: 20px;
                    margin-top: 16px;
                }
                
                .event-list {
                    list-style: none;
                    margin-top: 16px;
                }
                
                .event-item {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin-bottom: 8px;
                    border-left: 3px solid #667eea;
                    font-size: 14px;
                    color: #4a5568;
                }
                
                .event-item strong {
                    color: #2d3748;
                }
                
                .actions-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 12px;
                    margin: 24px 0;
                }
                
                .helper-text {
                    font-size: 13px;
                    color: #718096;
                    margin-top: 8px;
                    line-height: 1.5;
                }
                
                .dev-section {
                    border-top: 2px dashed #e2e8f0;
                    padding-top: 24px;
                    margin-top: 24px;
                }
                
                .dev-badge {
                    display: inline-block;
                    background: #fed7d7;
                    color: #c53030;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 8px;
                }
                
                a {
                    color: #667eea;
                    text-decoration: none;
                    font-weight: 500;
                }
                
                a:hover {
                    text-decoration: underline;
                }
                
                .date-input {
                    padding: 10px 14px;
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    margin-right: 8px;
                    font-size: 14px;
                    font-family: 'Inter', sans-serif;
                    transition: border-color 0.2s;
                }
                
                .date-input:focus {
                    outline: none;
                    border-color: #667eea;
                }
                
                .clear-section {
                    background: #fffaf0;
                    border: 2px solid #fbd38d;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                }
                
                .logout-section {
                    text-align: center;
                    margin-top: 32px;
                    padding-top: 24px;
                    border-top: 1px solid #e2e8f0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>📧 Sift</h1>
                    <p class="subtitle">Automatically sync email events to your calendar</p>
                    
                    <div class="user-info">
                        <strong>✓ Connected</strong>
                        <span>{{ email }}</span>
                    </div>
                    
                    <div class="how-it-works">
                        <h2>💡 How It Works</h2>
                        <ol>
                            <li>Click "Sync Emails" to scan your inbox for event information</li>
                            <li>AI extracts event details (date, time, location) from your emails</li>
                            <li>Events are added to your "Sift - Inbox Events" calendar in Google Calendar</li>
                            <li>View and manage events directly in your Google Calendar app</li>
                        </ol>
                    </div>
                    
                    <div class="section-title">
                        🔄 Sync Actions
                    </div>
                    
                    <div class="actions-grid">
                        <button onclick="runSync()" class="button button-secondary">
                            🔄 Sync Emails Now
                        </button>
                        <button onclick="viewCalendar()" class="button">
                            📅 View Calendar Info
                        </button>
                    </div>
                    
                    <div id="progressContainer" class="progress-container">
                        <div class="progress-bar-wrapper">
                            <div id="progressFill" class="progress-bar-fill" style="width: 0%">
                                0%
                            </div>
                        </div>
                        <div id="progressMessage" class="progress-message">Starting...</div>
                    </div>
                    
                    <div id="status" class="status-box"></div>
                </div>
                
                <div class="card">
                    <div class="section-title">
                        ⚙️ Advanced Options
                    </div>
                    
                    <div class="clear-section">
                        <strong style="display: block; margin-bottom: 12px; color: #744210;">
                            🗑️ Clear Events by Date Range
                        </strong>
                        <p class="helper-text" style="margin-bottom: 16px;">
                            Remove events from your Sift calendar within a specific date range
                        </p>
                        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">
                            <input type="date" id="clearStartDate" class="date-input">
                            <input type="date" id="clearEndDate" class="date-input">
                            <button onclick="clearEvents()" class="button button-warning">
                                Clear Events
                            </button>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <button onclick="resetProcessed()" class="button button-danger">
                            🔄 Reset All Data
                        </button>
                        <p class="helper-text">
                            Clears all calendar events and processed email records. Use this to start fresh.
                        </p>
                    </div>
                    
                    <div class="dev-section">
                        <div class="section-title">
                            🔧 Developer Tools
                            <span class="dev-badge">DEV ONLY</span>
                        </div>
                        <a href="/test-apis" class="button button-outline">
                            Test API Connections
                        </a>
                        <p class="helper-text">
                            Verify Gmail and Calendar API access (remove before production)
                        </p>
                    </div>
                    
                    <div class="logout-section">
                        <a href="/logout" class="button button-outline button-danger">
                            Logout
                        </a>
                    </div>
                </div>
            </div>
            
            <script>
                let eventSource = null;
                
                function showStatus(message, type) {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'status-box ' + type;
                    statusDiv.innerHTML = message;
                }
                
                function hideStatus() {
                    document.getElementById('status').style.display = 'none';
                }
                
                function runSync() {
                    const progressContainer = document.getElementById('progressContainer');
                    const progressFill = document.getElementById('progressFill');
                    const progressMessage = document.getElementById('progressMessage');
                    
                    // Show progress, hide status
                    progressContainer.style.display = 'block';
                    hideStatus();
                    
                    // Reset progress
                    progressFill.style.width = '0%';
                    progressFill.textContent = '0%';
                    progressMessage.textContent = 'Starting sync...';
                    
                    // Connect to progress stream
                    if (eventSource) {
                        eventSource.close();
                    }
                    
                    eventSource.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        
                        // Update progress bar
                        progressFill.style.width = data.progress + '%';
                        progressFill.textContent = data.progress + '%';
                        
                        // Special styling for rate limit stage
                        if (data.stage === 'rate_limit') {
                            progressFill.style.background = 'linear-gradient(90deg, #ed8936 0%, #dd6b20 100%)';
                            progressMessage.textContent = data.message;
                            progressMessage.style.color = '#c05621';
                            progressMessage.style.fontWeight = '600';
                        } else {
                            progressFill.style.background = 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)';
                            progressMessage.textContent = data.message;
                            progressMessage.style.color = '#4a5568';
                            progressMessage.style.fontWeight = '500';
                        }
                        
                        // If complete or error, close and show results
                        if (data.stage === 'complete') {
                            eventSource.close();
                            setTimeout(() => {
                                progressContainer.style.display = 'none';
                                fetchSyncResults();
                            }, 800);
                        } else if (data.stage === 'error') {
                            eventSource.close();
                            progressContainer.style.display = 'none';
                            showStatus('❌ Error during sync: ' + data.message, 'error');
                        }
                    };
                    
                    eventSource.onerror = function() {
                        eventSource.close();
                        progressContainer.style.display = 'none';
                        showStatus('❌ Connection error. Please try again.', 'error');
                    };
                    
                    // Start the sync
                    fetch('/sync').catch(error => {
                        if (eventSource) eventSource.close();
                        progressContainer.style.display = 'none';
                        showStatus('❌ Error starting sync: ' + error.message, 'error');
                    });
                }
                
                function fetchSyncResults() {
                    showStatus('⏳ Finalizing results...', 'loading');
                    
                    // The sync already completed, just get the last result
                    fetch('/sync-result')
                        .then(response => response.json())
                        .then(data => {
                            let message = `
                                <strong style="font-size: 18px;">✅ Sync Complete!</strong><br><br>
                                <div style="line-height: 2;">
                                📧 <strong>Emails scanned:</strong> ${data.emails_scanned}<br>
                                📝 <strong>Emails processed:</strong> ${data.emails_processed}<br>
                                🎉 <strong>Events extracted:</strong> ${data.events_extracted}<br>
                                📅 <strong>Events added:</strong> ${data.events_added}
                            `;
                            
                            if (data.duplicates_skipped > 0) {
                                message += `<br>⏭️ <strong>Duplicates skipped:</strong> ${data.duplicates_skipped}`;
                            }
                            
                            if (data.errors && data.errors.length > 0) {
                                message += `<br><br>⚠️ ${data.errors.length} error(s) occurred`;
                            }
                            
                            if (data.costs) {
                                message += `<br><br>💰 <strong>Cost:</strong> $${data.costs.total_cost.toFixed(4)}`;
                            }
                            
                            message += '</div>';
                            
                            showStatus(message, 'success');
                        })
                        .catch(error => {
                            showStatus('❌ Error fetching results', 'error');
                        });
                }
                
                function viewCalendar() {
                    showStatus('⏳ Loading calendar info...', 'loading');
                    
                    fetch('/calendar-info')
                        .then(response => response.json())
                        .then(data => {
                            let eventsHtml = '';
                            if (data.events && data.events.length > 0) {
                                eventsHtml = '<ul class="event-list">';
                                data.events.slice(0, 10).forEach(event => {
                                    const startTime = event.start ? new Date(event.start).toLocaleString() : 'No date';
                                    eventsHtml += `
                                        <li class="event-item">
                                            <strong>${event.summary}</strong><br>
                                            📅 ${startTime}
                                            ${event.location ? '<br>📍 ' + event.location : ''}
                                        </li>
                                    `;
                                });
                                eventsHtml += '</ul>';
                                
                                if (data.events.length > 10) {
                                    eventsHtml += `<p class="helper-text">Showing 10 of ${data.event_count} total events</p>`;
                                }
                            } else {
                                eventsHtml = '<p class="helper-text">No upcoming events. Try running a sync!</p>';
                            }
                            
                            let message = `
                                <strong style="font-size: 18px;">📅 Calendar Information</strong>
                                <div class="calendar-info-box">
                                    <p><strong>Calendar Name:</strong> Sift - Inbox Events</p>
                                    <p><strong>Total Events:</strong> ${data.event_count}</p>
                                    ${eventsHtml}
                                    <div style="margin-top: 16px;">
                                        <a href="https://calendar.google.com" target="_blank" class="button button-outline">
                                            Open Google Calendar →
                                        </a>
                                    </div>
                                </div>
                            `;
                            
                            showStatus(message, 'success');
                        })
                        .catch(error => {
                            showStatus('❌ Error loading calendar: ' + error.message, 'error');
                        });
                }
                
                function resetProcessed() {
                    if (!confirm('⚠️ This will delete ALL events from your Sift calendar and reset all processed email records. Are you sure?')) {
                        return;
                    }
                    
                    showStatus('⏳ Resetting all data...', 'loading');
                    
                    fetch('/reset-processed')
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                showStatus('✅ ' + data.message + '<br><br>You can now run a new sync.', 'success');
                            } else {
                                showStatus('❌ ' + data.message, 'error');
                            }
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
                    
                    if (!confirm(`Delete all events from ${startDate} to ${endDate}?`)) {
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
        # Landing page for non-authenticated users
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sift - Email Calendar Sync</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                
                .landing-container {
                    max-width: 600px;
                    background: white;
                    border-radius: 24px;
                    padding: 48px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }
                
                .logo {
                    font-size: 64px;
                    margin-bottom: 16px;
                }
                
                h1 {
                    font-size: 48px;
                    font-weight: 700;
                    color: #1a202c;
                    margin-bottom: 16px;
                }
                
                .tagline {
                    font-size: 20px;
                    color: #718096;
                    margin-bottom: 40px;
                    line-height: 1.6;
                }
                
                .login-button {
                    background: #667eea;
                    color: white;
                    padding: 16px 40px;
                    border-radius: 12px;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 18px;
                    font-weight: 600;
                    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
                    transition: all 0.3s;
                }
                
                .login-button:hover {
                    background: #5568d3;
                    transform: translateY(-2px);
                    box-shadow: 0 15px 35px rgba(102, 126, 234, 0.5);
                }
                
                .features {
                    text-align: left;
                    margin-top: 48px;
                    display: grid;
                    gap: 20px;
                }
                
                .feature {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 16px;
                    background: #f7fafc;
                    border-radius: 12px;
                }
                
                .feature-icon {
                    font-size: 24px;
                    flex-shrink: 0;
                }
                
                .feature-text {
                    color: #4a5568;
                    line-height: 1.6;
                }
            </style>
        </head>
        <body>
            <div class="landing-container">
                <div class="logo">📧</div>
                <h1>Sift</h1>
                <p class="tagline">Never miss an event buried in your inbox</p>
                
                <a href="/login" class="login-button">
                    Connect with Google
                </a>
                
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">✨</div>
                        <div class="feature-text">AI automatically extracts events from your emails</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📅</div>
                        <div class="feature-text">Creates a separate "Sift" calendar in Google Calendar</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🔄</div>
                        <div class="feature-text">Syncs on-demand or runs in the background</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🎯</div>
                        <div class="feature-text">View source emails directly from calendar events</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)


# Store last sync result
last_sync_result = {}

@app.route('/sync-progress')
def sync_progress():
    """Server-Sent Events endpoint for real-time progress"""
    def generate():
        import time
        last_stage = None
        
        while True:
            status = progress_tracker.get_status()
            
            # Only send if status changed
            if status['stage'] != last_stage or status['stage'] in ['processing', 'extracting', 'adding']:
                yield f"data: {json.dumps(status)}\n\n"
                last_stage = status['stage']
            
            # Stop streaming when done
            if status['stage'] in ['complete', 'error']:
                break
            
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/sync')
def run_sync():
    """Trigger sync with progress tracking"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from sync_worker import SyncWorker
    
    def progress_callback(stage, current, total, message):
        progress_tracker.update(stage, current, total, message)
    
    worker = SyncWorker(user)
    results = worker.run_sync(progress_callback=progress_callback)
    
    # Store result for later retrieval
    global last_sync_result
    last_sync_result = results
    
    return jsonify(results)


@app.route('/sync-result')
def sync_result():
    """Get the last sync result"""
    return jsonify(last_sync_result)

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
    """Clear all processed emails and all calendar events so we can re-sync"""
    user = GoogleOAuth.get_current_user()
    
    if not user:
        return redirect(url_for('login'))
    
    try:
        from models import ProcessedEmail, CalendarEvent
        from calendar_service import CalendarService
        
        deleted_count = 0
        
        # Delete ALL events from Google Calendar (if calendar exists)
        if user.sift_calendar_id:
            cal_service = CalendarService(user)
            
            try:
                # Get ALL events from the calendar (no date range)
                events_result = cal_service.service.events().list(
                    calendarId=user.sift_calendar_id,
                    maxResults=2500,  # Google's max per request
                    singleEvents=True
                ).execute()
                
                events = events_result.get('items', [])
                
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
                
                print(f"Deleted {deleted_count} events from Google Calendar")
                
            except Exception as e:
                print(f"Error accessing calendar: {e}")
        
        # Delete all calendar event records from database
        CalendarEvent.query.filter_by(user_id=user.id).delete()
        
        # Delete all processed emails from database
        ProcessedEmail.query.filter_by(user_id=user.id).delete()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Cleared {deleted_count} calendar events and all processed email records. Run sync to reprocess.'
        })
        
    except Exception as e:
        print(f"Error during reset: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error during reset: {str(e)}'
        }), 500

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