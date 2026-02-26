from django.urls import path
from .views import *

urlpatterns = [
    path('', trips, name="trips"),
    path('change-signup-type/<int:signup_id>/<int:new_type>', change_signup_type, name="change_signup_type"),
    path('clubroom-calendar/', clubroom_calendar, name="clubroom_calendar"),
    path('create/', trip_create, name="trip_create"),
    path('delete/<int:id>/', trip_delete, name="trip_delete"),
    path('details/<int:id>/', trip_details, name="trip_details"),
    path('download-participant-list/<int:trip_id>/', download_participant_list, name="download_participant_list"),
    path('edit/<int:id>/', trip_edit, name="trip_edit"),
    path('mark-going/<int:trip_id>/<int:user_id>/', mark_as_going, name="mark_as_going"),
    path('bulk-mark-going/<int:trip_id>', bulk_mark_going, name="bulk_mark_going"),
    path('remove-from-going/<int:trip_id>/<int:user_id>/', remove_from_going, name="remove_from_going"),
    path('previous/', previous_trips, name="previous_trips"),
    path('trip-organizer-message/', trip_organizer_message, name="trip_organizer_message"),
    path('trip-signup/<int:trip_id>/', trip_signup, name="trip_signup"),
]