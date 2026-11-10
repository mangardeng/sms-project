from datetime import date

from django.core.management.base import BaseCommand

from apps.core.models import AcademicYear, Term


class Command(BaseCommand):
    help = "Creates a default current Academic Year and Term so other modules (classes, exams, fees) have something to attach to on a fresh install."

    def handle(self, *args, **options):
        year, created = AcademicYear.objects.get_or_create(
            name="2025/2026",
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2026, 7, 31),
                "is_current": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created academic year: {year.name}"))
        else:
            self.stdout.write(f"Academic year already exists: {year.name}")

        term, created = Term.objects.get_or_create(
            academic_year=year,
            name=Term.TermName.TERM_1,
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2025, 12, 15),
                "is_current": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created term: {term}"))
        else:
            self.stdout.write(f"Term already exists: {term}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
