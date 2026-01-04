from django.conf import settings
from datetime import datetime
from zoneinfo import ZoneInfo

def get_current_date():
    """
    Returns the current date as a timezone-aware datetime in America/Chicago.
    If DEBUG=True and FAKE_DATE is set in settings, uses that date instead.
    """
    tz = ZoneInfo("America/Chicago")
    
    if settings.DEBUG and getattr(settings, 'FAKE_DATE', None):
        fake_date_str = settings.FAKE_DATE
        if fake_date_str:
            try:
                # Parse YYYY-MM-DD
                dt = datetime.strptime(fake_date_str, "%Y-%m-%d")
                # Make it timezone aware in Chicago time
                return dt.replace(tzinfo=tz)
            except ValueError:
                # If parsing fails, fall back to current time
                pass
    
    return datetime.now(tz)
