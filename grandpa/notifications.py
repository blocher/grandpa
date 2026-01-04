import datetime
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from .models import CalendarEvent, CalendarMonth

def send_next_day_events():
    """
    Finds or creates a Twilio conversation with participants from settings,
    fetches the next day's events, and sends them to the conversation.
    """
    # 1. Calculate tomorrow
    now = timezone.now()
    tomorrow = now + datetime.timedelta(days=1)
    
    # Extract day, month, year
    target_day = tomorrow.day
    target_month = tomorrow.month
    target_year = tomorrow.year
    
    # 2. Fetch events
    events_qs = CalendarEvent.objects.filter(
        calendar_month__month=target_month,
        calendar_month__year=target_year,
        day=target_day
    )
    
    if not events_qs.exists():
        print(f"No events found for {tomorrow.date()}")
        return

    # Sort events manually for correct 12h time ordering
    def event_sort_key(event):
        if event.all_day:
            return (-1, 0, 0)
            
        h = event.hour or 0
        m = event.minute or 0
        ap = (event.am_pm or '').lower()
        
        # Convert to 24h for sorting
        if ap == 'pm' and h != 12:
            h += 12
        elif ap == 'am' and h == 12:
            h = 0
            
        return (0, h, m)
        
    events = sorted(list(events_qs), key=event_sort_key)
        
    # 3. Format message
    date_str = tomorrow.strftime("%A, %B %d, %Y")
    message_lines = [f"📅 Events for {date_str}:"]
    
    for event in events:
        time_str = "All Day"
        if not event.all_day and event.hour is not None:
            minute_str = f"{event.minute:02d}"
            time_str = f"{event.hour}:{minute_str} {event.am_pm}"
            
        message_lines.append(f"• {time_str}: {event.title}")
        
    message_body = "\n".join(message_lines)
    
    # 4. Setup Twilio
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        print("Twilio credentials missing in settings.")
        return

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # 5. Find or Create Conversation
    unique_name = "grandpa_calendar_events"
    conversation = None
    
    try:
        conversation = client.conversations.v1.conversations(unique_name).fetch()
        print(f"Found existing conversation: {conversation.sid}")
    except Exception:
        print("Creating new conversation...")
        conversation = client.conversations.v1.conversations.create(
            friendly_name="Grandpa's Calendar",
            unique_name=unique_name
        )
        print(f"Created conversation: {conversation.sid}")

    # 6. Manage Participants
    # Get current participants to avoid duplicates
    participants = conversation.participants.list()
    current_numbers = set()
    for p in participants:
        # Check if it's an SMS participant
        if p.messaging_binding and 'address' in p.messaging_binding:
            current_numbers.add(p.messaging_binding['address'])
            
    target_numbers = [n.strip() for n in settings.TWILIO_PARTICIPANTS if n.strip()]
    
    for number in target_numbers:
        # Normalize US numbers
        clean_number = number
        if not clean_number.startswith('+'):
            # Remove non-digits
            digits = ''.join(filter(str.isdigit, clean_number))
            if len(digits) == 10:
                clean_number = f"+1{digits}"
            elif len(digits) == 11 and digits.startswith('1'):
                 clean_number = f"+{digits}"
        
        if clean_number not in current_numbers:
            try:
                conversation.participants.create(
                    messaging_binding_address=clean_number,
                    messaging_binding_proxy_address=settings.TWILIO_PHONE_NUMBER
                )
                print(f"Added participant: {clean_number}")
            except Exception as e:
                print(f"Failed to add participant {clean_number}: {e}")
                
    # 7. Send Message
    try:
        msg = conversation.messages.create(body=message_body)
        print(f"Message sent! SID: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"Failed to send message: {e}")
        return None
