"""
Automatic result computation.

Whenever Midterm or End-of-term marks are entered, changed or deleted, the
functions below rebuild:

  1. SubjectTermResult - one row per student per subject per term. The
     midterm marks and the end-of-term marks are ADDED together, exactly as on
     the school report card: e.g. 36 (out of 40) + 56 (out of 60) = 92 out of
     100 = 92%. Each exam's "out of" (max marks) is what sets its share. Until
     the end-of-term marks arrive, the result is "provisional" and uses the
     midterm only (36 out of 40 = 90%).
  2. A grade and remark for each subject result, from the school's grade scale.
  3. The student's position in the class for each subject.
  4. TermSummary - one row per student per term: total score, average, overall
     grade and overall class position.

Nothing here is typed in by hand; it is always derived from ExaminationResult.
"""
import threading
from collections import defaultdict
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.examinations.models import (
    Examination,
    ExaminationResult,
    ExaminationType,
    SubjectTermResult,
    TermSummary,
    get_grade_scale,
    grade_and_remark,
)

MIDTERM = ExaminationType.Category.MIDTERM
END_TERM = ExaminationType.Category.END_TERM
COUNTED_CATEGORIES = (MIDTERM, END_TERM)

_TWO_PLACES = Decimal("0.01")
_state = threading.local()


def _quantize(value) -> Decimal:
    return Decimal(value).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def percentage_of(marks, max_marks):
    """marks / max_marks as a 0-100 Decimal, or None when max_marks is not set."""
    if not max_marks:
        return None
    return _quantize(Decimal(marks) / Decimal(max_marks) * 100)


# --------------------------------------------------------------------------
# Pausing automatic recalculation (used by bulk entry so a whole class is
# saved first and the results are computed once).
# --------------------------------------------------------------------------
def is_suspended() -> bool:
    return getattr(_state, "depth", 0) > 0


@contextmanager
def suspend_auto_compute():
    _state.depth = getattr(_state, "depth", 0) + 1
    try:
        yield
    finally:
        _state.depth -= 1


# --------------------------------------------------------------------------
# Ranking helper (ties share a position: 1, 2, 2, 4)
# --------------------------------------------------------------------------
def _assign_ranks(rows, score_attr, rank_attr):
    changed = []
    previous_score = None
    rank = 0
    for index, row in enumerate(rows, start=1):
        score = getattr(row, score_attr)
        if score != previous_score:
            rank = index
            previous_score = score
        if getattr(row, rank_attr) != rank:
            setattr(row, rank_attr, rank)
            changed.append(row)
    return changed


# --------------------------------------------------------------------------
# Per subject
# --------------------------------------------------------------------------
def _recompute_subject_results(class_id, subject_id, term_id, scale):
    """Rebuild every student's SubjectTermResult for one subject in one class/term."""
    exams = list(
        Examination.objects.filter(
            school_class_id=class_id,
            subject_id=subject_id,
            term_id=term_id,
            examination_type__category__in=COUNTED_CATEGORIES,
        ).select_related("examination_type")
    )

    components = defaultdict(dict)  # student_id -> {category: (marks, out_of, exam)}
    if exams:
        for result in ExaminationResult.objects.filter(examination__in=exams):
            exam = result.examination
            if not exam.max_marks:
                continue
            components[result.student_id][exam.examination_type.category] = (
                Decimal(result.marks_obtained),
                Decimal(exam.max_marks),
                exam,
            )

    existing = SubjectTermResult.objects.filter(school_class_id=class_id, subject_id=subject_id, term_id=term_id)
    stale_student_ids = set(existing.values_list("student_id", flat=True)) - set(components)
    if stale_student_ids:
        existing.filter(student_id__in=stale_student_ids).delete()

    for student_id, parts in components.items():
        total_marks = sum(marks for marks, _, _ in parts.values())
        total_out_of = sum(out_of for _, out_of, _ in parts.values())
        final = _quantize(total_marks / total_out_of * 100)
        grade, remark = grade_and_remark(final, scale)
        exams_used = [exam for _, _, exam in parts.values()]

        SubjectTermResult.objects.update_or_create(
            student_id=student_id,
            subject_id=subject_id,
            term_id=term_id,
            defaults={
                "school_class_id": class_id,
                "academic_year_id": exams_used[0].academic_year_id,
                "midterm_percentage": percentage_of(*parts[MIDTERM][:2]) if MIDTERM in parts else None,
                "endterm_percentage": percentage_of(*parts[END_TERM][:2]) if END_TERM in parts else None,
                "midterm_points": _quantize(parts[MIDTERM][0]) if MIDTERM in parts else None,
                "midterm_out_of": parts[MIDTERM][1] if MIDTERM in parts else None,
                "endterm_points": _quantize(parts[END_TERM][0]) if END_TERM in parts else None,
                "endterm_out_of": parts[END_TERM][1] if END_TERM in parts else None,
                "final_percentage": final,
                "grade": grade,
                "remark": remark,
                "is_complete": MIDTERM in parts and END_TERM in parts,
                "is_published": all(exam.is_published for exam in exams_used),
            },
        )

    ranked = list(
        SubjectTermResult.objects.filter(school_class_id=class_id, subject_id=subject_id, term_id=term_id)
        .order_by("-final_percentage", "student_id")
    )
    changed = _assign_ranks(ranked, "final_percentage", "position")
    if changed:
        SubjectTermResult.objects.bulk_update(changed, ["position"])


# --------------------------------------------------------------------------
# Per student overall (all subjects) + class position
# --------------------------------------------------------------------------
def _refresh_term_summaries(class_id, term_id, scale):
    rows = list(SubjectTermResult.objects.filter(school_class_id=class_id, term_id=term_id))
    by_student = defaultdict(list)
    for row in rows:
        by_student[row.student_id].append(row)

    TermSummary.objects.filter(school_class_id=class_id, term_id=term_id).exclude(
        student_id__in=list(by_student)
    ).delete()
    if not by_student:
        return

    expected_subjects = (
        Examination.objects.filter(
            school_class_id=class_id, term_id=term_id, examination_type__category__in=COUNTED_CATEGORIES
        )
        .values("subject_id")
        .distinct()
        .count()
    )

    for student_id, subject_rows in by_student.items():
        count = len(subject_rows)
        total = sum(r.final_percentage for r in subject_rows)
        average = _quantize(total / count)
        grade, remark = grade_and_remark(average, scale)
        TermSummary.objects.update_or_create(
            student_id=student_id,
            term_id=term_id,
            defaults={
                "school_class_id": class_id,
                "academic_year_id": subject_rows[0].academic_year_id,
                "subjects_count": count,
                "total_score": _quantize(total),
                "average_percentage": average,
                "grade": grade,
                "remark": remark,
                "is_complete": count >= expected_subjects and all(r.is_complete for r in subject_rows),
                "is_published": all(r.is_published for r in subject_rows),
            },
        )

    summaries = list(
        TermSummary.objects.filter(school_class_id=class_id, term_id=term_id)
        .order_by("-average_percentage", "student_id")
    )
    for summary in summaries:
        summary.class_size = len(summaries)
    _assign_ranks(summaries, "average_percentage", "position")
    TermSummary.objects.bulk_update(summaries, ["position", "class_size"])


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------
@transaction.atomic
def recompute_scope(class_id, subject_id, term_id, *, refresh_summaries=True, scale=None):
    scale = scale or get_grade_scale()
    _recompute_subject_results(class_id, subject_id, term_id, scale)
    if refresh_summaries:
        _refresh_term_summaries(class_id, term_id, scale)


def recompute_for_examination(examination):
    """Call after marks for this examination changed (or the exam itself changed)."""
    recompute_scope(examination.school_class_id, examination.subject_id, examination.term_id)


@transaction.atomic
def regrade_all_results():
    """Re-apply the current grade scale to every stored examination mark."""
    scale = get_grade_scale()
    changed = []
    for result in ExaminationResult.objects.select_related("examination"):
        percentage = percentage_of(result.marks_obtained, result.examination.max_marks)
        if percentage is None:
            continue
        grade, _ = grade_and_remark(percentage, scale)
        if result.grade != grade:
            result.grade = grade
            changed.append(result)
    if changed:
        ExaminationResult.objects.bulk_update(changed, ["grade"])
    return len(changed)


@transaction.atomic
def recompute_all(class_id=None, term_id=None):
    """
    Rebuild every computed result (optionally only one class and/or term).
    Used after the grade scale changes, after weights change, and by the
    'Recalculate' button / `recompute_results` command.
    """
    scale = get_grade_scale()
    exam_filter = {}
    result_filter = {}
    if class_id:
        exam_filter["school_class_id"] = class_id
        result_filter["school_class_id"] = class_id
    if term_id:
        exam_filter["term_id"] = term_id
        result_filter["term_id"] = term_id

    scopes = set(Examination.objects.filter(**exam_filter).values_list("school_class_id", "subject_id", "term_id"))
    scopes |= set(SubjectTermResult.objects.filter(**result_filter).values_list("school_class_id", "subject_id", "term_id"))

    for cls, subject, term in scopes:
        recompute_scope(cls, subject, term, refresh_summaries=False, scale=scale)
    for cls, term in {(c, t) for c, _, t in scopes}:
        _refresh_term_summaries(cls, term, scale)
    return len(scopes)


def ensure_computed():
    """
    Marks entered before term results existed (or loaded straight into the database) have no
    computed results yet. The first time results are requested, build them once.
    """
    if ExaminationResult.objects.exists() and not SubjectTermResult.objects.exists():
        recompute_all()
