from django.db import transaction
from rest_framework import serializers

from apps.students.models import Student
from apps.examinations.models import (
    ExamMarkAuditLog,
    Examination,
    ExaminationResult,
    ExaminationType,
    GradeBoundary,
    SubjectTermResult,
    TermSummary,
    get_grade_scale,
)
from apps.examinations.services import recompute_for_examination, suspend_auto_compute


class ExaminationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExaminationType
        fields = (
            "id",
            "name",
            "category",
            "default_max_marks",
        )


class ExaminationSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )

    school_class_name = serializers.CharField(
        source="school_class.name",
        read_only=True
    )

    examination_type_name = serializers.CharField(
        source="examination_type.name",
        read_only=True
    )

    examination_type_category = serializers.CharField(
        source="examination_type.category",
        read_only=True
    )

    class Meta:
        model = Examination
        fields = (
            "id",
            "name",
            "examination_type",
            "examination_type_name",
            "examination_type_category",
            "school_class",
            "school_class_name",
            "subject",
            "subject_name",
            "academic_year",
            "term",
            "date",
            "max_marks",
            "is_published",
            "marks_locked",
            "created_by",
        )

        read_only_fields = (
            "created_by",
        )

        extra_kwargs = {
            "max_marks": {
                "required": False,
                "help_text": "What the exam is marked out of. Leave blank to use the exam type's default (Midterm 40, End of term 60).",
            },
        }

    def validate(self, attrs):
        if attrs.get("max_marks") is None and not self.instance:
            exam_type = attrs.get("examination_type")
            attrs["max_marks"] = exam_type.default_max_marks if exam_type else 100
        return attrs


class ExamMarkAuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source="changed_by.get_full_name",
        read_only=True
    )

    class Meta:
        model = ExamMarkAuditLog
        fields = (
            "id",
            "old_marks",
            "new_marks",
            "changed_by",
            "changed_by_name",
            "changed_at",
            "reason",
        )


class ExaminationResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student.user.get_full_name",
        read_only=True
    )

    student_index_number = serializers.CharField(
        source="student.index_number",
        read_only=True
    )

    examination_name = serializers.CharField(
        source="examination.name",
        read_only=True
    )

    subject_name = serializers.CharField(
        source="examination.subject.name",
        read_only=True
    )

    max_marks = serializers.DecimalField(
        source="examination.max_marks",
        max_digits=6,
        decimal_places=2,
        read_only=True
    )

    percentage = serializers.SerializerMethodField()

    grade_remark = serializers.SerializerMethodField()

    class Meta:
        model = ExaminationResult

        fields = (
            "id",
            "examination",
            "examination_name",
            "subject_name",
            "max_marks",
            "student",
            "student_name",
            "student_index_number",
            "marks_obtained",
            "grade",
            "grade_remark",
            "percentage",
            "remarks",
            "entered_by",
        )

        read_only_fields = (
            "grade",
            "entered_by",
        )

    def validate(self, attrs):
        examination = attrs.get("examination") or getattr(self.instance, "examination", None)
        marks = attrs.get("marks_obtained")
        if examination is not None and marks is not None and marks > examination.max_marks:
            raise serializers.ValidationError(
                {"marks_obtained": f"Marks cannot be more than the maximum of {examination.max_marks}."}
            )
        return attrs

    def get_grade_remark(self, obj):
        """The remark that goes with the grade on the school's scale (e.g. B = Very Good)."""
        if not hasattr(self, "_remarks_by_grade"):
            self._remarks_by_grade = {grade: remark for _, grade, remark in get_grade_scale()}
        return self._remarks_by_grade.get(obj.grade, "")

    def get_percentage(self, obj):
        if not obj.examination.max_marks:
            return None

        return round(
            float(obj.marks_obtained)
            / float(obj.examination.max_marks)
            * 100,
            2
        )

    def update(self, instance, validated_data):
        """
        Every mark change writes an ExamMarkAuditLog row.
        """

        request = self.context["request"]

        old_marks = instance.marks_obtained

        new_marks = validated_data.get(
            "marks_obtained",
            old_marks
        )

        instance = super().update(
            instance,
            validated_data
        )

        if new_marks != old_marks:
            ExamMarkAuditLog.objects.create(
                result=instance,
                old_marks=old_marks,
                new_marks=new_marks,
                changed_by=request.user,
                reason=self.context.get(
                    "reason",
                    ""
                ),
            )

        return instance


class BulkResultEntrySerializer(serializers.Serializer):
    student = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all()
    )

    marks_obtained = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0
    )

    remarks = serializers.CharField(
        required=False,
        allow_blank=True
    )


class BulkResultSerializer(serializers.Serializer):
    """
    Enter marks for a whole class for one examination
    in a single request.
    """

    examination = serializers.PrimaryKeyRelatedField(
        queryset=Examination.objects.all()
    )

    entries = BulkResultEntrySerializer(
        many=True
    )

    def validate(self, attrs):
        examination = attrs["examination"]
        errors = []
        for entry in attrs["entries"]:
            if entry["marks_obtained"] > examination.max_marks:
                errors.append(
                    f"{entry['student'].index_number}: marks cannot be more than {examination.max_marks}."
                )
        if errors:
            raise serializers.ValidationError({"entries": errors})
        return attrs

    def save(self, **kwargs):
        request = self.context["request"]

        examination = self.validated_data["examination"]

        results = []

        # Save the whole class first, then compute grades / term results / positions once.
        with suspend_auto_compute(), transaction.atomic():
            for entry in self.validated_data["entries"]:

                result, created = ExaminationResult.objects.get_or_create(
                    examination=examination,
                    student=entry["student"],
                    defaults={
                        "marks_obtained": entry["marks_obtained"],
                        "remarks": entry.get("remarks", ""),
                        "entered_by": request.user,
                    },
                )

                if not created:
                    old_marks = result.marks_obtained

                    result.marks_obtained = entry["marks_obtained"]

                    result.remarks = entry.get(
                        "remarks",
                        result.remarks
                    )

                    result.save()

                    if old_marks != result.marks_obtained:
                        ExamMarkAuditLog.objects.create(
                            result=result,
                            old_marks=old_marks,
                            new_marks=result.marks_obtained,
                            changed_by=request.user,
                            reason=self.context.get("reason") or "Bulk entry update",
                        )

                results.append(result)

        recompute_for_examination(examination)
        return results


class GradeBoundarySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeBoundary
        fields = ("id", "grade", "min_percentage", "remark")

    def validate_grade(self, value):
        return value.strip().upper()


class SubjectTermResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    term_name = serializers.CharField(source="term.__str__", read_only=True)

    class Meta:
        model = SubjectTermResult
        fields = (
            "id", "student", "student_name", "student_index_number",
            "school_class", "school_class_name", "subject", "subject_name", "subject_code",
            "academic_year", "term", "term_name",
            "midterm_percentage", "endterm_percentage",
            "midterm_points", "midterm_out_of", "endterm_points", "endterm_out_of",
            "final_percentage",
            "grade", "remark", "teacher_remark", "position", "is_complete", "is_published",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["auto_remark"] = data["remark"]
        data["remark"] = instance.teacher_remark or data["remark"]  # the teacher's own remark wins
        return data


class TermSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_index_number = serializers.CharField(source="student.index_number", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.CharField(source="term.__str__", read_only=True)

    class Meta:
        model = TermSummary
        fields = (
            "id", "student", "student_name", "student_index_number",
            "school_class", "school_class_name", "academic_year", "term", "term_name",
            "subjects_count", "total_score", "average_percentage",
            "grade", "remark", "position", "class_size", "is_complete", "is_published",
        )
        read_only_fields = fields
