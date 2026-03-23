from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.utils import timezone

from membership.models import Membership

import csv

User = get_user_model()

OUTPUT_FILENAME = "student_members.csv"

class Command(BaseCommand):
    help="Export a csv with the user id, email and student number of all current student members"

    def handle(self, *args, **kwargs):
        student_memberships = Membership.objects.filter(
            end_date__gte=timezone.localdate(),
            type=Membership.MembershipType.REGULAR,
            active=True
        ).select_related("user", "user__profile")

        try:
            with open(OUTPUT_FILENAME, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["VOC ID", "Email", "Student Number"])
                for membership in student_memberships:
                    user = membership.user
                    profile = getattr(user, "profile", None)
                    student_number = profile.student_number if profile else ""

                    writer.writerow([
                        user.id,
                        user.email,
                        student_number
                    ])
            
            self.stdout.write(self.style.SUCCESS(f"Successfully exported {student_memberships.count()} student members to {OUTPUT_FILENAME}"))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))