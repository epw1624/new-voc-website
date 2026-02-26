from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from gear.models import Rental

from datetime import timedelta
from zoneinfo import ZoneInfo

pacific_timezone = ZoneInfo("America/Vancouver")

class Command(BaseCommand):
    help = "Send gear return reminder emails"

    def handle(self, *args, **kwargs):
        today = timezone.localtime(timezone.now(), pacific_timezone).date()

        near_due_rentals = Rental.objects.filter(
            return_date__isnull=True,
            due_date__in=(today + timedelta(days=1), today + timedelta(days=2))
        )
        overdue_rentals = Rental.objects.filter(
            return_date__isnull=True,
            lost=False,
            due_date__lt=today
        )

        if not near_due_rentals.exists():
            self.stdout.write("No near-due rentals")
        else:
            for rental in near_due_rentals:
                context = {
                    "name": rental.member.display_name,
                    "days_until_due": (rental.due_date - today).days,
                    "rental": rental
                }
                text_body = render_to_string(
                    "gear/emails/gear_return_reminder.txt",
                    context
                )
                html_body = render_to_string(
                    "gear/emails/gear_return_reminder.html",
                    context
                )
                message = EmailMultiAlternatives(
                    subject="VOC Gear Rental Due Soon!",
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[rental.member.email]
                )
                message.attach_alternative(html_body, "text/html")
                message.send()

        if not overdue_rentals.exists():
            self.stdout.write("No overdue rentals")
        else:
            for rental in overdue_rentals:
                context = {
                    "name": rental.member.display_name,
                    "days_overdue": (today - rental.due_date).days,
                    "rental": rental
                }
                text_body = render_to_string(
                    "gear/emails/overdue_gear_reminder.txt",
                    context
                )
                html_body = render_to_string(
                    "gear/emails/overdue_gear_reminder.html",
                    context
                )
                message = EmailMultiAlternatives(
                    subject="Overdue VOC Gear Rental",
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[rental.member.email]
                )
                message.attach_alternative(html_body, "text/html")
                message.send()