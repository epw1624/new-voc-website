from django.urls import path
from .views import *

urlpatterns = [
    path('', gallery_album_index_page, name="gallery_album_index_page"),
    path('album/<str:album>', gallery_album, name="gallery_album")
]