from django.contrib import admin
from .models import CalendarMonth, CalendarEvent
import json
from django.utils.safestring import mark_safe
from django.utils.html import format_html

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('day', 'hour', 'minute', 'title', 'calendar_month')
    list_select_related = ('calendar_month',)
    ordering = ('-day', '-hour', '-minute')
    list_filter = ('calendar_month',)
    search_fields = ('title', 'original_text')

    def get_ordering(self, request):
        # If filtering by calendar_month, default to ascending order.
        # Check for the specific lookup parameter used by Django admin for foreign keys.
        if 'calendar_month__id__exact' in request.GET:
            return ('day', 'hour', 'minute')
        return super().get_ordering(request)

class CalendarEventInline(admin.TabularInline):
    model = CalendarEvent
    extra = 0
    ordering = ('day', 'hour', 'minute')
    fields = ('day', 'hour', 'minute', 'am_pm', 'title', 'color', 'all_day', 'featured')

@admin.register(CalendarMonth)
class CalendarMonthAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'status_display', 'month', 'year', 'successfully_parsed')
    list_display_links = ('id', 'created_at')
    ordering = ('-year', '-month')
    readonly_fields = ('parsed_data_pretty', 'created_at')
    fields = ('image', 'created_at', 'month', 'year', 'successfully_parsed', 'notes_or_announcements', 'parsed_data_pretty')
    inlines = [CalendarEventInline]

    def status_display(self, obj):
        if not obj.parsed_data:
            return "Pending"
        if obj.parsed_data.get('status') == 'processing':
            return "⏳ Processing..."
        if obj.parsed_data.get('successfully_parsed'):
            return "✅ Success"
        return "❌ Failed"
    status_display.short_description = "Status"

    def parsed_data_pretty(self, obj):
        if not obj.parsed_data:
            return "-"
        
        # If still processing, show a message
        if obj.parsed_data.get('status') == 'processing':
            return "Processing in background... Refresh page in a few seconds."

        # Format JSON for display
        json_str = json.dumps(obj.parsed_data, indent=2)
        return format_html('<pre>{}</pre>', json_str)
    
    parsed_data_pretty.short_description = "Parsed Data (JSON)"
