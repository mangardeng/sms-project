from django.contrib import admin

from .models import (
    AcademicYear,
    SchoolClass,
    Stream,
    TimeSlot,
    TimetableEntry
)


admin.site.register(AcademicYear)
admin.site.register(SchoolClass)
admin.site.register(Stream)
admin.site.register(TimeSlot)
admin.site.register(TimetableEntry)