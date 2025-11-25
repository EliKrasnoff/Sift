from models import db, SyncCost
from datetime import datetime

class CostTracker:
    """Track and calculate API costs"""
    
    # Pricing (as of 2024 - update these with current prices)
    PRICING = {
        'gpt-4': {
            'input': 0.03,   # per 1K tokens
            'output': 0.06   # per 1K tokens
        },
        'gpt-4o': {
            'input': 0.0025,   # per 1K tokens
            'output': 0.01   # per 1K tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.0005,  # per 1K tokens
            'output': 0.0015  # per 1K tokens
        },
        # Gmail/Calendar APIs are free for reasonable usage
        'gmail_api': 0.0,
        'calendar_api': 0.0
    }
    
    def __init__(self, user, model='gpt-4o'):
        self.user = user
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0
        self.gmail_calls = 0
        self.calendar_calls = 0
        self.emails_processed = 0
        self.events_extracted = 0
    
    def add_openai_usage(self, input_tokens, output_tokens):
        """Track OpenAI API usage"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
    
    def add_gmail_call(self):
        """Track Gmail API call"""
        self.gmail_calls += 1
    
    def add_calendar_call(self):
        """Track Calendar API call"""
        self.calendar_calls += 1
    
    def calculate_openai_cost(self):
        """Calculate OpenAI cost"""
        pricing = self.PRICING.get(self.model, self.PRICING['gpt-4o'])
        
        input_cost = (self.input_tokens / 1000) * pricing['input']
        output_cost = (self.output_tokens / 1000) * pricing['output']
        
        return input_cost + output_cost
    
    def calculate_total_cost(self):
        """Calculate total cost"""
        openai_cost = self.calculate_openai_cost()
        # Gmail and Calendar are free for now
        return openai_cost
    
    def save(self):
        """Save cost tracking to database"""
        sync_cost = SyncCost(
            user_id=self.user.id,
            emails_processed=self.emails_processed,
            events_extracted=self.events_extracted,
            openai_input_tokens=self.input_tokens,
            openai_output_tokens=self.output_tokens,
            openai_cost=self.calculate_openai_cost(),
            gmail_api_calls=self.gmail_calls,
            calendar_api_calls=self.calendar_calls,
            total_cost=self.calculate_total_cost(),
            model_used=self.model
        )
        
        db.session.add(sync_cost)
        db.session.commit()
        
        return sync_cost
    
    def get_summary(self):
        """Get cost summary"""
        return {
            'openai_input_tokens': self.input_tokens,
            'openai_output_tokens': self.output_tokens,
            'openai_cost': round(self.calculate_openai_cost(), 4),
            'gmail_api_calls': self.gmail_calls,
            'calendar_api_calls': self.calendar_calls,
            'total_cost': round(self.calculate_total_cost(), 4),
            'emails_processed': self.emails_processed,
            'events_extracted': self.events_extracted
        }