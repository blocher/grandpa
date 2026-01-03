import os
import json
from google import genai
from google.genai import types
from django.conf import settings
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class CalendarEvent(BaseModel):
    day: int = Field(..., description="Day of the month (1-31)")
    hour: Optional[int] = Field(None, description="Hour of the event (1-12)")
    minute: Optional[int] = Field(None, description="Minute of the event (0-59)")
    am_pm: Optional[str] = Field(None, description="am or pm")
    title: str = Field(..., description="Title of the event extracted exactly as it is written on the calendar")
    color: str = Field("black", description="Color of the event (e.g. black, red, blue, red with yellow highlight, black with yellow highlight etc.)")
    all_day: bool = Field(False, description="True if no time is specified")
    featured: bool = Field(False, description="True if the event is any color other than black or is highlighted, false otherwise")
    original_text: str = Field(..., description="The exact raw text of the event from the image, including the time string if present.")

class CalendarResponse(BaseModel):
    successfully_parsed: bool = Field(..., description="True if a calendar month/year and events were found")
    month: Optional[int] = Field(None, description="Month number (1-12)")
    year: Optional[int] = Field(None, description="Year (4 digits)")
    events: List[CalendarEvent] = Field(default_factory=list, description="List of events found")
    notes_or_announcements: Optional[List[str]] = Field(None, description="List of notes or announcements found not tied to a specific day")
class CalendarProcessor:
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'GOOGLE_API_KEY', None)
        if not self.api_key:
            # We allow initialization without key, but processing will fail
            pass
        else:
            self.client = genai.Client(api_key=self.api_key)

    def process_image(self, image_path):
        """
        Uploads an image to Gemini and extracts calendar events using Structured Outputs.
        """
        if not self.api_key:
             return {
                "successfully_parsed": False,
                "error": "GOOGLE_API_KEY not configured.",
                "month": None,
                "year": None,
                "events": []
            }

        try:
            # 1. Upload File (Best Practice: Use client.files.upload)
            # This handles large files better and returns a file reference URI
            file_ref = self.client.files.upload(file=image_path)
            
            # The prompt configuration
            current_month = datetime.now().month
            current_year = datetime.now().year

            prompt_text = f"""
            Analyze this image of a calendar. 
            Identify the month and year. Extract all events written on the days and sort them by day, hour, and minute, with all-day events last in the day. For the event title, make sure it matches exactly as the image shows.
            
            If a time is mis-formatted with a semi-colon (or is some other unusual way), like 10;30, consider it to be 10:30, and make sure the event is still included.
            
            CRITICAL: Please examine every single day box on the calendar grid thoroughly.
            Many days have multiple events. Do not stop after finding the first event for a day.
            Double-check and tripl-echeck your work:
            1. Scan the calendar row by row.
            2. For each day, list ALL distinct text items as separate events.
            3. Re-add any missed events.
            4. Capture the `original_text` for every event found, even if you can't parse the time perfectly. 
               Use this field to "save" the event data.
            5. Don't forget strings like "10;30am History Facts" even though the time is mis-formatted, it's still an event.
            
            Defaults if not visible: Month {current_month}, Year {current_year}.
            """
            
            # 2. Use Structured Outputs with Pydantic Schema
            # Using model='gemini-3-pro-preview' as requested and verified.
            model_name = "gemini-3-pro-preview"
            
            # Configure generation with schema
            # We enable "thinking" by using a model that supports it (gemini-3-pro-preview does)
            # and we can encourage it via the prompt or config if explicit thinking params exist.
            # Currently for gemini-3-pro-preview, 'thinking' is often implicit or enabled via specific config if available.
            # We will rely on the prompt's instruction to "Double-check" which aligns with thinking models.
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    file_ref, # Pass the file reference directly
                    prompt_text
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CalendarResponse, # Pass the Pydantic model directly!
                    # "thinking_config": {"include_thoughts": True} # If supported by the SDK/Model version for debugging, but currently we just want better results.
                )
            )
            
            # 3. Handle Response
            if response.parsed:
                # response.parsed is already a CalendarResponse object (or dict depending on client version)
                # We can convert it to a dict for our Django model
                if hasattr(response.parsed, 'model_dump'):
                    return response.parsed.model_dump()
                elif hasattr(response.parsed, 'dict'):
                    return response.parsed.dict()
                else:
                    return response.parsed # Already a dict?

            # Fallback if parsed isn't populated for some reason
            text = response.text
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())

        except Exception as e:
            return {
                "successfully_parsed": False,
                "error": str(e),
                "month": None,
                "year": None,
                "events": []
            }
