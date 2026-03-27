import os
import re
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction

from wagtail.models import Collection
from wagtail.images.models import Image
from tripreports.models import TripReport

class Command(BaseCommand):
    help = 'Imports legacy HTML and fixes dot-slash image paths'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Path to the renamed_archive folder')

    def handle(self, *args, **options):
        # Use absolute path to avoid Docker relative-path confusion
        base_dir = os.path.abspath(options['directory'])
        
        root_collection = Collection.get_first_root_node()
        
        collection = Collection.objects.filter(name="Legacy Imports").first()
        
        if not collection:
            self.stdout.write("Creating 'Legacy Imports' collection...")
            collection = root_collection.add_child(name="Legacy Imports")

        for folder_name in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            try:
                report = TripReport.objects.get(old_id=int(folder_name))
            except (TripReport.DoesNotExist, ValueError):
                continue

            html_path = os.path.join(folder_path, "index.html")
            assets_dir = os.path.join(folder_path, "_assets")

            if not os.path.exists(html_path):
                continue

            self.stdout.write(f"Processing ID {folder_name}...")

            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            with transaction.atomic():
                # Fix images, links, and data-src
                tags_to_check = soup.find_all(['img', 'a'])
                for tag in tags_to_check:
                    attr = 'src' if tag.name == 'img' else 'href'
                    if tag.has_attr(attr):
                        self.update_node_path(tag, attr, folder_name, assets_dir, collection)

                # Save and clear body
                report.legacy_html = str(soup)
                report.body = ""
                
                # PDF deletion logic (keep if you're doing the treadmill approach)
                if report.legacy_pdf:
                    try:
                        pdf_path = report.legacy_pdf.file.path
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                        report.legacy_pdf.delete()
                        report.legacy_pdf = None
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"PDF delete failed: {e}"))

                report.save()

    def update_node_path(self, tag, attribute, folder_id, assets_dir, collection):
        original_val = str(tag.get(attribute, ''))
        
        # Strip leading dots and slashes to get just the filename
        # e.g., "./_assets/ext_60218602.jpg" -> "ext_60218602.jpg"
        filename = original_val.split('/')[-1]
        full_img_path = os.path.join(assets_dir, filename)

        if os.path.exists(full_img_path):
            title_search = f"Legacy_{folder_id}_{filename}"
            # Duplicate check
            wagtail_img = Image.objects.filter(title=title_search, collection=collection).first()
            
            if not wagtail_img:
                try:
                    with open(full_img_path, 'rb') as img_f:
                        wagtail_img = Image(
                            title=title_search,
                            file=File(img_f, name=filename),
                            collection=collection
                        )
                        wagtail_img.save()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Img Save Err: {filename} - {e}"))
                    return

            # Crucial: Get the actual URL from Wagtail
            tag[attribute] = wagtail_img.get_rendition('original').url