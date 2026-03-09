from django.contrib import admin
from .models import LawFirm, FirmMembership

@admin.register(LawFirm)
class LawFirmAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_verified', 'is_active']
    list_filter = ['is_verified', 'is_active', 'state']
    search_fields = ['name', 'registration_number']

@admin.register(FirmMembership)
class FirmMembershipAdmin(admin.ModelAdmin):
    list_display = ['firm', 'user', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active']
    search_fields = ['firm__name', 'user__email']