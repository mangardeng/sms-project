from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, has_role
from apps.core.models import log_action
from apps.examinations.models import (
    Examination,
    ExaminationResult,
    ExaminationType,
    GradeBoundary,
    SubjectTermResult,
    TermSummary,
)
from apps.examinations.permissions import ExaminationAccessPermission, TermResultAccessPermission
from apps.examinations.serializers import (
    BulkResultSerializer,
    ExaminationResultSerializer,
    ExaminationSerializer,
    ExaminationTypeSerializer,
    GradeBoundarySerializer,
    SubjectTermResultSerializer,
    TermSummarySerializer,
)
from apps.examinations.services import ensure_computed, recompute_all, regrade_all_results
from apps.parents.services import get_linked_student_ids
from apps.teachers.services import get_assigned_class_ids, teacher_assigned_to_class, teacher_teaches_subject


class ExaminationTypeViewSet(viewsets.ModelViewSet):
    queryset = ExaminationType.objects.all()
    serializer_class = ExaminationTypeSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]


class ExaminationViewSet(viewsets.ModelViewSet):
    permission_classes = [ExaminationAccessPermission]
    serializer_class = ExaminationSerializer
    filterset_fields = ["school_class", "subject", "academic_year", "term", "is_published"]

    def get_queryset(self):
        user = self.request.user
        qs = Examination.objects.select_related("school_class", "subject", "examination_type")

        if user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return qs
        if user.role == User.Role.TEACHER:
            return qs.filter(school_class_id__in=get_assigned_class_ids(user))
        if user.role == User.Role.PARENT:
            student_ids = get_linked_student_ids(user)
            return qs.filter(is_published=True, results__student_id__in=student_ids).distinct()
        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            return qs.filter(is_published=True, school_class=user.student_profile.school_class)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        school_class = serializer.validated_data.get("school_class")
        if user.role == User.Role.TEACHER and not teacher_assigned_to_class(user, school_class.id):
            raise PermissionDenied("You may only create examinations for classes assigned to you.")
        instance = serializer.save(created_by=user)
        log_action(user=user, action="create", model_name="Examination", object_id=instance.id)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """POST /api/examinations/{id}/publish/ — Admin/Head Teacher releases results to parents/students."""
        exam = self.get_object()
        if not (request.user.is_superuser or has_role(request.user, User.Role.ADMIN, User.Role.HEAD_TEACHER)):
            raise PermissionDenied("Only an administrator or head teacher may publish results.")
        exam.is_published = True
        exam.marks_locked = True
        exam.save(update_fields=["is_published", "marks_locked"])
        log_action(user=request.user, action="update", model_name="Examination", object_id=exam.id, description="Published results")
        return Response(ExaminationSerializer(exam).data)


def _may_enter_marks(user, examination):
    """Administrators and the subject teacher may enter or correct marks (also after publishing)."""
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    return user.role == User.Role.TEACHER and teacher_teaches_subject(user, examination.school_class_id, examination.subject_id)


def _require_reason_if_locked(request, examination):
    if (examination.marks_locked or examination.is_published) and not str(request.data.get("reason", "")).strip():
        raise ValidationError({"reason": "These results are already published. Give a short reason for the correction."})


class ExaminationResultViewSet(viewsets.ModelViewSet):
    permission_classes = [ExaminationAccessPermission]
    serializer_class = ExaminationResultSerializer
    filterset_fields = ["examination", "student"]

    def get_queryset(self):
        user = self.request.user
        qs = ExaminationResult.objects.select_related("student__user", "examination__subject", "examination__school_class")

        if user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return qs
        if user.role == User.Role.TEACHER:
            return qs.filter(examination__school_class_id__in=get_assigned_class_ids(user))
        if user.role == User.Role.PARENT:
            return qs.filter(examination__is_published=True, student_id__in=get_linked_student_ids(user))
        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            return qs.filter(examination__is_published=True, student=user.student_profile)
        return qs.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["reason"] = self.request.data.get("reason", "")
        return ctx

    def perform_create(self, serializer):
        user = self.request.user
        examination = serializer.validated_data.get("examination")
        if not _may_enter_marks(user, examination):
            raise PermissionDenied("Only the subject teacher or an administrator may enter marks for this subject.")
        _require_reason_if_locked(self.request, examination)
        instance = serializer.save(entered_by=user)
        log_action(user=user, action="create", model_name="ExaminationResult", object_id=instance.id)

    def perform_update(self, serializer):
        _require_reason_if_locked(self.request, serializer.instance.examination)
        serializer.save()
        log_action(user=self.request.user, action="update", model_name="ExaminationResult", object_id=serializer.instance.id)

    def perform_destroy(self, instance):
        _require_reason_if_locked(self.request, instance.examination)
        log_action(user=self.request.user, action="delete", model_name="ExaminationResult", object_id=instance.id)
        instance.delete()

    @action(detail=False, methods=["post"], url_path="bulk-entry")
    def bulk_entry(self, request):
        """POST /api/examinations/results/bulk-entry/  — enter a whole class's marks at once."""
        examination_id = request.data.get("examination")
        from apps.examinations.models import Examination

        try:
            examination = Examination.objects.get(pk=examination_id)
        except Examination.DoesNotExist:
            return Response({"detail": "Examination not found."}, status=404)

        user = request.user
        if not _may_enter_marks(user, examination):
            raise PermissionDenied("Only the subject teacher or an administrator may enter marks for this subject.")
        _require_reason_if_locked(request, examination)

        serializer = BulkResultSerializer(data=request.data, context={"request": request, "reason": request.data.get("reason", "")})
        serializer.is_valid(raise_exception=True)
        results = serializer.save()
        log_action(user=user, action="create", model_name="ExaminationResult", description=f"Bulk marks entry for exam {examination_id}")
        return Response(ExaminationResultSerializer(results, many=True).data)



class GradeBoundaryViewSet(viewsets.ModelViewSet):
    """
    The school's grading scale (e.g. 80+ = A). Everyone signed in can read it;
    only an administrator can change it. Any change re-grades every mark and
    rebuilds every term result automatically.
    """

    queryset = GradeBoundary.objects.all()
    serializer_class = GradeBoundarySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def _rebuild(self):
        regrade_all_results()
        recompute_all()

    def perform_create(self, serializer):
        serializer.save()
        self._rebuild()
        log_action(user=self.request.user, action="update", model_name="GradeBoundary", description="Grade scale changed")

    def perform_update(self, serializer):
        serializer.save()
        self._rebuild()
        log_action(user=self.request.user, action="update", model_name="GradeBoundary", description="Grade scale changed")

    def perform_destroy(self, instance):
        instance.delete()
        self._rebuild()
        log_action(user=self.request.user, action="update", model_name="GradeBoundary", description="Grade scale changed")


def _scope_to_user(user, queryset):
    """Same visibility rules as examination marks, for the computed term results."""
    if user.is_superuser or has_role(user, User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
        return queryset
    if user.role == User.Role.TEACHER:
        return queryset.filter(school_class_id__in=get_assigned_class_ids(user))
    if user.role == User.Role.PARENT:
        return queryset.filter(is_published=True, student_id__in=get_linked_student_ids(user))
    if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
        return queryset.filter(is_published=True, student=user.student_profile)
    return queryset.none()


class SubjectTermResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Per-subject term results (midterm + end of term combined). Read-only: computed automatically."""

    permission_classes = [TermResultAccessPermission]
    serializer_class = SubjectTermResultSerializer
    filterset_fields = ["school_class", "subject", "term", "academic_year", "student"]

    def get_queryset(self):
        ensure_computed()
        qs = SubjectTermResult.objects.select_related(
            "student__user", "school_class", "subject", "term__academic_year"
        )
        return _scope_to_user(self.request.user, qs)


class TermSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Each student's overall result for a term (total, average, grade, class position)."""

    permission_classes = [TermResultAccessPermission]
    serializer_class = TermSummarySerializer
    filterset_fields = ["school_class", "term", "academic_year", "student"]

    def get_queryset(self):
        ensure_computed()
        qs = TermSummary.objects.select_related("student__user", "school_class", "term__academic_year")
        return _scope_to_user(self.request.user, qs)

    @action(detail=True, methods=["get"], url_path="report-card")
    def report_card(self, request, pk=None):
        """GET /api/examinations/term-summaries/{id}/report-card/ — overall result plus every subject."""
        summary = self.get_object()
        subjects = _scope_to_user(
            request.user,
            SubjectTermResult.objects.filter(student_id=summary.student_id, term_id=summary.term_id).select_related(
                "student__user", "school_class", "subject", "term__academic_year"
            ),
        ).order_by("subject__name")
        data = TermSummarySerializer(summary).data
        student = summary.student
        class_teacher = getattr(summary.school_class, "class_teacher", None)
        data["academic_year_name"] = summary.term.academic_year.name
        data["term_start"] = summary.term.start_date
        data["term_end"] = summary.term.end_date
        data["gender"] = student.get_gender_display() if student.gender else ""
        data["date_of_birth"] = student.date_of_birth
        data["class_teacher_name"] = class_teacher.user.get_full_name() if class_teacher else ""
        data["subjects"] = SubjectTermResultSerializer(subjects, many=True).data
        return Response(data)

    @action(detail=False, methods=["post"])
    def recompute(self, request):
        """POST /api/examinations/term-summaries/recompute/ {school_class, term} — rebuild results on demand."""
        user = request.user
        class_id = request.data.get("school_class")
        term_id = request.data.get("term")
        if not class_id or not term_id:
            raise ValidationError({"detail": "Choose a class and a term."})
        if user.role == User.Role.TEACHER and not teacher_assigned_to_class(user, int(class_id)):
            raise PermissionDenied("You may only recalculate results for classes assigned to you.")
        scopes = recompute_all(class_id=int(class_id), term_id=int(term_id))
        log_action(user=user, action="update", model_name="TermSummary", description=f"Recalculated term results for class {class_id}, term {term_id}")
        return Response({"detail": f"Recalculated {scopes} subject result group(s)."})
