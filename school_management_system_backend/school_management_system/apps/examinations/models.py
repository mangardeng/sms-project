from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class ExaminationType(TimeStampedModel):
    """E.g. 'Midterm', 'End of Term', 'Mock Exam'."""

    class Category(models.TextChoices):
        MIDTERM = "midterm", "Midterm"
        END_TERM = "end_term", "End of term"
        OTHER = "other", "Other (not counted in term results)"

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
        help_text="Midterm and End of term examinations are combined automatically into the term result.",
    )
    default_max_marks = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("100.00"),
        help_text='What exams of this type are marked "out of" unless set otherwise (Midterm 40, End of term 60).',
    )
    weight_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("100.00"),
        help_text="No longer used: marks are now simply added together.",
    )

    def __str__(self):
        return self.name

    @staticmethod
    def guess_category(name):
        """'Mid Term', 'Midterm Exam' -> midterm; 'End of Term', 'Final Exam' -> end_term; otherwise other."""
        lowered = (name or "").lower()
        if "mid" in lowered:
            return ExaminationType.Category.MIDTERM
        if "end" in lowered or "final" in lowered:
            return ExaminationType.Category.END_TERM
        return ExaminationType.Category.OTHER

    def save(self, *args, **kwargs):
        # A type that was never given a "Counts as" value (e.g. created in the admin site) is worked
        # out from its name, so "End of Term" is not silently left out of the term results.
        if self.category == self.Category.OTHER:
            self.category = self.guess_category(self.name)
            if kwargs.get("update_fields") is not None and "category" not in kwargs["update_fields"]:
                kwargs["update_fields"] = [*kwargs["update_fields"], "category"]
        if self._state.adding and self.default_max_marks == Decimal("100.00"):
            # School convention: midterm out of 40 + end of term out of 60 = 100.
            if self.category == self.Category.MIDTERM:
                self.default_max_marks = Decimal("40.00")
            elif self.category == self.Category.END_TERM:
                self.default_max_marks = Decimal("60.00")
        super().save(*args, **kwargs)


class Examination(TimeStampedModel):
    """A specific sitting of an exam for one subject in one class (3.10.8)."""

    name = models.CharField(max_length=150)
    examination_type = models.ForeignKey(ExaminationType, on_delete=models.PROTECT, related_name="examinations")
    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="examinations")
    subject = models.ForeignKey("subjects.Subject", on_delete=models.CASCADE, related_name="examinations")
    academic_year = models.ForeignKey("core.AcademicYear", on_delete=models.CASCADE, related_name="examinations")
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="examinations")
    date = models.DateField()
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("100.00"))
    is_published = models.BooleanField(
        default=False,
        help_text="Results are only visible to parents/students once published (3.10.8 'Publish results').",
    )
    marks_locked = models.BooleanField(
        default=False,
        help_text="Once locked (e.g. after approval), only an Administrator may edit marks.",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-date"]
        unique_together = ("school_class", "subject", "examination_type", "term")

    def __str__(self):
        return f"{self.name} - {self.subject.code} - {self.school_class}"


DEFAULT_GRADE_SCALE = [
    (Decimal("80"), "A", "Excellent"),
    (Decimal("70"), "B", "Very Good"),
    (Decimal("60"), "C", "Good"),
    (Decimal("50"), "D", "Satisfactory"),
    (Decimal("40"), "E", "Pass"),
    (Decimal("0"), "F", "Fail"),
]


class GradeBoundary(TimeStampedModel):
    """
    One row of the school's grading scale, e.g. 80% and above = A (Excellent).
    Administrators can edit these; every grade in the system follows them.
    """

    grade = models.CharField(max_length=2, unique=True)
    min_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, unique=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Lowest percentage that earns this grade.",
    )
    remark = models.CharField(max_length=50, blank=True, help_text="e.g. Excellent, Good, Fail")

    class Meta:
        ordering = ["-min_percentage"]

    def __str__(self):
        return f"{self.grade} (from {self.min_percentage}%)"


def get_grade_scale():
    """Returns [(min_percentage, grade, remark), ...] highest first. Falls back to the default scale."""
    rows = list(GradeBoundary.objects.order_by("-min_percentage").values_list("min_percentage", "grade", "remark"))
    return rows or DEFAULT_GRADE_SCALE


def grade_and_remark(percentage, scale=None):
    """Returns (grade, remark) for a percentage using the configured scale."""
    scale = scale or get_grade_scale()
    percentage = Decimal(str(percentage))
    for minimum, grade, remark in scale:
        if percentage >= minimum:
            return grade, remark
    return scale[-1][1], scale[-1][2]  # below the lowest boundary -> lowest grade


def grade_for_percentage(percentage, scale=None) -> str:
    return grade_and_remark(percentage, scale)[0]


class ExaminationResult(TimeStampedModel):
    """A student's marks for one Examination."""

    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="examination_results")
    marks_obtained = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    grade = models.CharField(max_length=2, blank=True)
    remarks = models.CharField(max_length=255, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        unique_together = ("examination", "student")
        ordering = ["-marks_obtained"]

    def __str__(self):
        return f"{self.student.index_number} | {self.examination} | {self.marks_obtained}"

    def save(self, *args, **kwargs):
        if self.examination.max_marks:
            percentage = (Decimal(self.marks_obtained) / Decimal(self.examination.max_marks)) * 100
            self.grade = grade_for_percentage(percentage)
        super().save(*args, **kwargs)


class ExamMarkAuditLog(models.Model):
    """
    Dedicated audit trail for examination-mark changes, explicitly
    required by design doc 3.10.8: "The system should maintain an
    audit trail for changes to examination marks."
    """

    result = models.ForeignKey(ExaminationResult, on_delete=models.CASCADE, related_name="audit_trail")
    old_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    new_marks = models.DecimalField(max_digits=6, decimal_places=2)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.result} : {self.old_marks} -> {self.new_marks}"


class SubjectTermResult(TimeStampedModel):
    """
    A student's combined result for ONE subject in ONE term, computed automatically
    from the Midterm and End-of-term examination marks (see services.py).
    Never entered by hand.
    """

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="subject_term_results")
    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="subject_term_results")
    subject = models.ForeignKey("subjects.Subject", on_delete=models.CASCADE, related_name="term_results")
    academic_year = models.ForeignKey("core.AcademicYear", on_delete=models.CASCADE, related_name="+")
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="subject_term_results")

    midterm_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    endterm_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Points each exam contributes, e.g. 36 out of 40 (midterm) + 56 out of 60 (end of term) = 92.
    midterm_points = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    midterm_out_of = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    endterm_points = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    endterm_out_of = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    final_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    remark = models.CharField(max_length=50, blank=True)
    teacher_remark = models.CharField(
        max_length=255, blank=True,
        help_text="Optional remark typed by the subject teacher. When set it replaces the automatic remark.",
    )
    position = models.PositiveIntegerField(null=True, blank=True, help_text="Rank in the class for this subject.")
    is_complete = models.BooleanField(default=False, help_text="True once every scheduled exam has marks for this student.")
    is_published = models.BooleanField(default=False, help_text="True once every exam behind this result is published.")

    class Meta:
        unique_together = ("student", "subject", "term")
        ordering = ["school_class__level", "subject__name", "position"]

    def __str__(self):
        return f"{self.student.index_number} | {self.subject.code} | {self.term} | {self.final_percentage}% {self.grade}"


class TermSummary(TimeStampedModel):
    """A student's overall result for a term across all subjects, with class position."""

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="term_summaries")
    school_class = models.ForeignKey("classes.SchoolClass", on_delete=models.CASCADE, related_name="term_summaries")
    academic_year = models.ForeignKey("core.AcademicYear", on_delete=models.CASCADE, related_name="+")
    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="term_summaries")

    subjects_count = models.PositiveSmallIntegerField(default=0)
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    average_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    grade = models.CharField(max_length=2)
    remark = models.CharField(max_length=50, blank=True)
    position = models.PositiveIntegerField(null=True, blank=True)
    class_size = models.PositiveIntegerField(default=0, help_text="Students ranked in this class for the term.")
    is_complete = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "term")
        ordering = ["school_class__level", "position"]

    def __str__(self):
        return f"{self.student.index_number} | {self.term} | avg {self.average_percentage}% {self.grade}"
