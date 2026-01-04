from django.core.management.base import BaseCommand
from grandpa.notifications import send_next_day_events

class Command(BaseCommand):
    help = 'Sends the next day events to the Twilio conversation'

    def handle(self, *args, **options):
        self.stdout.write('Sending next day events...')
        try:
            sid = send_next_day_events()
            if sid:
                self.stdout.write(self.style.SUCCESS(f'Successfully sent events. SID: {sid}'))
            else:
                self.stdout.write(self.style.WARNING('No message sent (maybe no events or error).'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
