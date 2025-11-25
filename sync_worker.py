from gmail_service import GmailService
from calendar_service import CalendarService
from event_extractor import EventExtractor
from models import db, User, ProcessedEmail, CalendarEvent
from datetime import datetime
from cost_tracker import CostTracker



class SyncWorker:
    """Orchestrate the email → event → calendar sync process"""
    
    def __init__(self, user):
        """
        Initialize sync worker for a user
        
        Args:
            user: User object from database
        """
        self.user = user
        self.gmail_service = GmailService(user)
        self.calendar_service = CalendarService(user)
        self.event_extractor = EventExtractor()
    
    def _parse_email_date(self, date_string):
        """Parse email date string to datetime"""
        if not date_string:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_string)
        except:
            try:
                # Try RFC 2822 format (common in emails)
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_string)
            except:
                return None
    
    def run_sync(self, max_emails=None):
        """Main sync process with cost tracking"""
        print(f"\n=== Starting sync for {self.user.email} ===")
        
        # Initialize cost tracker
        cost_tracker = CostTracker(self.user, model='gpt-4o')
        
        results = {
            'emails_scanned': 0,
            'emails_processed': 0,
            'events_extracted': 0,
            'events_added': 0,
            'duplicates_skipped': 0,
            'large_emails': [],
            'errors': [],
            'costs': {}  # Will be populated at the end
        }
    
        # Track events we've already added (to avoid duplicates across emails)
        added_events_cache = set()  # Store (title, start_datetime) tuples
        
        try:
            calendar_id = self.calendar_service.create_sift_calendar()
            print(f"Using calendar: {calendar_id}")
            
            # Fetch emails
            emails = self.gmail_service.get_recent_emails(days=1, max_results=25, exclude_categories=True)

            # Safety check
            if emails is None:
                emails = []
                
            results['emails_scanned'] = len(emails)
            print(f"Found {len(emails)} emails to scan")
            
            # Process each email
            for email in emails:
                try:
                    # Check if already processed
                    already_processed = ProcessedEmail.query.filter_by(
                        user_id=self.user.id,
                        email_id=email['id']
                    ).first()
                    
                    if already_processed:
                        print(f"Skipping already processed email: {email['subject']}")
                        continue
                    
                    # Extract events from email
                    events, token_usage = self.event_extractor.extract_events(email)  # Now returns tuple
                    
                    # Track token usage
                    cost_tracker.add_openai_usage(
                        token_usage['input_tokens'],
                        token_usage['output_tokens']
                    )
                    
                    # Track Gmail API calls (approximate)
                    cost_tracker.add_gmail_call()  # For fetching email list
                    cost_tracker.gmail_calls += 1  # For fetching each email details
                    
                    if events:
                        from datetime import datetime, timedelta
                        now = datetime.now()
                        
                        # Only keep future events (or events from today)
                        future_events = []
                        for event in events:
                            try:
                                event_start = datetime.fromisoformat(event['start_datetime'])
                                # Keep events that haven't ended yet (or started today)
                                if event_start.date() >= now.date():
                                    future_events.append(event)
                                else:
                                    print(f"Skipping past event: {event['title']} on {event_start.date()}")
                            except:
                                # If we can't parse the date, keep the event to be safe
                                future_events.append(event)
                        
                        events = future_events
                    # Check if email has too many events
                    MAX_EVENTS_PER_EMAIL = 60
                    if events and len(events) > MAX_EVENTS_PER_EMAIL:
                        print(f"⚠️ Email has {len(events)} events (max {MAX_EVENTS_PER_EMAIL})")
                        
                        # Store info about the overflow
                        results['large_emails'] = results.get('large_emails', [])
                        results['large_emails'].append({
                            'subject': email['subject'],
                            'total_events': len(events),
                            'capped_at': MAX_EVENTS_PER_EMAIL,
                            'email_id': email['id']
                        })
                        
                        # Only process first 60 events
                        events = events[:MAX_EVENTS_PER_EMAIL]
                        
                        print(f"Processing first {MAX_EVENTS_PER_EMAIL} events. User will be notified.")

                    if events:
                        print(f"Found {len(events)} event(s) in: {email['subject']}")
                        results['events_extracted'] += len(events)
                        
                        event_ids = []
                        
                        # Add each event to calendar (with deduplication)
                        for event in events:
                            try:
                                # Create a unique key for this event
                                event_key = (
                                    event['title'].lower().strip(),
                                    event['start_datetime']
                                )
                                
                                # Skip if we've already added this exact event
                                if event_key in added_events_cache:
                                    print(f"Skipping duplicate event: {event['title']}")
                                    results['duplicates_skipped'] += 1
                                    continue
                                
                                gcal_event = self.event_extractor.format_for_google_calendar(event)
                                event_id = self.calendar_service.add_event(gcal_event)
                                
                                # Store in database (NEW)
                                from models import CalendarEvent
                                cal_event = CalendarEvent(
                                    user_id=self.user.id,
                                    gcal_event_id=event_id,
                                    gcal_calendar_id=self.user.sift_calendar_id,
                                    event_title=event['title'],
                                    start_datetime=datetime.fromisoformat(event['start_datetime']),
                                    end_datetime=datetime.fromisoformat(event.get('end_datetime')) if event.get('end_datetime') else None,
                                    location=event.get('location')
                                )
                                db.session.add(cal_event)
                                event_ids.append(event_id)
                                
                                # Mark this event as added
                                added_events_cache.add(event_key)
                                results['events_added'] += 1
                                cost_tracker.add_calendar_call()  # Track calendar API call

                                
                            except Exception as e:
                                print(f"Error adding event to calendar: {e}")
                                results['errors'].append({
                                    'email': email['subject'],
                                    'event': event.get('title', 'Unknown'),
                                    'error': str(e)
                                })
                        
                        # Mark email as processed with enhanced info (UPDATED)
                        processed = ProcessedEmail(
                            user_id=self.user.id,
                            email_id=email['id'],
                            email_subject=email['subject'],
                            email_date=self._parse_email_date(email.get('date')),
                            event_created=len(event_ids) > 0,
                            events_count=len(event_ids),
                            processing_status='success',
                            calendar_event_id=event_ids[0] if event_ids else None
                        )
                        db.session.add(processed)
                    else:
                        # No events found
                        processed = ProcessedEmail(
                            user_id=self.user.id,
                            email_id=email['id'],
                            event_created=False
                        )
                        db.session.add(processed)
                    
                    results['emails_processed'] += 1
                    db.session.commit()
                    
                except Exception as e:
                    print(f"Error processing email {email['subject']}: {e}")
                    results['errors'].append({
                        'email': email['subject'],
                        'error': str(e)
                    })
                    db.session.rollback()
                    continue
            
            # Update last sync time
            self.user.last_sync = datetime.utcnow()
            db.session.commit()
            
            print(f"\n=== Sync complete ===")
            print(f"Emails scanned: {results['emails_scanned']}")
            print(f"Emails processed: {results['emails_processed']}")
            print(f"Events extracted: {results['events_extracted']}")
            print(f"Events added to calendar: {results['events_added']}")
            print(f"Duplicate events skipped: {results['duplicates_skipped']}")
            print(f"Errors: {len(results['errors'])}")
            
            cost_tracker.emails_processed = results['emails_processed']
            cost_tracker.events_extracted = results['events_extracted']
            
            # Save cost tracking
            cost_tracker.save()
            
            # Add cost summary to results
            results['costs'] = cost_tracker.get_summary()
            
            print(f"\n=== Cost Summary ===")
            print(f"OpenAI tokens: {results['costs']['openai_input_tokens']} input, {results['costs']['openai_output_tokens']} output")
            print(f"OpenAI cost: ${results['costs']['openai_cost']:.4f}")
            print(f"Total cost: ${results['costs']['total_cost']:.4f}")

            return results
            
        except Exception as e:
            print(f"Fatal error during sync: {e}")
            import traceback
            traceback.print_exc()
            results['errors'].append({'fatal': str(e)})
            return results
    
    def test_single_email(self, email_subject_substring):
        """
        Test event extraction on a single email (for debugging)
        
        Args:
            email_subject_substring (str): Part of the subject to search for
            
        Returns:
            dict: Extracted events
        """
        query = f'subject:"{email_subject_substring}"'
        emails = self.gmail_service.search_emails(query, max_results=1)
        
        if not emails:
            print(f"No email found with subject containing: {email_subject_substring}")
            return None
        
        email = emails[0]
        print(f"\nTesting event extraction on: {email['subject']}")
        print(f"From: {email['sender']}")
        print(f"Date: {email['date']}")
        print(f"\nBody preview: {email['snippet']}\n")
        
        events, token_usage = self.event_extractor.extract_events(email)  # FIX: Now receives tuple
        
        print(f"\nToken usage: {token_usage['input_tokens']} input, {token_usage['output_tokens']} output")
        print(f"\nExtracted {len(events)} event(s):")
        for i, event in enumerate(events, 1):
            print(f"\nEvent {i}:")
            print(f"  Title: {event['title']}")
            print(f"  Start: {event['start_datetime']}")
            print(f"  End: {event['end_datetime']}")
            print(f"  Location: {event.get('location', 'Not specified')}")
            print(f"  RSVP: {event.get('rsvp_required', False)}")
        
        return events
