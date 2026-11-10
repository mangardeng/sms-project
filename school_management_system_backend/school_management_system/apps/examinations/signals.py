from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.examinations.models import Examination, ExaminationResult, ExaminationType
from apps.examinations.services import (
    is_suspended,
    recompute_for_examination,
    recompute_scope,
)


@receiver(post_save, sender=ExaminationResult)
@receiver(post_delete, sender=ExaminationResult)
def recompute_when_marks_change(sender, instance, **kwargs):
    """Marks entered / edited / removed -> term results, grades and positions update by themselves."""
    if is_suspended():
        return
    try:
        examination = instance.examination
    except ObjectDoesNotExist:
        return
    recompute_for_examination(examination)


@receiver(post_save, sender=Examination)
def recompute_when_examination_changes(sender, instance, **kwargs):
    """Max marks, type or published state changed."""
    if not is_suspended():
        recompute_for_examination(instance)


@receiver(post_delete, sender=Examination)
def recompute_when_examination_deleted(sender, instance, **kwargs):
    if not is_suspended():
        recompute_scope(instance.school_class_id, instance.subject_id, instance.term_id)


@receiver(post_save, sender=ExaminationType)
def recompute_when_type_changes(sender, instance, created, **kwargs):
    """Weight or category of an exam type changed -> everything built from it is rebuilt."""
    if created or is_suspended():
        return
    scopes = set(instance.examinations.values_list("school_class_id", "subject_id", "term_id"))
    for class_id, subject_id, term_id in scopes:
        recompute_scope(class_id, subject_id, term_id)
