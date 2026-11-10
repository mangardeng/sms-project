from django.db import migrations


def fix(apps, schema_editor):
    ExaminationType = apps.get_model("examinations", "ExaminationType")
    for exam_type in ExaminationType.objects.filter(category="other"):
        name = exam_type.name.lower()
        if "mid" in name:
            exam_type.category = "midterm"
        elif "end" in name or "final" in name:
            exam_type.category = "end_term"
        else:
            continue
        exam_type.save(update_fields=["category"])


class Migration(migrations.Migration):
    dependencies = [("examinations", "0004_subject_term_points")]
    operations = [migrations.RunPython(fix, migrations.RunPython.noop)]
