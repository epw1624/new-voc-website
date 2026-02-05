from django import forms
from django.utils import timezone
from membership.models import Profile
from .models import CancelledGearHour, GearHour, Rental, RentalTypes

from django.contrib.auth import get_user_model

import datetime
import pytz

User = get_user_model()

class GearHourForm(forms.ModelForm):
    class Meta:
        model = GearHour
        fields = (
            'start_date',
            'end_date',
            'start_time',
            'duration'
        )

    def __init__(self, *args, gear_hour=None, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.gear_hour = gear_hour

        now = timezone.now().astimezone(pytz.timezone("America/Vancouver"))
        self.fields["start_date"].initial = now.date()
        self.fields["start_time"].initial = now.strftime('%I:%M %p')

    def save(self, commit=True):
        gear_hour = super().save(commit=False)
        if self.user:
            gear_hour.qm = self.user

        if commit:
            gear_hour.save()

        return gear_hour

    start_date = forms.DateField(
        required=True,
        initial=timezone.localdate(),
        widget=forms.TextInput(attrs={'class': 'flatpickr-date'}),
        label="Date (recurring weekly)"
    )
    end_date = forms.DateField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'flatpickr-date'}),
        label="Date of last recurrence"
    )
    start_time = forms.TimeField(
        required=True,
        initial=timezone.now().strftime('%I:%M %p'),
        input_formats=['%I:%M %p'],
        widget=forms.TextInput(attrs={'class': 'flatpickr-timeonly'})
    )
    duration = forms.IntegerField(
        required=True,
        initial=60
    )


class CancelledGearHourForm(forms.ModelForm):
    class Meta:
        model = CancelledGearHour
        fields = (
            'gear_hour',
            'date'
        )
    gear_hour = forms.ModelChoiceField(
        queryset=GearHour.objects.all(),
        label="Gear Hour",
        widget=forms.Select,
        required=True
    )
    date = forms.DateField(
        required=True
    )

class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = (
            "type",
            "member",
            "deposit",
            "start_date",
            "due_date",
            "what",
            "notes"
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].label_from_instance = self.get_profile_label

    @staticmethod
    def get_profile_label(user):
        try:
            return user.profile.full_name
        except Profile.DoesNotExist:
            return user.email
        
    type = forms.ChoiceField(
        choices=RentalTypes.choices,
        widget=forms.RadioSelect,
        required=True,
        initial=RentalTypes.GEAR,
        label="Rental Type"
    )

    member = forms.ModelChoiceField(
        queryset=User.objects.filter(membership__active=True).distinct().exclude(membership__type__in=["H", "I"]), # Exclude both types of honorary members
        label="Member Name",
        widget=forms.Select(attrs={"id": "member-select"}),
        required=True
    )
    deposit = forms.IntegerField()
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.localdate()
    )
    due_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.localdate() + datetime.timedelta(days=7)
    )
    what = forms.CharField(
        required=True,
        label="What is being rented"
    )
    notes = forms.CharField(
        required=False
    )
