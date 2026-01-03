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
def list_events(request, month: Optional[int] = None, day: Optional[int] = None, year: Optional[int] = None, scope: str = "day"):
    qs = CalendarEvent.objects.all().select_related('calendar_month')

    # Default to current year if not provided, for date calculations
    current_year = year or datetime.now().year
    
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
