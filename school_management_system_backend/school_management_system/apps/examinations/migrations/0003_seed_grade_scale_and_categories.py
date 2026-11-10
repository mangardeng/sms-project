from decimal import Decimal

from django.db import migrations

DEFAULT_SCALE = [
    ("A", Decimal("80"), "Excellent"),
    ("B", Decimal("70"), "Very Good"),
    ("C", Decimal("60"), "Good"),
    ("D", Decimal("50"), "Satisfactory"),
    ("E", Decimal("40"), "Pass"),
    ("F", Decimal("0"), "Fail"),
]


def seed(apps, schema_editor):
    GradeBoundary = apps.get_model("examinations", "GradeBoundary")
    if not GradeBoundary.objects.exists():
        for grade, minimum, remark in DEFAULT_SCALE:
            GradeBoundary.objects.create(grade=grade, min_percentage=minimum, remark=remark)

    # Existing exam types: work out whether they are midterm or end-of-term from the name.
    ExaminationType = apps.get_model("examinations", "ExaminationType")
    for exam_type in ExaminationType.objects.all():
        name = exam_type.name.lower()
        if "mid" in name:
            exam_type.category = "midterm"
        elif "end" in name or "final" in name:
            exam_type.category = "end_term"
        else:
            continue
        exam_type.save(update_fields=["category"])


class Migration(migrations.Migration):
    dependencies = [("examinations", "0002_grading_and_term_results")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
