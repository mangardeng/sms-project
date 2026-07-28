from django.db import models

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)   # e.g. "2026/2027"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    name = models.CharField(max_length=50)        # e.g. "Grade 7"
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")

    class Meta:
        unique_together = ("name", "academic_year")

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class Stream(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="streams")
    name = models.CharField(max_length=20)          # e.g. "A", "B", "North"
    class_teacher = models.ForeignKey(
        "teachers.Teacher", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="streams_managed"
    )

    class Meta:
        unique_together = ("school_class", "name")

    def __str__(self):
        return f"{self.school_class.name} {self.name}"



class TimeSlot(models.Model):

    DAYS = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    day = models.CharField(
        max_length=3,
        choices=DAYS
    )

    start_time = models.TimeField()

    end_time = models.TimeField()


    def __str__(self):
        return f"{self.day} {self.start_time} - {self.end_time}"


class TimetableEntry(models.Model):
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name="timetable_entries")
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=100)
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE, related_name="timetable_entries")
    classroom = models.CharField(max_length=50)

    class Meta:
        unique_together = ("stream", "time_slot")  # one subject per stream per slot