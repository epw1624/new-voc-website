"""
SELECT 
    i.g_title AS title,
    i.g_description AS description,
    f.g_pathComponent AS filename,
    TRIM(BOTH '/' FROM CONCAT_WS('/', 
        p3.g_pathComponent, 
        p2.g_pathComponent, 
        p1.g_pathComponent
    )) AS album_name
FROM g2_Item i
JOIN g2_FileSystemEntity f ON i.g_id = f.g_id
JOIN g2_ChildEntity c1 ON i.g_id = c1.g_id
JOIN g2_FileSystemEntity p1 ON c1.g_parentId = p1.g_id
LEFT JOIN g2_ChildEntity c2 ON c1.g_parentId = c2.g_id
LEFT JOIN g2_FileSystemEntity p2 ON c2.g_parentId = p2.g_id AND p2.g_id != 1
LEFT JOIN g2_ChildEntity c3 ON c2.g_parentId = c3.g_id
LEFT JOIN g2_FileSystemEntity p3 ON c3.g_parentId = p3.g_id AND p3.g_id != 1
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

        with open(path, encoding="utf-8") as f:
            print(repr(f.readline()))
            reader = csv.DictReader(
                f, 
                fieldnames=["title", "description", "filename", "album"],
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )

            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f, fieldnames=["title", "description", "filename", "album"])
                for row in reader:
                    s3_key = f"{row['album']}/{row['filename']}" if row["album"] != "NULL" else row["filename"]
                    obj, created = GalleryPhoto.objects.update_or_create(
                        image=s3_key,
                        album=row["album"], 
                        defaults={
                            "title": row["title"] if row["title"] != "NULL" else "",
                            "description": row["description"] if row["description"] != "NULL" else None,
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Imported {row['filename']}"))
                        count += 1
                    else:
                        self.stdout.write(f"{row['filename']} already exists")

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {count} gallery photos"))