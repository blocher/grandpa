from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
from .models import CalendarEvent
from .utils import get_current_date

def calendar_view(request, year=None, month=None):
    # Pass initial date to template if provided
    context = {}
    if year and month:
        context['initial_date'] = f"{year}-{month:02d}-01"
    else:
        # If no date provided in URL, use our custom current date logic
        current_date = get_current_date()
        context['initial_date'] = current_date.strftime("%Y-%m-%d")
        context['now_date'] = current_date.strftime("%Y-%m-%d")

    return render(request, 'calendar.html', context)

def get_events_text(target_date, title_prefix):
    year = target_date.year
    month = target_date.month
    day = target_date.day
    
    # --- Check 3: Current month empty check ---
    now_chicago = get_current_date()
    
    current_month_events_exist = CalendarEvent.objects.filter(
        calendar_month__year=now_chicago.year,
        calendar_month__month=now_chicago.month
    ).exists()
    
    if not current_month_events_exist:
        # Format date: Saturday, January 3
        date_str = target_date.strftime("%A, %B %-d")
        lines = [f"Events {title_prefix}, {date_str}:"]
        lines.append("")
        lines.append("** No events entered yet. Please send a photo of this month's calendar to Ben (724-747-9347) or Elizabeth so we can add the events. ***")
        lines.append("")
        lines.append("You can call the Activity Director at EXT 3244 for assistance")
        # For the URL, we might default to current month even if empty
        site_url = settings.SITE_URL.rstrip('/')
        calendar_url = f"{site_url}/calendar/month/{year}/{month}/"
        lines.append(f"Full schedule at: {calendar_url}")
        return "\n".join(lines)

    # --- Query Events for Target Date ---
    events = CalendarEvent.objects.filter(
        calendar_month__year=year,
        calendar_month__month=month,
        day=day
    )
    
    # Helper to normalize time to (hour_24, minute)
    def normalize_time(e):
        h = e.hour
        m = e.minute or 0
        
        if h is None:
            return (24, 0) # No time -> End
            
        # If hour > 12, assume 24h format (e.g. 13-23)
        if h > 12:
            pass # already 24h
        elif h == 12:
             # 12 is tricky. 12 AM = 0, 12 PM = 12.
             if e.am_pm and e.am_pm.lower() == 'am':
                 h = 0
        else: # 0-11 or 1-11
             if e.am_pm and e.am_pm.lower() == 'pm':
                 h += 12
                 
        return (h, m)

    # Custom sort for time
    events_list = list(events)
    events_list.sort(key=lambda e: (-1, 0) if e.all_day else normalize_time(e))
    
    # Format date: Saturday, January 3
    date_str = target_date.strftime("%A, %B %-d")
    lines = [f"Events {title_prefix}, {date_str}:"]
    
    if not events_list:
        # --- Check 1: Empty Day but Month has events ---
        # We know "current month" has events from Check 3.
        # But target_date might be next month.
        target_month_has_events = CalendarEvent.objects.filter(
            calendar_month__year=year,
            calendar_month__month=month
        ).exists()
        
        if target_month_has_events:
            lines.append("No events appear to be scheduled on this day.")
        else:
            lines.append("No events found.")
    else:
        for e in events_list:
            if e.all_day:
                lines.append(f"All Day - {e.title}")
            else:
                h, m = normalize_time(e)
                if h == 24: # No time (but not all_day)
                    lines.append(f"{e.title}")
                    continue
                
                # Format back to 12h for display
                am_pm_str = "AM"
                disp_h = h
                if h >= 12:
                    am_pm_str = "PM"
                    if h > 12:
                        disp_h -= 12
                if disp_h == 0:
                    disp_h = 12
                
                minute_str = f"{m:02d}"
                lines.append(f"{disp_h}:{minute_str} {am_pm_str} - {e.title}")
    
    # --- Check 2: End of Month Warning ---
    # Check if now_chicago is last or 2nd to last day of month
    last_day_of_month = calendar.monthrange(now_chicago.year, now_chicago.month)[1]
    is_end_of_month = now_chicago.day >= (last_day_of_month - 1)
    
    if is_end_of_month:
        # Calculate next month
        if now_chicago.month == 12:
            next_month_year = now_chicago.year + 1
            next_month_month = 1
        else:
            next_month_year = now_chicago.year
            next_month_month = now_chicago.month + 1
            
        next_month_has_events = CalendarEvent.objects.filter(
            calendar_month__year=next_month_year,
            calendar_month__month=next_month_month
        ).exists()
        
        if not next_month_has_events:
            lines.append("")
            lines.append("** Please send a photo of next month's calendar to Ben (724-747-9347) or Elizabeth so we can add next month's events. ***")
            
    lines.append("")
    lines.append("You can call the Activity Director at EXT 3244 for assistance")
    
    site_url = settings.SITE_URL.rstrip('/')
    calendar_url = f"{site_url}/calendar/month/{year}/{month}/"
    lines.append(f"Full schedule at: {calendar_url}")
    
    return "\n".join(lines)

def messages_today(request):
    today = get_current_date()
    text = get_events_text(today, "today")
    return HttpResponse(text, content_type="text/plain")

def messages_tomorrow(request):
    tomorrow = get_current_date() + timedelta(days=1)
    print(f"Tomorrow: {tomorrow}")
    text = get_events_text(tomorrow, "tomorrow")
    return HttpResponse(text, content_type="text/plain")
