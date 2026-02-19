from django.urls import path
from .views import *

urlpatterns = [ 
    path("join/", join, name="join"),
    path("join-complete", join_complete, name="join_complete"),
    path("waiver/<int:membership_id>/", waiver, name="waiver"),
    path("members/", member_list, name="members"),
    path("profile/<int:id>/", profile, name="profile"),
    path("edit-profile/", edit_profile, name="edit_profile"),
    path("view-waiver/<int:id>/", view_waiver, name="view_waiver"),
    path("manage-memberships/", manage_memberships, name="manage_memberships"),
    path("memberships/<int:id>/", get_memberships_for_user, name="get_memberships_for_user"),
    path("toggle/<int:membership_id>/", toggle_membership, name="toggle_membership"),
    path("membership-stats/", membership_stats, name="membership_stats"),
    path("download-member-table/<str:type>/", download_member_table, name="download_member_table"),
    path("proof-of-membership/", proof_of_membership, name="proof_of_membership")
]