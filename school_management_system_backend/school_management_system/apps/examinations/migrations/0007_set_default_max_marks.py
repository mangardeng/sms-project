from decimal import Decimal

from django.db import migrations


def fill(apps, schema_editor):
    ExaminationType = apps.get_model("examinations", "ExaminationType")
    ExaminationType.objects.filter(category="midterm", default_max_marks=Decimal("100")).update(default_max_marks=Decimal("40"))
    ExaminationType.objects.filter(category="end_term", default_max_marks=Decimal("100")).update(default_max_marks=Decimal("60"))


class Migration(migrations.Migration):
    dependencies = [("examinations", "0006_type_default_max_marks")]
    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
