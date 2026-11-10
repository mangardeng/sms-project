"""
Subject results sheet.

One table per class + subject + term where the subject teacher (or an administrator) types each
student's midterm mark and end-of-term mark. Everything else - total, percentage, grade, remark
and positions - is calculated automatically. Mistakes can be corrected here at any time, even after
the results are published (a reason is then recorded in the audit log).
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import permissions
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.classes.models import SchoolClass
from apps.core.models import AcademicYear, Term, log_action
from apps.examinations.models import (
    ExamMarkAuditLog,
    Examination,
    ExaminationResult,
    ExaminationType,
    SubjectTermResult,
)
from apps.examinations.services import recompute_scope, suspend_auto_compute
from apps.students.models import Student
from apps.subjects.models import ClassSubject, Subject
from apps.teachers.services import teacher_teaches_subject

CATEGORIES = (ExaminationType.Category.MIDTERM, ExaminationType.Category.END_TERM)
LABELS = {ExaminationType.Category.MIDTERM: "Midterm", ExaminationType.Category.END_TERM: "End of Term"}


def _is_admin(user):
    return user.is_superuser or user.role == User.Role.ADMIN


def can_edit_sheet(user, class_id, subject_id):
    if _is_admin(user):
        return True
    return user.role == User.Role.TEACHER and teacher_teaches_subject(user, class_id, subject_id)


def can_view_sheet(user, class_id, subject_id):
    return can_edit_sheet(user, class_id, subject_id) or user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR)


def _exam(category, class_id, subject_id, term_id):
    return Examination.objects.filter(
        school_class_id=class_id, subject_id=subject_id, term_id=term_id, examination_type__category=category
    ).select_related("examination_type").first()


def _type(category):
    exam_type = ExaminationType.objects.filter(category=category).order_by("id").first()
    if exam_type is None:
        exam_type = ExaminationType.objects.create(name=f"{LABELS[category]} Exam", category=category)
    return exam_type


def _parse_mark(value, label):
    try:
        mark = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError({"detail": f"{label}: '{value}' is not a number."})
    if mark < 0:
        raise ValidationError({"detail": f"{label}: marks cannot be negative."})
    return mark


def _lookup(request, data):
    try:
        school_class = SchoolClass.objects.get(pk=data.get("school_class"))
        subject = Subject.objects.get(pk=data.get("subject"))
        term = Term.objects.select_related("academic_year").get(pk=data.get("term"))
    except (SchoolClass.DoesNotExist, Subject.DoesNotExist, Term.DoesNotExist, ValueError, TypeError):
        raise NotFound("Choose a class, a subject and a term.")
    return school_class, subject, term


class SubjectSheetOptionsView(APIView):
    """GET /api/examinations/subject-sheet/options/ - the class + subject pairs this user may work on."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = ClassSubject.objects.select_related("school_class", "subject", "academic_year")
        if _is_admin(user) or user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            current = AcademicYear.objects.filter(is_current=True).first()
            if current:
                qs = qs.filter(academic_year=current)
        elif user.role == User.Role.TEACHER and hasattr(user, "teacher_profile"):
            qs = qs.filter(teacher=user.teacher_profile)
        else:
            raise PermissionDenied("Subject results are only available to teachers and administrators.")
        seen, options = set(), []
        for cs in qs.order_by("school_class__level", "subject__name"):
            key = (cs.school_class_id, cs.subject_id)
            if key in seen:
                continue
            seen.add(key)
            options.append({
                "school_class": cs.school_class_id, "school_class_name": cs.school_class.name,
                "subject": cs.subject_id, "subject_name": cs.subject.name,
                "can_edit": can_edit_sheet(user, cs.school_class_id, cs.subject_id),
            })
        return Response(options)


class SubjectSheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # ---------------------------------------------------------------- read
    def get(self, request):
        school_class, subject, term = _lookup(request, request.query_params)
        user = request.user
        if not can_view_sheet(user, school_class.id, subject.id):
            raise PermissionDenied("Only the subject teacher or an administrator may open this sheet.")
        return Response(self._build(school_class, subject, term, can_edit_sheet(user, school_class.id, subject.id)))

    def _build(self, school_class, subject, term, can_edit):
        exams = {c: _exam(c, school_class.id, subject.id, term.id) for c in CATEGORIES}
        meta = {}
        for category, exam in exams.items():
            meta[category] = {
                "exam_id": exam.id if exam else None,
                "out_of": exam.max_marks if exam else _type(category).default_max_marks,
                "is_published": bool(exam and exam.is_published),
            }
        marks = {}
        for category, exam in exams.items():
            if exam:
                for r in ExaminationResult.objects.filter(examination=exam):
                    marks[(r.student_id, category)] = r.marks_obtained
        computed = {r.student_id: r for r in SubjectTermResult.objects.filter(school_class=school_class, subject=subject, term=term)}

        rows = []
        for student in Student.objects.filter(school_class=school_class, status="active").select_related("user").order_by("index_number"):
            row = computed.get(student.id)
            mid = marks.get((student.id, ExaminationType.Category.MIDTERM))
            end = marks.get((student.id, ExaminationType.Category.END_TERM))
            rows.append({
                "student": student.id,
                "student_name": student.user.get_full_name(),
                "student_index_number": student.index_number,
                "midterm_marks": mid,
                "endterm_marks": end,
                "total": (row.midterm_points or 0) + (row.endterm_points or 0) if row else None,
                "percentage": row.final_percentage if row else None,
                "grade": row.grade if row else "",
                "auto_remark": row.remark if row else "",
                "teacher_remark": row.teacher_remark if row else "",
                "remark": (row.teacher_remark or row.remark) if row else "",
                "position": row.position if row else None,
                "is_complete": row.is_complete if row else False,
            })
        return {
            "school_class": school_class.id, "school_class_name": school_class.name,
            "subject": subject.id, "subject_name": subject.name,
            "term": term.id, "term_name": str(term),
            "midterm": meta[ExaminationType.Category.MIDTERM],
            "endterm": meta[ExaminationType.Category.END_TERM],
            "can_edit": can_edit,
            "rows": rows,
        }

    # --------------------------------------------------------------- write
    @transaction.atomic
    def post(self, request):
        data = request.data
        school_class, subject, term = _lookup(request, data)
        user = request.user
        if not can_edit_sheet(user, school_class.id, subject.id):
            raise PermissionDenied("Only the subject teacher or an administrator may enter or correct these results.")

        entries = data.get("entries") or []
        if not isinstance(entries, list):
            raise ValidationError({"detail": "entries must be a list."})
        reason = str(data.get("reason", "")).strip()

        # Make sure both exams exist (created on first use) and are marked out of the right total.
        exams = {}
        for category, key in ((ExaminationType.Category.MIDTERM, "midterm_out_of"), (ExaminationType.Category.END_TERM, "endterm_out_of")):
            exam = _exam(category, school_class.id, subject.id, term.id)
            wanted = data.get(key)
            exam_type = exam.examination_type if exam else _type(category)
            if exam is None:
                exam = Examination.objects.create(
                    name=f"{term.get_name_display()} {LABELS[category]} - {subject.name}",
                    examination_type=exam_type, school_class=school_class, subject=subject,
                    academic_year=term.academic_year, term=term, date=term.start_date,
                    max_marks=_parse_mark(wanted, "Out of") if wanted not in (None, "") else exam_type.default_max_marks,
                    created_by=user,
                )
            elif wanted not in (None, "") and Decimal(str(wanted)) != exam.max_marks:
                new_max = _parse_mark(wanted, f"{LABELS[category]} out of")
                if new_max <= 0:
                    raise ValidationError({"detail": f"{LABELS[category]} must be marked out of more than 0."})
                too_big = exam.results.filter(marks_obtained__gt=new_max).count()
                if too_big:
                    raise ValidationError({"detail": f"{too_big} {LABELS[category]} mark(s) are above {new_max}. Correct them first."})
                exam.max_marks = new_max
                exam.save(update_fields=["max_marks"])
            exams[category] = exam

        valid_students = {s.id: s for s in Student.objects.filter(school_class=school_class)}
        pending_changes, remarks = [], {}
        for entry in entries:
            student = valid_students.get(entry.get("student"))
            if student is None:
                raise ValidationError({"detail": "A student in the list does not belong to this class."})
            for category, field in ((ExaminationType.Category.MIDTERM, "midterm_marks"), (ExaminationType.Category.END_TERM, "endterm_marks")):
                value = entry.get(field)
                if value in (None, ""):
                    continue
                exam = exams[category]
                mark = _parse_mark(value, f"{student.index_number} {LABELS[category]}")
                if mark > exam.max_marks:
                    raise ValidationError({"detail": f"{student.index_number}: {LABELS[category]} marks cannot be more than {exam.max_marks}."})
                pending_changes.append((exam, student, mark))
            if "remark" in entry:
                remarks[student.id] = str(entry.get("remark") or "").strip()[:255]

        # A reason is needed only when changing marks that are already published.
        for exam, student, mark in pending_changes:
            existing = ExaminationResult.objects.filter(examination=exam, student=student).first()
            if existing and existing.marks_obtained != mark and (exam.is_published or exam.marks_locked) and not reason:
                raise ValidationError({"reason": "These results are already published. Give a short reason for the correction."})

        changed = 0
        with suspend_auto_compute():
            for exam, student, mark in pending_changes:
                result, created = ExaminationResult.objects.get_or_create(
                    examination=exam, student=student, defaults={"marks_obtained": mark, "entered_by": user},
                )
                if created:
                    changed += 1
                elif result.marks_obtained != mark:
                    old = result.marks_obtained
                    result.marks_obtained = mark
                    result.save()
                    ExamMarkAuditLog.objects.create(
                        result=result, old_marks=old, new_marks=mark, changed_by=user,
                        reason=reason or "Correction on subject sheet",
                    )
                    changed += 1

        recompute_scope(school_class.id, subject.id, term.id)
        for student_id, remark in remarks.items():
            SubjectTermResult.objects.filter(student_id=student_id, subject=subject, term=term).update(teacher_remark=remark)

        log_action(
            user=user, action="update", model_name="SubjectTermResult",
            description=f"Subject sheet saved: {school_class.name} / {subject.name} / {term} ({changed} mark(s) changed). {reason}".strip(),
        )
        return Response(self._build(school_class, subject, term, True))
