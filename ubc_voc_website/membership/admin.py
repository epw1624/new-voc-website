from django.contrib import admin
from .models import Exec, FormerExec, Membership, Profile, PSG, Waiver

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user__email', 'start_date', 'end_date', 'type', 'active')
    search_fields = ('user__email',)
    list_filter = ('start_date', 'end_date')
    readonly_fields = ("user",)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'phone')
    search_fields = ('user__email', 'first_name', 'last_name')
    list_filter = ('first_name', 'last_name')

    formfield_overrides = {
        
    }

@admin.register(Exec)
class ExecAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'exec_role', 'priority')
    list_editable = ('priority',)
    autocomplete_fields = ('user',)
    search_fields = ('user__email', 'user__profile__first_name', 'user__profile__last_name', 'exec_role')
    ordering = ('priority', 'user__profile__first_name')

    def first_name(self, obj):
        return obj.user.profile.first_name

    def last_name(self, obj):
        return obj.user.profile.last_name
    
@admin.register(FormerExec)
class FormerExecAdmin(admin.ModelAdmin):
    list_display = ('user', 'exec_role', 'end_year')
    autocomplete_fields = ('user',)
    search_fields = ('user__email', 'user__profile__first_name', 'user__profile__last_name', 'exec_role', 'end_year')
    ordering = ('-end_year', 'user__profile__first_name', 'user__profile__last_name')

@admin.register(PSG)
class PSGAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name')
    autocomplete_fields = ('user',)
    search_fields = ('user__email', 'user__profile__first_name', 'user__profile__last_name')

    def first_name(self, obj):
        return obj.user.profile.first_name

    def last_name(self, obj):
        return obj.user.profile.last_name
    
@admin.register(Waiver)
class WaiverAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name')
    search_fields = ('membership__user__email', 'membership__user__profile__first_name', 'membership__user__profile__last_name')
    readonly_fields = ('membership',)

    def email(self, obj):
        return obj.membership.user.email
    
    def first_name(self, obj):
        return obj.membership.user.profile.first_name
    
    def last_name(self, obj):
        return obj.membership.user.profile.last_name