from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.parents.services import parent_owns_student
from apps.teachers.services import teacher_assigned_to_class, teacher_teaches_subject


class ExaminationAccessPermission(BasePermission):
    """
    Admin: full.
    Head Teacher/Registrar: view only.
    Teacher: create/edit exams & marks ONLY for classes/subjects assigned
             to them (3.4.4), and only while not `marks_locked`.
    Accountant/Librarian: no access (3.8 matrix: Accountant Results = No).
    Parent/Student: view only PUBLISHED results, and only for the
             linked/own student (3.14).
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            return True

        if user.role in (User.Role.PARENT, User.Role.STUDENT):
            return request.method in SAFE_METHODS

        # Accountant, Librarian: explicitly denied access to exam records.
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        school_class_id = getattr(obj, "school_class_id", None) or getattr(obj.examination, "school_class_id", None)

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if user.role in (User.Role.HEAD_TEACHER, User.Role.REGISTRAR):
            return request.method in SAFE_METHODS

        if user.role == User.Role.TEACHER:
            if hasattr(obj, "marks_locked"):  # the examination itself
                if not teacher_assigned_to_class(user, school_class_id):
                    return False
                return request.method in SAFE_METHODS or not obj.marks_locked
            # A mark: only the subject teacher may change it (even after publishing, to fix a mistake).
            exam = obj.examination
            if request.method in SAFE_METHODS:
                return teacher_assigned_to_class(user, school_class_id)
            return teacher_teaches_subject(user, school_class_id, exam.subject_id)

        if user.role == User.Role.PARENT:
            student_id = getattr(obj, "student_id", None)
            is_published = obj.examination.is_published if hasattr(obj, "examination") else False
            return request.method in SAFE_METHODS and is_published and parent_owns_student(user, student_id)

        if user.role == User.Role.STUDENT:
            is_published = obj.examination.is_published if hasattr(obj, "examination") else False
            owns_record = getattr(obj, "student", None) and obj.student.user_id == user.id
            return request.method in SAFE_METHODS and is_published and owns_record

        return False


class TermResultAccessPermission(ExaminationAccessPermission):
    """
    Same role rules as examination marks. The computed term results are
    read-only and the querysets already limit what each role can see
    (teacher: assigned classes, parent: linked children, student: self, and only
    when published), so no extra object-level check is needed.
    """

    def has_object_permission(self, request, view, obj):
        return True
