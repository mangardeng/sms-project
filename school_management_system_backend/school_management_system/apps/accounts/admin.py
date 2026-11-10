from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_active", "is_locked", "date_joined")
    list_filter = ("role", "is_active", "is_locked")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role & Security", {"fields": ("role", "phone_number", "must_change_password", "failed_login_attempts", "is_locked")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role", "phone_number")}),
    )
