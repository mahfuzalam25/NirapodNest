from django.core.management.base import BaseCommand
from django.utils import timezone
from home.models import AIRadarAlert
from property.models import Property
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends hourly AI Market Radar summaries to users based on their preferred time.'

    def handle(self, *args, **kwargs):
        # 1. Get the current local hour
        current_hour = timezone.localtime(timezone.now()).hour
        self.stdout.write(f"--- Waking up AI Radar for Hour: {current_hour}:00 ---")

        # 2. Find all active radars that want a summary at THIS exact hour
        radars_due_now = AIRadarAlert.objects.filter(
            is_active=True,
            frequency='Daily Summary',
            preferred_time__hour=current_hour
        )

        if not radars_due_now.exists():
            self.stdout.write(self.style.WARNING("No radars scheduled for this hour. Going back to sleep."))
            return

        emails_sent = 0

        # 3. Process each radar
        for radar in radars_due_now:
            target_purpose = "Sale" if radar.purpose == "Buy" else "Rent"
            
            # Ask the database for properties matching the radar criteria
            matches = Property.objects.filter(
                purpose=target_purpose,
                city__iexact=radar.district,
                area__icontains=radar.area,
                price__lte=radar.max_budget
            )[:5] # Limit to top 5 matches
            
            if matches.exists():
                if radar.notify_email:
                    try:
                        send_mail(
                            subject=f"Your Daily AI Radar Summary: {radar.area}",
                            message=f"Hi {radar.user.user.first_name},\n\nWe found {matches.count()} new properties matching your radar today! Log in to AponThikana to view them.\n\n- The AponThikana AI",
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[radar.user.user.email],
                            fail_silently=True
                        )
                        emails_sent += 1
                        self.stdout.write(self.style.SUCCESS(f"Sent summary to {radar.user.user.email}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to send email to {radar.user.user.email}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"--- AI Radar Complete. Sent {emails_sent} summaries. ---"))