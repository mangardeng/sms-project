from django.contrib import admin

from apps.parents.models import Parent, ParentStudent


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("user", "occupation")
    search_fields = ("user__first_name", "user__last_name")


@admin.register(ParentStudent)
class ParentStudentAdmin(admin.ModelAdmin):
    list_display = ("parent", "student", "relationship", "is_primary_contact")
    list_filter = ("relationship", "is_primary_contact")
