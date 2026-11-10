from django.contrib import admin

from apps.teachers.models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("staff_id", "user", "gender", "is_active_staff")
    search_fields = ("staff_id", "user__first_name", "user__last_name")
