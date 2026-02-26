from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date

from .models import Membership, Profile

def get_end_date(today):
    """
    Evaluates the custom VOC membership end date logic
    
    If today is between Jan 1 and Apr 30 inclusive, return Sept 30 of the current year
    Otherwise return Sept 30 of the following year
    """
    current_year = today.year
    
    if date(current_year, 1, 1) <= today <= date(current_year, 4, 30):
        return date(current_year, 9, 30)
    
    else:
        return date(current_year + 1, 9, 30)

def is_minor(today, birthdate):
    """
    Determine whether a user is a minor based on their birthdate. This is required to determine 
    whether they are eligible to sign their own waiver or if a parent/guardian must sign on
    their behalf

    Returns True if the user is under 19 years of age
    Returns False if the user is 19 years of age or older
    """
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age < 19

def get_membership_type(user):
    """
    Given a user, return the Membership.MembershipType of their current, active membership
    If the user does not exist, or exists but is not a member return None
    """
    if not user or not user.is_authenticated:
        return None
    else:
        membership = Membership.objects.filter(
            user=user,
            end_date__gte=timezone.localdate(),
            active=True
        ).order_by('-end_date').first()

        if membership:
            return membership.type
        return None
    
def send_honorary_member_request_email(request):
    context = {
        "full_name": request.user.get_full_name(),
        "email": request.user.email,
        "admin_url": (
            f"{request.build_absolute_uri('/membership/manage-memberships')}?id={request.user.id}"
        ),
    }

    subject = "Honorary Membership Request Requires Review"

    text_body = render_to_string(
        "membership/emails/honorary_membership_request.txt",
        context
    )
    html_body = render_to_string(
        "membership/emails/honorary_membership_request.html",
        context
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["membership@ubc-voc.com"]
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

def member_search(q):
    if len(q) < 2:
        return Profile.objects.none()
    
    today = timezone.localdate()

    return Profile.objects.filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(user__email__icontains=q)
    ).filter(
        user__membership__active=True,
        user__membership__end_date__gte=today
    ).select_related("user").only(
        "user__id", "user__email", "first_name", "last_name"
    )
