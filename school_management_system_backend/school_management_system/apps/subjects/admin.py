from django.contrib import admin

from apps.subjects.models import ClassSubject, Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_compulsory")


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ("school_class", "subject", "teacher", "academic_year")
    list_filter = ("academic_year", "school_class")
