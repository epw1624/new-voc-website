"""
SELECT comment_ID, comment_post_ID, comment_author_email, comment_date, comment_parent, comment_content FROM wp_comments
"""
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from tripreports.models import Comment, TripReport

import csv
from datetime import datetime
from zoneinfo import ZoneInfo

pacific_timezone = ZoneInfo("America/Vancouver")

User = get_user_model()

class Command(BaseCommand):
    help="Migrate trip report comments from csv"

    def handle(self, *args, **kwargs):
        path = "trip_report_comments.csv"

        id_map = {}
        parent_map = {}

        orphaned_emails = set()
        missing_trip_reports = set()

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=[
                "comment_ID",
                "comment_post_ID",
                "comment_author_email",
                "comment_date",
                "comment_parent",
                "comment_content"
            ])

            self.stdout.write("Step 1: Finding all comment parents...")
            rows = list(reader)
            for row in rows:
                old_id = row["comment_ID"]
                old_parent = row["comment_parent"]
                parent_map[old_id] = old_parent

                try:
                    user = User.objects.get(email=row["comment_author_email"])
                    trip_report = TripReport.objects.get(old_id=int(row["comment_post_ID"]))
                    
                    dt = datetime.strptime(row["comment_date"], "%Y-%m-%d %H:%M:%S")
                    dt = dt.replace(tzinfo=pacific_timezone)

                    comment, created = Comment.objects.get_or_create(
                        timestamp=dt,
                        user=user,
                        trip_report=trip_report,
                        defaults={"body": row["comment_content"]}
                    )
                    
                    id_map[old_id] = comment
                except User.DoesNotExist:
                    orphaned_emails.add(row["comment_author_email"])
                    continue
                except TripReport.DoesNotExist:
                    missing_trip_reports.add(row["comment_post_ID"])
                    continue

            self.stdout.write("Step 2: Re-mapping comment parents")
            for old_id, comment in id_map.items():
                curr_parent_id = parent_map.get(old_id)
                if curr_parent_id == "0":
                    continue
                else:
                    root_parent_id = curr_parent_id
                    while parent_map.get(root_parent_id) != "0":
                        root_parent_id = parent_map[root_parent_id]

                    new_parent_id = id_map.get(root_parent_id)
                    if new_parent_id and new_parent_id != comment:
                        comment.parent = new_parent_id
                        comment.save()
            
            self.stdout.write(self.style.SUCCESS("Trip report comment migration complete"))
            self.stdout.write(self.style.WARNING(f"Orphaned emails: {orphaned_emails}"))
            self.stdout.write(self.style.WARNING(f"Missing trip reports: {missing_trip_reports}"))
