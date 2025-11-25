import openai
import json
from config import Config
from datetime import datetime


class EventExtractor:
    """Extract event information from email text using Azure OpenAI"""
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        # Configure Azure OpenAI
        openai.api_type = "azure"
        openai.api_key = Config.AZURE_OPENAI_KEY
        openai.api_base = Config.AZURE_OPENAI_ENDPOINT
        openai.api_version = "2023-05-15"
        
        self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT
    
    def extract_events(self, email_data, progress_callback=None):
        """
        Extract event information from an email
        
        Args:
            email_data (dict): Email with 'subject', 'body', 'sender', 'date'
            progress_callback (function): Optional callback for progress updates
            
        Returns:
            tuple: (events list, token_usage dict)
        """
        import time
        prompt = self._build_extraction_prompt(email_data)

        max_retries = 3
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                response = openai.ChatCompletion.create(
                    engine=self.deployment_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting event information from emails. Always return valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=10000
                )
            
                result_text = response.choices[0].message.content.strip()

                # Remove markdown code blocks if present
                if result_text.startswith('```json'):
                    result_text = result_text[7:]
                if result_text.startswith('```'):
                    result_text = result_text[3:]
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
                result_text = result_text.strip()

                # Parse JSON response
                result = json.loads(result_text)

                events = result.get('events', [])

                # Get token usage from response
                token_usage = {
                    'input_tokens': response.usage.prompt_tokens,
                    'output_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }

                print(f"Extracted {len(events)} event(s) from email: {email_data['subject']}")
                print(f"Token usage: {token_usage['input_tokens']} input, {token_usage['output_tokens']} output")

                return events, token_usage
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Response was: {result_text}")
                return [], {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
            except Exception as e:
                error_message = str(e)
                
                # Check if it's a rate limit error
                if 'rate limit' in error_message.lower() and attempt < max_retries - 1:
                    print(f"Rate limit hit, waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}")
                    
                    # Report progress with countdown
                    if progress_callback:
                        for countdown in range(retry_delay, 0, -1):
                            progress_callback(
                                'rate_limit',
                                retry_delay - countdown + 1,  # Current progress (1, 2, 3...)
                                retry_delay,                   # Total
                                f'⏸️ Rate limit reached. Waiting {countdown}s before retry {attempt + 1}/{max_retries}...'
                            )
                            time.sleep(1)
                    else:
                        time.sleep(retry_delay)
                    
                    retry_delay *= 2  # Exponential backoff
                    continue
                
                # If not rate limit or last retry, return empty
                print(f"Error extracting events: {e}")
                return [], {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}


    def _build_extraction_prompt(self, email_data):
        """Build the prompt for event extraction"""
        current_year = datetime.now().year
        
        prompt = f"""
Extract ALL event information from this email. Be concise.

EMAIL:
Subject: {email_data['subject']}
From: {email_data['sender']}
Body: {email_data['body']}

CRITICAL: Extract EVERY event mentioned. If there are many events, still include all of them. However, ensure that the 
events you extract are seemingly targetted to the email recipient, and not just mentioned in passing. For example, if
an email mentions a meeting won't happen because of some other event, do NOT extract that other event (the conflict). ALSO,
if an email doesn't include critical information about the event (e.g. no date or time), do NOT make up that information - 
only extract what is clearly specified or can be reliably inferred. If the email does not contain this information,
it's likely because the event is not intended for the recipient.

Also VERY critical for events scheduled in an email chain between people: only include events that have been confirmed, 
NOT proposed times. So, for example, if an emails proposes a few possible dates for a meeting but doesn't confirm one, 
do NOT extract that as an event. Only extract the event once an event has been confirmed.

Return ONLY valid JSON in this EXACT format (no additional text):
{{
  "events": [
    {{
      "title": "Event Name",
      "start_datetime": "YYYY-MM-DDTHH:MM:SS",
      "end_datetime": "YYYY-MM-DDTHH:MM:SS",
      "location": "Location",
      "description": "Brief description",
      "rsvp_required": false,
      "rsvp_link": null
    }}
  ]
}}

IMPORTANT: 
- ALWAYS provide end_datetime. If not specified, estimate based on event type (e.g., 1 hour for meetings, 3 hours for parties).
- Keep descriptions under 50 words each.
- If no events found, return: {{"events": []}}
- Current year is {current_year}. Assume Pacific time zone, unless the email specifies otherwise.
- Also very important, don't add events that have already happened (i.e., dates in the past).
"""
        return prompt
    
    def format_for_google_calendar(self, event, email_id=None, email_subject=None):
        """
        Convert extracted event to Google Calendar API format
        
        Args:
            event (dict): Extracted event data
            email_id (str): Gmail message ID (optional)
            email_subject (str): Email subject (optional)
            
        Returns:
            dict: Google Calendar event object
        """
        from datetime import datetime, timedelta
        
        start_dt = event.get('start_datetime')
        end_dt = event.get('end_datetime')
        
        # Handle missing start_datetime
        if not start_dt or start_dt == 'None' or start_dt == 'null':
            print(f"Warning: Event '{event.get('title')}' has no start time, skipping")
            return None
        
        # Parse start datetime
        try:
            start_obj = datetime.fromisoformat(start_dt)
        except Exception as e:
            print(f"Error parsing start_datetime '{start_dt}': {e}")
            return None
        
        # Handle missing end_datetime
        if not end_dt or end_dt == 'None' or end_dt == 'null':
            end_obj = start_obj + timedelta(hours=1)
        else:
            try:
                end_obj = datetime.fromisoformat(end_dt)
            except Exception as e:
                print(f"Error parsing end_datetime '{end_dt}', using start + 1 hour")
                end_obj = start_obj + timedelta(hours=1)
        
        # Build description with email link
        description = event.get('description', '')
        
        # Add source email link
        if email_id:
            gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{email_id}"
            description += f"\n\n📧 Source Email: {gmail_link}"
            if email_subject:
                description += f"\nSubject: {email_subject}"
        
        gcal_event = {
            'summary': event['title'],
            'start': {
                'dateTime': start_obj.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_obj.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'description': description
        }
        
        if event.get('location'):
            gcal_event['location'] = event['location']
        
        if event.get('rsvp_required'):
            gcal_event['description'] += f"\n\n⚠️ RSVP Required"
            if event.get('rsvp_link'):
                gcal_event['description'] += f"\nRSVP: {event['rsvp_link']}"
        
        return gcal_event