from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .decorators import Members
from photologue.models import Gallery, Photo
from wagtail.images.models import Image

PHOTO_CONTEST_ALBUM = "photo-contest-2025"

def home(request):
    try:
        gallery = Gallery.objects.filter(slug="homepage").first()
        gallery_photos = gallery.public() if gallery else []
        about_photo = Photo.objects.get(slug="about")
        join_photo = Photo.objects.get(slug="join")
        trips_photo = Photo.objects.get(slug="trips")
        huts_photo = Photo.objects.get(slug="huts")
    except Exception:
        gallery_photos = None
        about_photo = None
        join_photo = None
        trips_photo = None
        huts_photo = None

    return render(request, "home.html", {
        "photos": gallery_photos,
        "about": about_photo,
        "join": join_photo,
        "trips": trips_photo,
        "huts": huts_photo
    })

def about(request):
    return render(request, "about.html")

def how_to_join(request):
    return render(request, "how_to_join.html")

def membership_handbook(request):
    return render(request, "membership_handbook.html")

@csrf_exempt
@Members
def quill_image_upload(request):
    MAX_FILE_SIZE = 2097152

    if request.method == "POST" and request.FILES.get("image"):
        image_file = request.FILES["image"]

        if image_file.size > MAX_FILE_SIZE:
            return JsonResponse({
                "error": "File too large. Please keep images under 2MB"
            }, status=400)

        image = Image(
            title=image_file.name,
            file=image_file,
            collection_id=2,
            uploaded_by_user=request.user
        )
        image.save()
        rendition = image.get_rendition("width-1000")
        return JsonResponse({"url": rendition.url})
    return JsonResponse({"error": "Failed to upload image"}, status=403)