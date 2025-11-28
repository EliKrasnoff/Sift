import { useState } from 'react';
import './App.css';

function App() {
  // Backend base URL (set via env var `REACT_APP_API_BASE`), defaults to localhost:5000
  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000';
  const loginUrl = `${API_BASE}/login`;

  return (
    <div className="App">
      <div className="stars"></div>
      
      <nav className="navbar">
        <div className="nav-content">
          <div className="logo-nav">
            <img src="/sift_logo.png" alt="Sift logo" className="nav-logo-img" />
            <span className="logo-text">Sift</span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#waitlist">Join</a>
          </div>
        </div>
      </nav>

      <main className="main-content">
        {/* Hero Section */}
        <section className="hero">
          <div className="hero-content">
            <div className="hero-text">
              <h1 className="hero-title">
                <span className="gradient-text">Never Miss an Event Again</span>
              </h1>
              <p className="hero-subtitle">
                Feeling overwhelmed by email spam? Sift intelligently extracts events from your inbox and adds them to your calendar in one click.
              </p>
              <div className="hero-badges">
                <span className="badge">🤖 AI-Powered</span>
                <span className="badge">⚡ One Click</span>
                <span className="badge">📧 Email Magic</span>
              </div>
            </div>
            <div className="hero-visual">
              <div className="floating-card card-1">
                <div className="email-icon">📧</div>
              </div>
              <div className="floating-card card-2">
                <div className="calendar-icon">📅</div>
              </div>
              <div className="floating-card card-3">
                <div className="spark-icon">✨</div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="features">
          <h2 className="section-title">Why Sift?</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🎯</div>
              <h3>Smart Parsing</h3>
              <p>AI extracts all event details from any email or newsletter automatically.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚙️</div>
              <h3>Seamless Integration</h3>
              <p>One-click adds events directly to your calendar. No copy-paste needed.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3>Privacy First</h3>
              <p>Your emails stay private. We only extract what you need.</p>
            </div>
          </div>
        </section>

        {/* Problem Section */}
        <section className="problem-section">
          <h2 className="section-title">The Problem</h2>
          <div className="problem-container">
            <div className="problem-item">
              <span className="problem-number">01</span>
              <h3>Email Overload</h3>
              <p>Your inbox is flooded with newsletters, promotions, and event updates. Important information gets buried.</p>
            </div>
            <div className="problem-item">
              <span className="problem-number">02</span>
              <h3>Missed Events</h3>
              <p>You worry that you're missing important conferences, talks, and networking opportunities hiding in your emails.</p>
            </div>
            <div className="problem-item">
              <span className="problem-number">03</span>
              <h3>Manual Work</h3>
              <p>Adding events to your calendar is tedious. Search, copy, paste, repeat—over and over again.</p>
            </div>
          </div>
        </section>

        {/* Waitlist Section */}
        <section id="waitlist" className="waitlist-section">
          <div className="waitlist-container">
            <div className="waitlist-text">
              <h2 className="waitlist-title">Securely connect your Stanford Google account</h2>
              <p className="waitlist-description">
                We only access event details needed to add events to your calendar and never share your emails. Only Stanford students are eligible during onboarding.
              </p>
              <div className="info-tags">
                <span className="tag">🎓 Stanford Only</span>
                <span className="tag">❄️ Launch: Winter 2025</span>
                <span className="tag">🔒 Privacy-first</span>
              </div>
            </div>
            
            <div className="waitlist-form-container">
              <div className="waitlist-cta">
                <p className="waitlist-cta-text">To get early access and connect Sift to your account, click the button below to continue on the secure backend.</p>
                <a className="form-submit-btn" href={loginUrl}>Connect with Google</a>
                <p style={{marginTop: '12px', color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem'}}>Only Stanford emails will be eligible during onboarding.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <p>&copy; 2025 Sift. All rights reserved.</p>
          <div className="footer-links">
            <a href="#privacy">Privacy</a>
            <a href="#terms">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
