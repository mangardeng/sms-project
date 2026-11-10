"""
Single source of truth for parent -> student authorization checks.

Every app that exposes student-linked data (students, attendance,
examinations, fees, notifications, dashboard) MUST use these helpers
rather than re-implementing the check, so the rule described in design
doc 3.14 ("Parent-Student Data Security") is enforced consistently
everywhere:

    "the backend must first determine whether Student 25 is linked to
    the authenticated parent. If the relationship exists: ALLOW.
    If the relationship does not exist: DENY."
"""
from apps.parents.models import ParentStudent


def get_linked_student_ids(user):
    """Returns a list of Student IDs linked to this parent user. Empty list if not a parent."""
    if not hasattr(user, "parent_profile"):
        return []
    return list(
        ParentStudent.objects.filter(parent=user.parent_profile).values_list("student_id", flat=True)
    )


def parent_owns_student(user, student_id) -> bool:
    """The core allow/deny check described in 3.14."""
    if not hasattr(user, "parent_profile"):
        return False
    return ParentStudent.objects.filter(parent=user.parent_profile, student_id=student_id).exists()
