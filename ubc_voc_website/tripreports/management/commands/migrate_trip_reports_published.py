"""
SELECT p.ID, u.user_email, p.post_date, p.post_title, p.post_status, p.post_content
FROM `wp_posts` as p inner join `wp_users` as u on p.post_author = u.ID 
where post_type="post" and (post_status="publish" or post_status="private")
"""
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management import BaseCommand
from django.utils.text import slugify

from tripreports.models import TripReport, TripReportIndexPage

import csv
from datetime import datetime
import os
from wagtail.documents.models import Document
from zoneinfo import ZoneInfo

pacific_timezone = ZoneInfo("America/Vancouver")

User = get_user_model()

class Command(BaseCommand):
    help="Migrate published tirp report metadata from csv, and attach pdf content"

    def handle(self, *args, **kwargs):
        path = "trip_reports_published.csv"
        # pdf_dir = "trip_report_pdfs/"
        # pdf_files = os.listdir(pdf_dir)

        parent = TripReportIndexPage.objects.first()

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=[
                "ID",
                "post_author_email",
                "post_date",
                "post_title",
                "post_status",
                "post_content"
            ])

            orphaned_emails = set()
            missing_pdfs = set()

            for row in reader:
                try:
                    user = User.objects.get(email=row["post_author_email"])
                except User.DoesNotExist:
                    orphaned_emails.add(row["post_author_email"])
                    self.stdout.write(self.style.WARNING(f"User not found with email {row['post_author_email']}"))
                    continue

                if TripReport.objects.filter(old_id=int(row["ID"])).exists():
                    self.stdout.write(f"Skipping {row['post_title']} - report already exists")
                    continue

                # pdf = None
                # try:
                #     pdf_filename = next((p for p in pdf_files if p.startswith(f"{int(row['ID'])}_")), None)
                #     if pdf_filename:
                #         pdf_filepath = os.path.join(pdf_dir, pdf_filename)
                #         with open(pdf_filepath, 'rb') as pdf_file:
                #             pdf = Document(
                #                 title=row["post_title"],
                #                 file=File(pdf_file, name=pdf_filename)
                #             )
                #             pdf.save()
                #             self.stdout.write(self.style.SUCCESS(f"Attached pdf file for {row['post_title']}"))
                #     else:
                #         missing_pdfs.add(int(row["ID"]))
                #         self.stdout.write(self.style.ERROR(f"No pdf found for {row['post_title']}"))
                #         continue
                # except Exception as e:
                #     self.stdout.write(self.style.ERROR(f"Error processing pdf for {row['post_title']}: {e}"))

                try:
                    trip_report = TripReport(
                        title=row["post_title"],
                        slug=slugify(f"{row['post_title']}-{row['ID']}"),
                        owner=user,
                        old_id=int(row["ID"]),
                        first_published_at=datetime.strptime(row["post_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pacific_timezone),
                        # legacy_pdf=pdf,
                        is_private=row["post_status"] == "private"
                    )

                    parent.add_child(instance=trip_report)
                    trip_report.save_revision().publish()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to create trip report for {row['post_title']}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"Published trip report migration complete"))
            self.stdout.write(self.style.WARNING(f"Orphaned emails: {orphaned_emails}"))
            self.stdout.write(self.style.WARNING(f"Trip report IDs for missing PDF files: {missing_pdfs}"))
            