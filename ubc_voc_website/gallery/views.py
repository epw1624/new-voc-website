from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import render

from urllib.parse import unquote

from .models import GalleryPhoto
from .storage import LegacyGalleryStorage

def gallery_album_index_page(request):
    query = request.GET.get("q")

    albums = GalleryPhoto.objects.values("album").annotate(
        photo_count=Count("id")
    ).order_by("album")

    if query:
        albums = albums.filter(album__icontains=query)

    album_cover_images = GalleryPhoto.objects.filter(
        album=OuterRef("album")
    ).values("image")[:1]

    albums = albums.annotate(cover_image=Subquery(album_cover_images))

    paginator = Paginator(albums, 25) 
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    albums = list(page_obj.object_list)

    storage = LegacyGalleryStorage()

    for album in albums:
        if album["cover_image"]:
            album["cover_url"] = storage.url(album["cover_image"])
        else:
            album["cover_url"] = None

    return render(request, "gallery/album_index_page.html", {
        "albums": albums,
        "page_obj": page_obj
    })

def gallery_album(request, album):
    album = unquote(album)
    photos = GalleryPhoto.objects.filter(album=album).order_by('id')
    return render(request, 'gallery/album.html', {
        'album': album,
        'photos': photos
    })
