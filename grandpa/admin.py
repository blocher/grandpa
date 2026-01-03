from django.contrib import admin
from .models import CalendarImage, CalendarMonth
import json
from django.utils.safestring import mark_safe
from django.utils.html import format_html

@admin.register(CalendarMonth)
class CalendarMonthAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'calendar_file')
    list_filter = ('year', 'month')
    search_fields = ('year',)

@admin.register(CalendarImage)
class CalendarImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'status_display')
    readonly_fields = ('parsed_data_pretty', 'created_at')
    fields = ('image', 'created_at', 'parsed_data_pretty')

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
