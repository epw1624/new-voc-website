from django.contrib import admin

from .models import GalleryPhoto

@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ("album", "title", "description")
    search_fields = ("album", "title")
    list_filter = ("album", "title")
    readonly_fields = ("album", "title", "description", "image")
