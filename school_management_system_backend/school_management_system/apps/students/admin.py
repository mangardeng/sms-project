from django.contrib import admin

from apps.students.models import Student, StudentTransferHistory


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("index_number", "user", "school_class", "stream", "status")
    list_filter = ("status", "school_class")
    search_fields = ("index_number", "user__first_name", "user__last_name")


@admin.register(StudentTransferHistory)
class StudentTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "from_class", "to_class", "created_at")
