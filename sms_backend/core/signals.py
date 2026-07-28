from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from .models import AuditLog



@receiver(post_save, sender=User)
def log_user_change(sender, instance, created, **kwargs):

    AuditLog.objects.create(

        action="Created" if created else "Updated",

        model_name="User",

        object_id=str(instance.id)

    )