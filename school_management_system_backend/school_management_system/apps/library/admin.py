from django.contrib import admin

from apps.library.models import Book, BorrowingRecord


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "isbn", "category", "available_copies", "total_copies")
    search_fields = ("title", "author", "isbn")


@admin.register(BorrowingRecord)
class BorrowingRecordAdmin(admin.ModelAdmin):
    list_display = ("book", "student", "teacher", "issued_date", "due_date", "returned_date", "status", "fine_amount")
    list_filter = ("status",)
