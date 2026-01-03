from django.db import models
import json
import threading

class CalendarMonth(models.Model):
    MONTH_CHOICES = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField()
    calendar_file = models.FileField(upload_to="calendars/", verbose_name="Calendar Field")

    class Meta:
        verbose_name = "Calendar Month"
        verbose_name_plural = "Calendar Months"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["month", "year"], name="unique_month_year")
        ]

    def __str__(self):
        return f"{self.get_month_display()} {self.year}"


class CalendarImage(models.Model):
    image = models.ImageField(upload_to='calendar_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    parsed_data = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"Calendar Image {self.id} - {self.created_at}"

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
            CalendarImage.objects.filter(pk=self.pk).update(parsed_data={"status": "processing", "successfully_parsed": False})

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
            
            # Re-fetch object or update directly
            CalendarImage.objects.filter(pk=pk).update(parsed_data=result)
        except Exception as e:
            error_data = {"successfully_parsed": False, "error": str(e), "status": "failed"}
            CalendarImage.objects.filter(pk=pk).update(parsed_data=error_data)
        finally:
            connection.close()
