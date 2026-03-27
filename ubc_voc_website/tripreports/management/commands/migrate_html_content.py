import os
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction

from wagtail.models import Collection
from wagtail.images.models import Image
from tripreports.models import TripReport # Adjust to your app name

class Command(BaseCommand):
    help = 'Imports legacy HTML and uploads _assets images to Wagtail'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Path to the renamed_archive folder')

    def handle(self, *args, **options):
        base_dir = options['directory']
        missing_reports = set()
        
        # --- FIXED COLLECTION LOGIC ---
        root_collection = Collection.get_first_root_node()
        collection = Collection.objects.filter(name="Legacy Imports").first()
        
        if not collection:
            collection = root_collection.add_child(name="Legacy Imports")

        for folder_name in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, folder_name)
            
            if not os.path.isdir(folder_path):
                continue

            # 1. Match by old_id (folder name is the ID)
            try:
                report = TripReport.objects.get(old_id=int(folder_name))
            except (TripReport.DoesNotExist, ValueError):
                self.stdout.write(self.style.WARNING(f"ID {folder_name}: No matching TripReport found."))
                missing_reports.add(folder_name)
                continue

            html_path = os.path.join(folder_path, "index.html")
            if not os.path.exists(html_path):
                continue

            self.stdout.write(f"Processing ID {folder_name}: {report.title}...")

            # 2. Process images and rewrite HTML
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            assets_dir = os.path.join(folder_path, "_assets")
            
            with transaction.atomic():
                for img_tag in soup.find_all('img'):
                    update_node_path(img_tag, 'src', folder_name, assets_dir, collection)

                # 2. Fix Lightbox Links <a> tags
                # WordPress galleries usually wrap the <img> in an <a href="...">
                for a_tag in soup.find_all('a', href=True):
                    update_node_path(a_tag, 'href', folder_name, assets_dir, collection)

                # 3. Fix any custom data attributes (Common in JS sliders)
                for node in soup.find_all(attrs={"data-src": True}):
                    update_node_path(node, 'data-src', folder_name, assets_dir, collection)

                # 3. Save to the new legacy_html field
                report.legacy_html = str(soup)
                report.body = None

                if report.legacy_pdf:
                    pdf_doc = report.legacy_pdf
                    pdf_path = pdf_doc.file.path
                    if os.path.exists(pdf_path):
                        self.stdout.write(self.style.NOTICE(f"Deleting PDF: {pdf_path}"))
                        os.remove(pdf_path)
                    pdf_doc.delete()
                    report.legacy_pdf = None

                report.save()

            self.stdout.write(self.style.SUCCESS(f"Successfully imported ID {folder_name}"))

        self.stdout.write(self.style.WARNING(f"Missing TripReport objects for: {missing_reports}"))

def update_node_path(tag, attribute, folder_id, assets_dir, collection):
    original_val = tag.get(attribute, '')
    if '_assets/' not in original_val:
        return

    filename = os.path.basename(original_val)
    full_img_path = os.path.join(assets_dir, filename)

    if os.path.exists(full_img_path):
        # Use our existing duplicate check logic
        title_search = f"Legacy_{folder_id}_{filename}"
        wagtail_img = Image.objects.filter(title=title_search, collection=collection).first()
        
        if wagtail_img:
            # Swap the old relative path for the real Wagtail URL
            tag[attribute] = wagtail_img.get_rendition('original').url