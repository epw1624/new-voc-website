"""
URL configuration for ubc_voc_website project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from .views import about, home, how_to_join, membership_handbook, quill_image_upload

from machina import urls as machina_urls

urlpatterns = [
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("gallery/", include("gallery.urls")),
    path("gear/", include("gear.urls")),
    path('how-to-join/', how_to_join, name="how_to_join"),
    path("membership/", include("membership.urls")),
    path("membership-handbook/", membership_handbook, name="membership_handbook"),
    path("message-board/", include(machina_urls)),
    path("photologue/", include("photologue.urls", namespace="photologue")),
    path("trips/", include("trips.urls")),
    path("trip-reports/", include("tripreports.urls")),
    path("upload/image/", quill_image_upload, name="quill_image_upload"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
