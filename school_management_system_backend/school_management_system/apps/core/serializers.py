from rest_framework import serializers

from apps.core.models import AcademicYear, Term


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ("id", "name", "start_date", "end_date", "is_current")


class TermSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Term
        fields = (
            "id", "academic_year", "academic_year_name", "display_name",
            "name", "start_date", "end_date", "is_current",
        )
