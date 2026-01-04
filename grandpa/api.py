from ninja import NinjaAPI, Schema
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import CalendarEvent, CalendarMonth
from datetime import datetime, timedelta, date

api = NinjaAPI()

class CalendarEventSchema(Schema):
    id: int
    day: int
    month: int
    year: int
    hour: Optional[int] = None
    minute: Optional[int] = None
    am_pm: Optional[str] = None
    title: str
    color: str
    all_day: bool
    featured: bool
    original_text: str

    @staticmethod
    def resolve_month(obj):
        return obj.calendar_month.month

    @staticmethod
    def resolve_year(obj):
        return obj.calendar_month.year

@api.get("/events", response=List[CalendarEventSchema])
def list_events(request, 
                month: Optional[int] = None, 
                day: Optional[int] = None, 
                year: Optional[int] = None, 
                scope: str = "day",
                start: Optional[str] = None,
                end: Optional[str] = None):
    qs = CalendarEvent.objects.all().select_related('calendar_month')

    # Default to current year if not provided, for date calculations
    current_year = year or datetime.now().year

    if start and end:
        try:
            # FullCalendar sends ISO strings like '2023-09-01T00:00:00-05:00'
            # We strip time/timezone for simpler date handling
            start_date = datetime.fromisoformat(start.replace("Z", "+00:00")).date()
            end_date = datetime.fromisoformat(end.replace("Z", "+00:00")).date()
            
            # Filter for months that overlap with the range
            q_filter = Q()
            curr = start_date.replace(day=1)
            # Adjust end_date to include the full month of the end date
            target_end_month = end_date.replace(day=1)
            
            while curr <= target_end_month:
                q_filter |= Q(calendar_month__year=curr.year, calendar_month__month=curr.month)
                
                # Move to next month
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)
            
            qs = qs.filter(q_filter)
            
        except Exception as e:
            # If parsing fails, ignore start/end and fall back to other filters
            pass

    if scope == "week" and month and day:
        # Week filtering logic
        try:
            start_date = date(current_year, month, day)
        except ValueError:
            return []

        end_date = start_date + timedelta(days=6)
        
        target_dates = []
        curr = start_date
        while curr <= end_date:
            target_dates.append((curr.year, curr.month, curr.day))
            curr += timedelta(days=1)
            
        q_filter = Q()
        for y, m, d in target_dates:
            q_filter |= Q(calendar_month__year=y, calendar_month__month=m, day=d)
            
        qs = qs.filter(q_filter)
        
    elif month:
        qs = qs.filter(calendar_month__month=month)
        if day:
            qs = qs.filter(day=day)
            
        if year:
            qs = qs.filter(calendar_month__year=year)
            
    elif year:
        qs = qs.filter(calendar_month__year=year)

    return qs.order_by('calendar_month__year', 'calendar_month__month', 'day', 'hour', 'minute')
