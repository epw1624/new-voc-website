from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .forms import TripForm, TripSignupForm
from .models import Meeting, Trip, TripSignup, TripSignupTypes
from .utils import is_signup_type_change_valid, signup_type_as_str, valid_signup_changes
from gear.forms import GearHourForm
from gear.models import CancelledGearHour, GearHour
from membership.models import Membership, Profile
from membership.utils import get_membership_type, member_search
from ubc_voc_website.decorators import Members
from ubc_voc_website.utils import is_exec, is_member

from collections import OrderedDict
import datetime
import json
import pytz
from types import SimpleNamespace
from weasyprint import HTML

User = get_user_model()

pacific_timezone = pytz.timezone("America/Vancouver")

def trips(request):
    trips = Trip.objects.filter(
        Q(published=True) & (
            Q(end_time__isnull=False, end_time__gt=timezone.now()) | 
            Q(end_time__isnull=True, start_time__gte=timezone.now())
        )
    ).only(
        "id", "name", "start_time", "end_time", "tags"
    ).order_by("start_time", "end_time", "name")
    trips_list = {}
    all_trip_tags = set()
    for trip in trips:
        month = trip.start_time.strftime("%B %Y")
        if month not in trips_list:
            trips_list[month] = []
        trips_list[month].append(trip)
        for tag in trip.tags.all():
            all_trip_tags.add(tag)
    trips_list = dict(sorted(trips_list.items(), key=lambda x: datetime.datetime.strptime(x[0], "%B %Y")))

    trips_calendar = []
    for trip in trips:
        if trip.status == Trip.TripStatus.CANCELLED:
            continue

        end_time = trip.end_time if trip.end_time else trip.start_time + datetime.timedelta(hours=1)

        # This is to avoid long term events like "Journal Submissions Open" from cluttering the calendar
        # Future improvement could be to create a new "Announcements" class for such events so they are not classified as trips
        # Also, create a better long term solution for "recurring" trips that happen once a week for several months
        duration = end_time - trip.start_time
        if duration > datetime.timedelta(days=7):
            continue

        trips_calendar.append({
            "id": trip.id,
            "title": trip.name,
            "start": trip.start_time.isoformat(),
            "end": end_time.isoformat(),
            "color": trip.tags.all()[0].colour if trip.tags.exists() else "#808080",
            "tags": [tag.name for tag in trip.tags.all()]
        })

    return render(request, "trips/trip_agenda.html", {
        "all_trip_tags": list(all_trip_tags),
        "trips_list": trips_list, 
        "trips_calendar": json.dumps(trips_calendar)
    })

def previous_trips(request):
    trips = Trip.objects.filter(
        Q(published=True) & (
            Q(end_time__isnull=False, end_time__lte=timezone.now()) |
            Q(end_time__isnull=True, start_time__lt=timezone.now())
        )
    ).order_by("-start_time")

    q = request.GET.get("q")
    if q:
        trips = trips.filter(Q(name__icontains=q) | Q(description__icontains=q))

    page = request.GET.get("page")
    paginator = Paginator(trips, 50)

    try:
        previous_trips_page = paginator.page(page)
    except PageNotAnInteger:
        previous_trips_page = paginator.page(1)
    except EmptyPage:
        previous_trips_page = paginator.page(paginator.num_pages)

    grouped_trips = OrderedDict()
    for trip in previous_trips_page.object_list:
        month_key = trip.start_time.strftime("%B %Y")
        if month_key not in grouped_trips:
            grouped_trips[month_key] = []
        grouped_trips[month_key].append(trip)

    return render(request, "trips/previous_trips.html", {
        "trips": grouped_trips,
        "page_obj": previous_trips_page,
        "q": q
    })

@Members
def trip_organizer_message(request):
    return render(request, "trips/trip_organizer_message.html")

@Members
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST, user=request.user)
        if form.is_valid():
            trip = form.save(user=request.user)
            action = request.POST.get("action")
            if action == "publish":
                trip.published = True
                trip.save()
            return redirect("trips")
    else:
        form = TripForm(user=request.user)
    return render(request, "trips/trip_form.html", {"form": form})

@Members
def trip_edit(request, id):
    trip = get_object_or_404(Trip, id=id)
    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    else:
        if request.method == "POST":
            form = TripForm(request.POST, instance=trip, user=request.user)
            if form.is_valid():
                action = request.POST.get("action")
                trip = form.save(commit=True, user=request.user)

                if action == "publish":
                    trip.published = True
                    trip.save()

                return redirect("trips")
        else:
            form = TripForm(instance=trip, user=request.user)
        return render(request, "trips/trip_form.html", {
            "form": form,
            "published": trip.published
        })
    
@Members
def trip_delete(request, id):
    trip = get_object_or_404(Trip, id=id)

    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    else:
        trip.delete()
        return redirect("trips")

def trip_details(request, id):
    trip = get_object_or_404(Trip, id=id)

    try:
        description = json.loads(trip.description).get("html", "")
    except json.JSONDecodeError:
        description = trip.description

    organizers = Profile.objects.filter(user__in=trip.organizers.all()).values(
            "user__id", "first_name", "last_name"
        )

    if request.user.is_authenticated and is_member(request.user):
        if trip.use_signup:
            def construct_signup_list(signups):
                """
                Returns a list of signups correctly formatted for the template
                """
                signup_list = []
                emails = []
                car_spots = 0
                for signup in signups:
                    signup_list.append({
                        "id": signup.user.id,
                        "name": signup.user.profile.full_name_with_pronouns,
                        "email": signup.user.email,
                        "signup_answer": signup.signup_answer,
                        "car_spots": signup.car_spots if signup.can_drive else 0
                    })
                    emails.append(signup.user.email)
                    if signup.can_drive:
                        car_spots += signup.car_spots
                return signup_list, emails, car_spots
            signups = TripSignup.objects.filter(trip=trip).select_related("user__profile").order_by("signup_time")

            interested_list, interested_emails, interested_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.INTERESTED))
            committed_list, committed_emails, committed_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.COMMITTED))
            going_list, going_emails, going_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.GOING))

            no_longer_interested_list, _, no_longer_interested_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.NO_LONGER_INTERESTED))
            bailed_from_committed_list, _, bailed_from_committed_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.BAILED_FROM_COMMITTED))
            no_longer_going_list, _, no_longer_going_car_spots = construct_signup_list(signups.filter(type=TripSignupTypes.NO_LONGER_GOING))

            # Create signup form for user
            user_can_signup = trip.use_signup and get_membership_type(request.user) != Membership.MembershipType.INACTIVE_HONOURARY
            if user_can_signup:
                signup = TripSignup.objects.filter(user=request.user, trip=trip).first() if user_can_signup else None
                form = TripSignupForm(user=request.user, trip=trip, instance=signup)
                valid_type_changes = valid_signup_changes(signup.type, trip.valid_signup_types) if signup else []
                valid_type_changes = [{"type": type, "name": signup_type_as_str(type)} for type in valid_type_changes]

            return render(request, "trips/trip.html", {
                "trip": trip, 
                "organizers": organizers,
                "description": description,
                "signups": SimpleNamespace(
                    interested=interested_list,
                    committed=committed_list,
                    going=going_list,
                    no_longer_interested=no_longer_interested_list,
                    bailed_from_committed=bailed_from_committed_list,
                    no_longer_going=no_longer_going_list,
                ),
                "signup_emails": SimpleNamespace(
                    interested=interested_emails,
                    committed=committed_emails,
                    going=going_emails
                ),
                "user_can_signup": user_can_signup,
                "user_signup": signup,
                "valid_type_changes": valid_type_changes,
                "form": form,
                "car_spots": SimpleNamespace(
                    interested=interested_car_spots,
                    committed=committed_car_spots,
                    going=going_car_spots,
                    no_longer_interested = no_longer_interested_car_spots,
                    bailed_from_committed=bailed_from_committed_car_spots,
                    no_longer_going=no_longer_going_car_spots,
                ) if trip.drivers_required else None,
            })
    else:
        trip.members_only_info = None

    return render(request, "trips/trip.html", {
        "trip": trip,
        "organizers": organizers,
        "description": description,
    })
    
@Members
def trip_signup(request, trip_id):
    if request.method == "POST":
        trip = get_object_or_404(Trip, id=trip_id)
        if get_membership_type(request.user) != Membership.MembershipType.INACTIVE_HONOURARY:
            existing_signup = TripSignup.objects.filter(user=request.user, trip=trip).first()
            form = TripSignupForm(request.POST, user=request.user, trip=trip, instance=existing_signup)
            if form.is_valid():
                form.save()
        
    return redirect("trip_details", id=trip_id)
    
@Members
def change_signup_type(request, signup_id, new_type):
    signup = get_object_or_404(TripSignup, id=signup_id)
    trip = signup.trip
    if signup.user != request.user or not is_signup_type_change_valid(signup.type, new_type, trip.valid_signup_types):
        return render(request, "access_denied.html", status=403)
    else:
        signup.type = new_type
        signup.signup_time = timezone.now()
        signup.save()

    return redirect(f"/trips/details/{trip.id}")

@Members
def mark_as_going(request, trip_id, user_id):
    user = get_object_or_404(User, id=user_id)
    trip = get_object_or_404(Trip, id=trip_id)

    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    else:
        # edit existing signup to going if it exists, else create a new one
        trip_signup, created = TripSignup.objects.get_or_create(
            trip=trip,
            user=user,
        )
        trip_signup.type = TripSignupTypes.GOING
        trip_signup.signup_time = timezone.now()
        trip_signup.save()

        return redirect(f"/trips/details/{trip_id}")
    
@Members
def going_list_search(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    
    going_list = TripSignup.objects.filter(
        trip=trip,
        type=TripSignupTypes.GOING
    ).values_list("user_id", flat=True)

    q = request.GET.get("q")
    profiles = member_search(q)
    profiles = profiles.exclude(user_id__in=Subquery(going_list)).distinct()

    results = [{"id": profile.user.id, "full_name": f"{profile.first_name} {profile.last_name}"} for profile in profiles]
    return JsonResponse(results, safe=False)
    
@Members
def bulk_mark_going(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    
    if request.method == "POST":
        user_ids = request.POST.getlist("user_ids")
        user_ids = [id for id in user_ids if id and id.isdigit()]
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
            for user in users:
                trip_signup, created = TripSignup.objects.get_or_create(
                    trip=trip,
                    user=user
                )
                trip_signup.type = TripSignupTypes.GOING
                trip_signup.signup_time = timezone.now()
                trip_signup.save()

    return redirect(f"/trips/details/{trip_id}")
    
@Members
def remove_from_going(request, trip_id, user_id):
    user = get_object_or_404(User, id=user_id)
    trip = get_object_or_404(Trip, id=trip_id)

    if not trip.organizers.filter(pk=request.user.pk).exists():
        return render(request, "access_denied.html", status=403)
    else:
        trip_signup = get_object_or_404(TripSignup, user=user, trip=trip)
        trip_signup.type = TripSignupTypes.NO_LONGER_GOING
        trip_signup.signup_time = timezone.now()
        trip_signup.save()
        return redirect(f"/trips/details/{trip_id}")
    
@Members
def download_participant_list(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if request.user not in trip.organizers.all() and not is_exec(request.user):
        return redirect(f"/trips/details/{trip_id}")

    if trip.use_signup:
        participants = TripSignup.objects.filter(
            trip=trip, type=TripSignupTypes.GOING,
        ).exclude(
            user__in=trip.organizers.all()
        ).select_related(
            "user", "user__profile"
        ).order_by("user__profile__first_name", "user__profile__last_name")

        organizers = trip.organizers.all().select_related("profile").order_by("profile__first_name", "profile__last_name")

        html_content = render_to_string("trips/participant_list.html", {
            "trip": trip,
            "organizers": organizers,
            "participants": participants,
            "headcount": len(organizers) + len(participants),
            "now": timezone.now()
        })

        base_url = request.build_absolute_uri("/")
        pdf_file = HTML(string=html_content, base_url=base_url).write_pdf()

        response = HttpResponse(pdf_file, content_type="application/pdf")
        filename = f"{trip.name.replace(' ', '_')}_participants.pdf"
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    return redirect(f"/trips/details/{trip_id}")

def clubroom_calendar(request):
    if request.POST:
        if "delete" in request.POST:
            gear_hour_id = request.POST.get("gear-hour-id")
            delete_all = request.POST.get("delete-all") == "true"
            gear_hour = get_object_or_404(GearHour, id=gear_hour_id)

            if delete_all:
                gear_hour.delete()
            else:
                date_str = request.POST.get("date")
                dt = parse_datetime(date_str).astimezone(pytz.timezone("America/Vancouver"))
                CancelledGearHour.objects.create(
                    gear_hour = gear_hour,
                    date = dt.date()
                )
            return redirect("clubroom_calendar")
        else:
            form = GearHourForm(request.POST, user=request.user)
            if form.is_valid():
                form.save()
            return redirect("clubroom_calendar")
    else:
        events_calendar = []

        upcoming_clubroom_events = Trip.objects.filter(in_clubroom=True).exclude(
            status=Trip.TripStatus.CANCELLED
        ).values(
            "id", "name", "start_time", "end_time"
        )
        for event in upcoming_clubroom_events:
            # This is to avoid long term events like "Journal Submissions Open" from cluttering the calendar
            # Future improvement could be to create a new "Announcements" class for such events so they are not classified as trips
            # Also, create a better long term solution for "recurring" trips that happen once a week for several months
            end_time = event["end_time"] if event["end_time"] else event["start_time"] + datetime.timedelta(hours=1)
            duration = end_time - event["start_time"]
            if duration > datetime.timedelta(days=7):
                continue

            events_calendar.append({
                "id": event["id"],
                "title": event["name"],
                "start": event["start_time"].isoformat(),
                "end": event["end_time"].isoformat(),
                "color": "#0000FF",
                "type": "trip"
            })

        upcoming_clubroom_pretrips = Trip.objects.filter(use_pretrip=True, pretrip_location="VOC Clubroom").values(
            "id", "name", "pretrip_time"
        )
        for pretrip in upcoming_clubroom_pretrips:
            end_time = pretrip["pretrip_time"] + datetime.timedelta(hours=1)

            events_calendar.append({
                "id": pretrip["id"], # passing in the trip ID, so clicking the pretrip calendar event will link to trip details page
                "title": f"Pretrip Meeting - {pretrip['name']}",
                "start": pretrip["pretrip_time"].isoformat(),
                "end": end_time.isoformat(),
                "color": "#00FF00",
                "type": "pretrip"
            })

        meetings = Meeting.objects.filter(end_date__gte=timezone.localdate())
        for meeting in meetings:
            date = meeting.start_date
            while date <= meeting.end_date:
                start_datetime = datetime.datetime.combine(date, meeting.start_time)
                start_datetime = pacific_timezone.localize(start_datetime)
                end_datetime = start_datetime + datetime.timedelta(minutes=meeting.duration)
                events_calendar.append({
                    "title": meeting.name,
                    "start": start_datetime.isoformat(),
                    "end": end_datetime.isoformat(),
                    "color": "#FF0000",
                    "type": "meeting"
                })
                date += datetime.timedelta(days=7)

        gear_hours = GearHour.objects.filter(end_date__gte=timezone.localdate())
        cancelled_gear_hours = CancelledGearHour.objects.filter(gear_hour__in=gear_hours)

        for gear_hour in gear_hours:
            qm_name = Profile.objects.get(user=gear_hour.qm).first_name

            date = gear_hour.start_date
            while date <= gear_hour.end_date:
                if not cancelled_gear_hours.filter(gear_hour=gear_hour, date=date).exists():
                    start_datetime = datetime.datetime.combine(date, gear_hour.start_time)
                    start_datetime = pacific_timezone.localize(start_datetime)
                    end_datetime = start_datetime + datetime.timedelta(minutes=gear_hour.duration)

                    events_calendar.append({
                        "id": f"{gear_hour.id}:{date.isoformat()}",
                        "title": f"Gear Hours - {qm_name}",
                        "start": start_datetime.isoformat(),
                        "end": end_datetime.isoformat(),
                        "type": "gear_hour"
                    })
                date = date + datetime.timedelta(days=7)

        form = None
        if request.user.is_authenticated and is_exec(request.user):
            form = GearHourForm(user=request.user)

        return render(request, "trips/clubroom_calendar.html", {
            "trips_calendar": json.dumps(events_calendar),
            "form": form
        })


