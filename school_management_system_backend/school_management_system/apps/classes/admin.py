from django.contrib import admin

from apps.classes.models import SchoolClass, Stream


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "class_teacher", "is_active")
    list_filter = ("is_active",)


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ("school_class", "name", "capacity")
