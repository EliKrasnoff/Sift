from gmail_service import GmailService
from calendar_service import CalendarService
from event_extractor import EventExtractor
from cost_tracker import CostTracker
from models import db, ProcessedEmail, CalendarEvent
from datetime import datetime


class SyncWorker:
    """Orchestrates the email-to-calendar sync process"""
    
    def __init__(self, user):
        self.user = user
        self.gmail = GmailService(user)
        self.calendar = CalendarService(user)
        self.extractor = EventExtractor()
        self.cost_tracker = CostTracker(user)
        
    def run_sync(self, days=1, progress_callback=None):
        """
        Run the full sync process
        
        Args:
            days: Number of days to look back for emails
            progress_callback: Function to call with progress updates
                              (stage, current, total, message)
        
        Returns:
            dict: Summary of sync results
        """
        print(f"\n=== Starting sync for {self.user.email} ===")
        
        results = {
            'emails_scanned': 0,
            'emails_processed': 0,
            'emails_skipped': 0,  # NEW: Track skipped emails
            'events_extracted': 0,
            'events_added': 0,
            'duplicates_skipped': 0,
            'errors': [],
            'costs': None
        }
        
        try:
            # Progress: Setup
            if progress_callback:
                progress_callback('setup', 1, 4, '[setup] Initializing calendar... (1/4)')
            
            # Ensure Sift calendar exists
            calendar_id = self.calendar.create_sift_calendar()
            print(f"Using calendar: {calendar_id}")
            self.cost_tracker.add_calendar_call()
            
            if progress_callback:
                progress_callback('setup', 2, 4, '[setup] Connecting to Gmail... (2/4)')
            
            # Get recent emails
            if progress_callback:
                progress_callback('setup', 3, 4, '[setup] Fetching recent emails... (3/4)')
            
            emails = self.gmail.get_recent_emails(days=days)
            self.cost_tracker.add_gmail_call()
            
            if not emails:
                print("No emails found to process")
                if progress_callback:
                    progress_callback('complete', 1, 1, '[complete] No emails found')
                results['costs'] = self.cost_tracker.get_summary()
                return results
            
            results['emails_scanned'] = len(emails)
            
            if progress_callback:
                progress_callback('setup', 4, 4, f'[setup] Found {len(emails)} emails to scan (4/4)')
            
            # Process each email
            total_emails = len(emails)
            for idx, email in enumerate(emails, 1):
                email_id = email['id']
                email_subject = email['subject'][:50] + '...' if len(email['subject']) > 50 else email['subject']
                
                if progress_callback:
                    progress_callback(
                        'processing', 
                        idx, 
                        total_emails, 
                        f'[processing] Email {idx}/{total_emails}: {email_subject}... ({idx}/{total_emails})'
                    )
                
                # Check if already processed
                existing = ProcessedEmail.query.filter_by(
                    user_id=self.user.id,
                    email_id=email_id
                ).first()
                
                if existing:
                    print(f"Skipping already processed email: {email['subject']}")
                    results['emails_skipped'] += 1  # Track skipped
                    continue
                
                # Process this email
                try:
                    events, token_usage = self.extractor.extract_events(email, progress_callback=progress_callback)
                    
                    # Track costs
                    self.cost_tracker.add_openai_usage(
                        token_usage['input_tokens'],
                        token_usage['output_tokens']
                    )
                    self.cost_tracker.emails_processed += 1
                    results['emails_processed'] += 1
                    
                    # Record that we processed this email
                    processed = ProcessedEmail(
                        user_id=self.user.id,
                        email_id=email_id,
                        email_subject=email['subject'],
                        events_count=len(events),
                        event_created=len(events) > 0
                    )
                    db.session.add(processed)
                    db.session.commit()
                    
                    # Add events to calendar
                    for event in events:
                        try:
                            gcal_event = self.extractor.format_for_google_calendar(
                                event, 
                                email_id=email_id,
                                email_subject=email['subject']
                            )
                            
                            if not gcal_event:
                                continue
                            
                            # Check for duplicate events
                            if self._is_duplicate_event(gcal_event):
                                print(f"Skipping duplicate event: {gcal_event['summary']}")
                                results['duplicates_skipped'] += 1
                                continue
                            
                            # Add to calendar
                            event_id = self.calendar.add_event(gcal_event)
                            self.cost_tracker.add_calendar_call()
                            
                            # Record the calendar event
                            cal_event = CalendarEvent(
                                user_id=self.user.id,
                                processed_email_id=processed.id,
                                gcal_event_id=event_id,
                                gcal_calendar_id=self.user.sift_calendar_id,
                                event_title=gcal_event['summary'],
                                start_datetime=datetime.fromisoformat(gcal_event['start']['dateTime']),
                                end_datetime=datetime.fromisoformat(gcal_event['end']['dateTime']),
                                location=gcal_event.get('location')
                            )
                            db.session.add(cal_event)
                            db.session.commit()
                            
                            results['events_added'] += 1
                            results['events_extracted'] += 1
                            self.cost_tracker.events_extracted += 1
                            
                        except Exception as e:
                            print(f"Error adding event to calendar: {e}")
                            results['errors'].append(f"Calendar error: {str(e)}")
                    
                except Exception as e:
                    print(f"Error processing email {email_id}: {e}")
                    results['errors'].append(f"Email {email_id}: {str(e)}")
                    
                    # Still record as processed (with error) so we don't retry
                    processed = ProcessedEmail(
                        user_id=self.user.id,
                        email_id=email_id,
                        email_subject=email['subject'],
                        processing_status='error',
                        error_message=str(e)
                    )
                    db.session.add(processed)
                    db.session.commit()
            
            # Save costs
            self.cost_tracker.save()
            results['costs'] = self.cost_tracker.get_summary()
            
            # Final progress update
            if progress_callback:
                progress_callback('complete', total_emails, total_emails, f'[complete] Sync complete! ({total_emails}/{total_emails})')
            
            # Print summary
            print(f"\n=== Sync complete ===")
            print(f"Emails scanned: {results['emails_scanned']}")
            print(f"Emails processed: {results['emails_processed']}")
            print(f"Emails skipped (already processed): {results['emails_skipped']}")
            print(f"Events extracted: {results['events_extracted']}")
            print(f"Events added to calendar: {results['events_added']}")
            print(f"Duplicate events skipped: {results['duplicates_skipped']}")
            print(f"Errors: {len(results['errors'])}")
            
            print(f"\n=== Cost Summary ===")
            print(f"OpenAI tokens: {results['costs']['openai_input_tokens']} input, {results['costs']['openai_output_tokens']} output")
            print(f"OpenAI cost: ${results['costs']['openai_cost']:.4f}")
            print(f"Total cost: ${results['costs']['total_cost']:.4f}")
            
            return results
            
        except Exception as e:
            print(f"Sync error: {e}")
            import traceback
            traceback.print_exc()
            
            if progress_callback:
                progress_callback('error', 0, 1, f'Error: {str(e)}')
            
            results['errors'].append(str(e))
            results['costs'] = self.cost_tracker.get_summary()
            return results
    
    def _is_duplicate_event(self, gcal_event):
        """Check if this event already exists in the calendar"""
        # Check by title and start time
        existing = CalendarEvent.query.filter_by(
            user_id=self.user.id,
            event_title=gcal_event['summary'],
            start_datetime=datetime.fromisoformat(gcal_event['start']['dateTime'])
        ).first()
        
        return existing is not None