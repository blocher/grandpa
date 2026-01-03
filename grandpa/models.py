from django.db import models
import json
import threading

class CalendarMonth(models.Model):
    MONTH_CHOICES = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]

    image = models.ImageField(upload_to='calendar_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    parsed_data = models.JSONField(blank=True, null=True)
    
    # Fields from CalendarResponse Pydantic model
    successfully_parsed = models.BooleanField(default=False)
    month = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    notes_or_announcements = models.JSONField(default=list, blank=True, null=True)
    
    class Meta:
        verbose_name = "Calendar Month"
        verbose_name_plural = "Calendar Months"

    def __str__(self):
        if self.month and self.year:
            # Get month name from CalendarMonth choices or default to number
            month_dict = dict(self.MONTH_CHOICES)
            month_name = month_dict.get(self.month, self.month)
            return f"{month_name} {self.year}"
        return f"Calendar Month {self.id} - {self.created_at}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Process image if it's new and has an image
        if is_new and self.image:
            # Run processing in a background thread
            thread = threading.Thread(target=self._process_image_background, args=(self.pk, self.image.path))
            thread.daemon = True # Daemonize so it doesn't block server shutdown
            thread.start()
            
            # Immediately set parsed_data to indicate processing
            CalendarMonth.objects.filter(pk=self.pk).update(parsed_data={"status": "processing", "successfully_parsed": False})

    @staticmethod
    def _process_image_background(pk, image_path):
        """
        Background task to process the image.
        Note: We must handle database connections carefully in threads in older Django, 
        but usually safe for simple updates in new threads if connection is closed.
        """
        from django.db import connection
        try:
            from .gemini import CalendarProcessor
            processor = CalendarProcessor()
            result = processor.process_image(image_path)
            
            # Re-fetch object
            calendar_month = CalendarMonth.objects.get(pk=pk)
            
            # Update CalendarMonth fields
            calendar_month.parsed_data = result
            calendar_month.successfully_parsed = result.get('successfully_parsed', False)
            calendar_month.month = result.get('month')
            calendar_month.year = result.get('year')
            calendar_month.notes_or_announcements = result.get('notes_or_announcements')
            calendar_month.save()
            
            # Create CalendarEvent objects
            events_data = result.get('events', [])
            
            # Clear existing events if any (though this is usually a new object)
            calendar_month.events.all().delete()
            
            new_events = []
            for event_data in events_data:
                new_events.append(CalendarEvent(
                    calendar_month=calendar_month,
                    day=event_data.get('day'),
                    hour=event_data.get('hour'),
                    minute=event_data.get('minute'),
                    am_pm=event_data.get('am_pm'),
                    title=event_data.get('title'),
                    color=event_data.get('color'),
                    all_day=event_data.get('all_day', False),
                    featured=event_data.get('featured', False),
                    original_text=event_data.get('original_text', '')
                ))
            
            if new_events:
                CalendarEvent.objects.bulk_create(new_events)
                
        except Exception as e:
            error_data = {"successfully_parsed": False, "error": str(e), "status": "failed"}
            CalendarMonth.objects.filter(pk=pk).update(parsed_data=error_data)
        finally:
            connection.close()


class CalendarEvent(models.Model):
    calendar_month = models.ForeignKey(CalendarMonth, on_delete=models.CASCADE, related_name='events')
    day = models.IntegerField(verbose_name="Day of the month (1-31)")
    hour = models.IntegerField(null=True, blank=True, verbose_name="Hour of the event (1-12)")
    minute = models.IntegerField(null=True, blank=True, verbose_name="Minute of the event (0-59)")
    am_pm = models.CharField(max_length=4, null=True, blank=True, verbose_name="am or pm")
    title = models.TextField(verbose_name="Title of the event")
    color = models.CharField(max_length=50, default="black", verbose_name="Color of the event")
    all_day = models.BooleanField(default=False, verbose_name="All day")
    featured = models.BooleanField(default=False, verbose_name="Featured")
    original_text = models.TextField(verbose_name="The exact raw text")

    class Meta:
        ordering = ['-day', '-hour', '-minute']
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"

    def __str__(self):
        time_str = "All Day" if self.all_day else f"{self.hour}:{self.minute:02d} {self.am_pm}"
        return f"Day {self.day} - {time_str} - {self.title}"
