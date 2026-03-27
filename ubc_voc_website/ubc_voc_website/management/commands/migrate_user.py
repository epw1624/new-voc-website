"""
select id, email from members_table
"""
from django.db.utils import IntegrityError
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

import csv
from allauth.account.models import EmailAddress

User = get_user_model()

class Command(BaseCommand):
    help="Migrate Users from CSV"

    def handle(self, *args, **options):
        path="user.csv"

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=["id", "email"])

            for row in reader:
                for row in reader:
                    # 1. Clean the email immediately
                    raw_email = row.get('email', '').strip().lower()
                    if not raw_email:
                        continue

                    # 2. Manual check instead of get_or_create
                    user = User.objects.filter(email__iexact=raw_email).first()

                    if user:
                        self.stdout.write(f"User {raw_email} already exists")
                    else:
                        try:
                            user = User.objects.create(
                                email=raw_email,
                                # Add other fields here (first_name, last_name, etc.)
                            )
                            self.stdout.write(self.style.SUCCESS(f"Created user {raw_email}"))
                        except IntegrityError:
                            # This is a safety net in case of concurrent writes
                            self.stdout.write(self.style.WARNING(f"Skipping {raw_email}: Integrity collision"))

                email_obj, email_created = EmailAddress.objects.get_or_create(
                    user=user,
                    email=user.email,
                    defaults={
                        "verified": True,
                        "primary": True
                    }
                )

                if not email_created:
                    email_obj.verified = True
                    email_obj.primary = True
                    email_obj.save()

        self.stdout.write(self.style.SUCCESS("User migration complete"))        