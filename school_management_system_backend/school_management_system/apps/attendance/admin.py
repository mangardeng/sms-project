from django.contrib import admin

from apps.attendance.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "date", "status", "recorded_by")
    list_filter = ("status", "school_class", "date")
    search_fields = ("student__index_number",)
