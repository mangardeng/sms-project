from django.core.management.base import BaseCommand

from apps.examinations.services import recompute_all, regrade_all_results


class Command(BaseCommand):
    help = (
        "Rebuilds every grade, subject term result (midterm + end of term), "
        "overall student grade and class position from the stored examination marks. "
        "Run once after upgrading; afterwards results update automatically."
    )

    def handle(self, *args, **options):
        regraded = regrade_all_results()
        groups = recompute_all()
        self.stdout.write(self.style.SUCCESS(
            f"Re-graded {regraded} mark(s) and rebuilt results for {groups} subject group(s)."
        ))
