from django.db import models
from .storage import LegacyGalleryStorage

class GalleryPhoto(models.Model):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(max_length=1024, blank=True, null=True)
    album = models.CharField(max_length=255, db_index=True, blank=True, null=True)
    image = models.ImageField(storage=LegacyGalleryStorage())

    def __str__(self):
        return self.title or f"Photo: {self.id}"
