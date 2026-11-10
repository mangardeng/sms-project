from django.contrib import admin

from apps.examinations.models import (
    ExamMarkAuditLog,
    Examination,
    ExaminationResult,
    ExaminationType,
    GradeBoundary,
    SubjectTermResult,
    TermSummary,
)


@admin.register(ExaminationType)
class ExaminationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "weight_percentage")


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ("name", "school_class", "subject", "term", "date", "is_published", "marks_locked")
    list_filter = ("is_published", "marks_locked", "term")


@admin.register(ExaminationResult)
class ExaminationResultAdmin(admin.ModelAdmin):
    list_display = ("student", "examination", "marks_obtained", "grade")
    search_fields = ("student__index_number",)


@admin.register(ExamMarkAuditLog)
class ExamMarkAuditLogAdmin(admin.ModelAdmin):
    list_display = ("result", "old_marks", "new_marks", "changed_by", "changed_at")
    readonly_fields = [f.name for f in ExamMarkAuditLog._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(GradeBoundary)
class GradeBoundaryAdmin(admin.ModelAdmin):
    list_display = ("grade", "min_percentage", "remark")


@admin.register(SubjectTermResult)
class SubjectTermResultAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "term", "midterm_percentage", "endterm_percentage", "final_percentage", "grade", "position", "is_complete")
    list_filter = ("term", "school_class", "is_complete", "is_published")
    search_fields = ("student__index_number",)


@admin.register(TermSummary)
class TermSummaryAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "school_class", "average_percentage", "grade", "position", "class_size", "is_complete")
    list_filter = ("term", "school_class", "is_complete", "is_published")
    search_fields = ("student__index_number",)
