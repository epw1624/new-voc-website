from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import render

from .models import GalleryPhoto
from .storage import LegacyGalleryStorage

def gallery_album_index_page(request):
    albums = GalleryPhoto.objects.values("album").annotate(
        photo_count=Count("id")
    ).order_by("album")

    album_cover_images = GalleryPhoto.objects.filter(
        album=OuterRef("album")
    ).values("image")[:1]

    albums = list(albums.annotate(cover_image=Subquery(album_cover_images)))

    storage = LegacyGalleryStorage()

    for album in albums:
        if album["cover_image"]:
            album["cover_url"] = storage.url(album["cover_image"])
        else:
            album["cover_url"] = None

    return render(request, "gallery/album_index_page.html", {"albums": albums})

def gallery_album(request, album):
    photos = GalleryPhoto.objects.filter(album=album).order_by('id')
    
    return render(request, 'gallery/album.html', {
        'album': album,
        'photos': photos
    })
