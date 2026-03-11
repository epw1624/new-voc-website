"""
SELECT 
    i.g_title AS title, 
    i.g_description AS description, 
    f.g_pathComponent AS filename,
    p.g_pathComponent AS album_name
FROM g2_Item i
JOIN g2_FileSystemEntity f ON i.g_id = f.g_id
JOIN g2_ChildEntity c ON i.g_id = c.g_id
JOIN g2_FileSystemEntity p ON c.g_parentId = p.g_id
WHERE i.g_canContainChildren = 0;
"""

from django.core.management import BaseCommand

import csv

from gallery.models import GalleryPhoto

class Command(BaseCommand):
    help="Import legacy gallery data from S3"

    def handle(self, *args, **kwargs):
        path = "gallery.csv"
        count = 0

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=["title", "description", "filename", "album"])
            for row in reader:
                s3_key = f"{row['album']}/{row['filename']}" if row["album"] != "NULL" else row["filename"]
                obj, created = GalleryPhoto.objects.update_or_create(
                    image=s3_key,
                    defaults={
                        "title": row["title"],
                        "description": row["description"] if row["description"] != "NULL" else None,
                        "album": row["album"] if row["album"] != "NULL" else None
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Imported {row['filename']}"))
                    count += 1
                else:
                    self.stdout.write(f"{row['filename']} already exists")

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {count} gallery photos"))