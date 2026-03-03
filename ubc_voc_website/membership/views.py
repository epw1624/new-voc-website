from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .forms import MembershipForm, ProfileForm, WaiverForm
from .models import Exec, FormerExec, Membership, Profile, PSG, Waiver
from .utils import *
from tripreports.models import TripReport
from trips.models import Trip, TripSignup
from trips.utils import signup_type_as_str
from ubc_voc_website.decorators import Members, Execs
from ubc_voc_website.utils import is_exec, is_member

import base64
import datetime
from openpyxl import Workbook
import os
from weasyprint import CSS, HTML

User = get_user_model()

@login_required
def join(request):
    start_date = timezone.localdate()
    end_date = get_end_date(timezone.localdate())

    # If the user has an existing membership with the same end_date, redirect
    membership = Membership.objects.filter(user=request.user, end_date=end_date).first()
    if membership:
        if not hasattr(membership, "waiver"):
            return redirect("waiver", membership.id)
        else:
            return redirect("join_complete")

    if request.method == "POST":
        form = MembershipForm(request.POST, user=request.user)
        if form.is_valid():
            membership = form.save()
            if membership.type == Membership.MembershipType.INACTIVE_HONOURARY:
                # Inactive Honorary members don't need to sign the waiver
                send_honorary_member_request_email(request)
                return redirect("home")
                
            return redirect("waiver", membership.id)
    else:
        form = MembershipForm(user=request.user)

    return render(request, 'membership/join.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date    
    })

@login_required
def join_complete(request):
    membership = Membership.objects.filter(user=request.user, end_date=get_end_date(timezone.localdate())).first()
    return render(request, "membership/join_complete.html", { "active": membership.active })

@login_required
def edit_profile(request):
    user = request.user
    profile = Profile.objects.get(user=user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', profile.user.id)
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'membership/edit_profile.html', {'form': form})

@login_required
def waiver(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)

    if membership.user != request.user:
        return render(request, "access_denied.html", status=403)
    
    # Don't let someone sign the waiver twice for the same membership
    if hasattr(membership, "waiver"):
        return render(request, "access_denied.html", status=403)
    
    if request.method == "POST":
        form = WaiverForm(request.POST, user=request.user)

        if form.is_valid():
            waiver = form.save(commit=False)
            waiver.membership = membership

            signature_data = form.cleaned_data["signature"]
            f, imgstr = signature_data.split(";base64")
            data = ContentFile(base64.b64decode(imgstr))

            waiver.signature.save("signature.png", data, save=False)

            waiver.save()

            # If the waiver was for an Active Honorary membership, email the Membership Coordinator
            if membership.type == Membership.MembershipType.ACTIVE_HONORARY:
                send_honorary_member_request_email(request)

            return redirect("join_complete")
        
    else:
        form = WaiverForm(user=request.user)

    return render(request, "membership/waiver.html", {"form": form, "user_is_minor": is_minor(timezone.localdate(), request.user.profile.birthdate)})

@Members
def member_list(request):
    exec_queryset = Exec.objects.select_related('user', 'user__profile').order_by('priority', 'user__profile__first_name')
    execs = []
    for exec in exec_queryset:
        profile = exec.user.profile
        execs.append({
            'id': profile.user.id,
            'name': f'{profile.first_name} {profile.last_name}',
            'position': exec.exec_role,
            'email': profile.user.email,
            'phone': profile.phone
        })

    psg_queryset = PSG.objects.select_related('user', 'user__profile').order_by('user__profile__first_name')
    psg_members = []
    for psg in psg_queryset:
        profile = psg.user.profile
        psg_members.append({
            'id': profile.user.id,
            'name': f'{profile.first_name} {profile.last_name}',
            'email': profile.user.email,
            'phone': profile.phone
        })

    exec_user_ids = Exec.objects.values_list('user_id', flat=True)
    psg_user_ids = PSG.objects.values_list('user_id', flat=True)
    member_profiles = Profile.objects.all().exclude(user_id__in=exec_user_ids).exclude(user_id__in=psg_user_ids).filter(user__in=Membership.objects.filter(
            end_date__gte=timezone.localdate(),
            active=True
        ).values('user')).order_by('first_name', 'last_name')
    members = []
    for profile in member_profiles:
        members.append({
            'id': profile.user.id,
            'name': f'{profile.first_name} {profile.last_name}',
            'email': profile.user.email,
            'phone': profile.phone
        })

    return render(request, 'membership/members.html', {'execs': execs, 'psg_members': psg_members, 'members': members})

@login_required
def profile(request, id):
    user = get_object_or_404(User, id=id)
    if not is_member(request.user) and user != request.user: # Non-members can only view their own profile
        return render(request, 'access_denied.html', status=403)
    else:
        profile = Profile.objects.get(user=user)

        former_exec_roles = FormerExec.objects.filter(user=user).order_by("-end_year")

        organized_trips = Trip.objects.filter(organizers=user).order_by("start_time")
        if user != request.user:
            organized_trips = organized_trips.filter(published=True)

        organized_trips_list = {}
        for trip in organized_trips:
            month = trip.start_time.strftime('%B %Y')
            if month not in organized_trips_list:
                organized_trips_list[month] = []
            organized_trips_list[month].append(trip)
        organized_trips_list = dict(sorted(organized_trips_list.items(), key=lambda x: datetime.datetime.strptime(x[0], '%B %Y'), reverse=True))

        # signups = TripSignup.objects.filter(user=user).exclude(trip__organizers=user)
        signups = TripSignup.objects.filter(user=user).order_by("trip__start_time")
        attended_trips = [{'trip': signup.trip, 'type': signup_type_as_str(signup.type)} for signup in signups]
        attended_trips_list = {}
        for trip in attended_trips:
            month = trip["trip"].start_time.strftime('%B %Y')
            if month not in attended_trips_list:
                attended_trips_list[month] = []
            attended_trips_list[month].append(trip)
        attended_trips_list = dict(sorted(attended_trips_list.items(), key=lambda x: datetime.datetime.strptime(x[0], '%B %Y'), reverse=True))

        trip_reports = TripReport.objects.filter(owner=profile.user, live=True).order_by("-first_published_at")

        exec = Exec.objects.filter(user=user).first()
        exec_role = exec.exec_role if exec else None

        return render(request, 'membership/profile.html', {
            'user': user, 
            'profile': profile,
            'trips': {
                'organized': organized_trips_list,
                'attended': attended_trips_list
            },
            'trip_reports': trip_reports,
            'own_profile': user == request.user,
            'exec_role': exec_role,
            'former_exec_roles': former_exec_roles
        })

@Members
def view_waiver(request, id):
    membership = get_object_or_404(Membership.objects.select_related("user"), id=id)
    waiver = Waiver.objects.filter(membership=membership).first()
    if not waiver:
        messages.warning(request, "This membership has no associated waiver")
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return HttpResponseRedirect(referer)
        else:
            return redirect("manage_memberships")

    if membership.user != request.user and not is_exec(request.user):
        # custom access control - Execs can see all waivers but non-Execs can only see their own
        return render(request, 'access_denied.html', status=403)
    else:
        form = WaiverForm(user=membership.user, instance=waiver, readonly=True)
        html_content = render_to_string('membership/waiver_readonly.html', {'form': form, 'waiver': waiver, 'readonly': True})
        css_path = os.path.join(settings.STATIC_ROOT, "membership", "waiver.css")
        pdf = HTML(string=html_content, base_url=request.build_absolute_uri('/')).write_pdf(
            stylesheets=[CSS(css_path)]
        )

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="waiver.pdf"'
        return response


@Members
def proof_of_membership(request):
    membership = Membership.objects.filter(user=request.user).order_by("-end_date").first()
    if not membership:
        raise Http404("No membership found for user")

    profile = getattr(request.user, 'profile', None)

    context = {
        "membership": membership,
        "profile": profile,
        "user": request.user
    }

    html_content = render_to_string("membership/proof_of_membership.html", context)
    base_url = request.build_absolute_uri('/')
    pdf = HTML(string=html_content, base_url=base_url)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=proof_of_membership.pdf"
    response.write(pdf.write_pdf())
    return response

@Execs
def manage_memberships(request):
    q = request.GET.get("q")
    user_id = request.GET.get("id")

    profiles = Profile.objects.none()

    if q or user_id:
        base_query = Profile.objects.select_related("user")
        if user_id:
            profiles = base_query.filter(user__id=user_id)
        elif q:
            name_filter = Q()
            for term in q.strip().split():
                name_filter &= (
                    Q(first_name__icontains=term) |
                    Q(last_name__icontains=term)
                )

            profiles = (
                Profile.objects.select_related("user").filter(
                    name_filter |
                    Q(user__email__icontains=q)
                ).filter(
                    user__in=Membership.objects.all().values("user")
                )
            )

        profiles = profiles.order_by("first_name", "last_name")

        for profile in profiles:
            membership = Membership.objects.filter(
                user=profile.user,
            ).order_by(
                "-end_date"
            ).first()

            if membership.active and membership.end_date >= timezone.now().date():
                profile.membership_status = "Active"
            elif membership.active:
                profile.membership_status = "Expired"
            else:
                profile.membership_status = "Inactive"

    return render(request, "membership/manage_memberships.html", {
        "profiles": profiles,
        "query": q
    })

@Execs
def get_memberships_for_user(request, id):
    user = get_object_or_404(User, id=id)
    memberships = user.membership_set.order_by("-end_date")
    return render(request, "membership/partial/memberships_table.html", {
        "memberships": memberships,
        "q": request.GET.urlencode()
    })

@Execs
def toggle_membership(request, membership_id):
    membership = get_object_or_404(Membership.objects.select_related("user", "user__profile"), id=membership_id)

    membership.active = not membership.active
    membership.save()

    # Send welcome email for activated membership
    if membership.active:
        context = {
            "name": membership.user.profile.full_name,
            "end_date": membership.end_date,
            "site_url": settings.SITE_URL
        }
        text_body = render_to_string(
            "membership/emails/membership_activated.txt",
            context
        )
        html_body = render_to_string(
            "membership/emails/membership_activated.html",
            context
        )
        message = EmailMultiAlternatives(
            subject=f"Welcome to the VOC!",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[membership.user.email]
        )
        message.attach_alternative(html_body, "text/html")
        message.send()

    query_string = request.GET.urlencode()
    url = reverse("manage_memberships")
    if query_string:
        url = f"{url}?{query_string}"
    return redirect(url)

@Execs
def membership_stats(request):
    active_memberships = Membership.objects.filter(
        end_date__gte=timezone.localdate(),
        active=True
    )
    regular_memberships = active_memberships.filter(type=Membership.MembershipType.REGULAR)
    associate_memberships = active_memberships.filter(type=Membership.MembershipType.ASSOCIATE)
    active_honorary_memberships = active_memberships.filter(type=Membership.MembershipType.ACTIVE_HONORARY)
    inactive_honorary_memberships = active_memberships.filter(type=Membership.MembershipType.INACTIVE_HONOURARY)

    inactive_memberships = Membership.objects.filter(
        end_date__gte=timezone.localdate(),
        active=False
    )

    return render(request, 'membership/membership_stats.html', {
            'num_members': active_memberships.count(),
            'num_inactive_memberships': inactive_memberships.count(),
            'num_regular_members': regular_memberships.count(), 
            'num_associate_members': associate_memberships.count(), 
            'num_active_honorary_members': active_honorary_memberships.count(),
            'num_inactive_honorary_members': inactive_honorary_memberships.count()
        })
    
    # TODO add more stats that would be useful/interesting (trip signups, etc.)

@Execs
def download_member_table(request, type):
    if type == "acc":
        memberships = Membership.objects.filter(
            end_date__gte=timezone.localdate(),
            active=True,
            type=Membership.MembershipType.REGULAR
        )
        profiles = Profile.objects.filter(
            user__in=memberships.values_list('user', flat=True), 
            acc=True
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "ACC Membership Candidates"

        fields = ['First Name', 'Last Name', 'Email']
        ws.append(fields)

        for profile in profiles:
            row = [
                profile.first_name,
                profile.last_name,
                profile.user.email,
            ]
            ws.append(row)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="voc_acc_members.xlsx"'
        wb.save(response)
        return response
    
    elif type == "fmcbc":
        """
            This result is sent to the FMCBC for insurance, so we exclude inactive honorary members
        """
        memberships = Membership.objects.filter(
            end_date__gte=timezone.localdate(),
            active=True
        ).exclude(
            type=Membership.MembershipType.INACTIVE_HONOURARY
        )
        profiles = Profile.objects.filter(user__in=memberships.values_list('user', flat=True))

        wb = Workbook()
        ws = wb.active
        ws.title = "VOC Member List (for FMCBC)"

        fields = ['No.', 'First Name', 'Last Name', 'Email', 'Phone', 'Birthdate']
        ws.append(fields)

        i = 1
        for profile in profiles:
            row = [
                i,
                profile.first_name,
                profile.last_name,
                profile.user.email,
                profile.phone,
                profile.birthdate
            ]
            ws.append(row)
            i += 1

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="voc_members.xlsx"'
        wb.save(response)
        return response

    else:
        return Http404(f"Member list type {type} not found")

