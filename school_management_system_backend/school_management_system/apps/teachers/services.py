"""
Helpers enforcing 3.4.4: "A teacher must not be allowed to modify
students or classes that are outside the teacher's assigned
responsibilities unless explicitly authorized."
"""


def get_assigned_class_ids(user):
    """Returns SchoolClass IDs this teacher user is assigned to teach at least one subject in."""
    if not hasattr(user, "teacher_profile"):
        return []
    from apps.subjects.models import ClassSubject

    return list(
        ClassSubject.objects.filter(teacher=user.teacher_profile)
        .values_list("school_class_id", flat=True)
        .distinct()
    )


def teacher_assigned_to_class(user, school_class_id) -> bool:
    return school_class_id in get_assigned_class_ids(user)


def teacher_assigned_to_student(user, student) -> bool:
    if student.school_class_id is None:
        return False
    return teacher_assigned_to_class(user, student.school_class_id)


def teacher_teaches_subject(user, school_class_id, subject_id) -> bool:
    """True when this teacher is the assigned subject teacher for the subject in that class."""
    from apps.subjects.models import ClassSubject

    if not hasattr(user, "teacher_profile"):
        return False
    return ClassSubject.objects.filter(
        teacher=user.teacher_profile, school_class_id=school_class_id, subject_id=subject_id
    ).exists()
