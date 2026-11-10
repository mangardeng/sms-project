from rest_framework import serializers

from apps.library.models import Book, BorrowingRecord


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "title", "author", "isbn", "category", "total_copies", "available_copies")

    def validate(self, attrs):
        total = attrs.get("total_copies", getattr(self.instance, "total_copies", None))
        available = attrs.get("available_copies", getattr(self.instance, "available_copies", None))
        if total is not None and available is not None and available > total:
            raise serializers.ValidationError("Available copies cannot exceed total copies.")
        return attrs


class BorrowingRecordSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    borrower_name = serializers.SerializerMethodField()

    class Meta:
        model = BorrowingRecord
        fields = (
            "id", "book", "book_title", "student", "teacher", "borrower_name", "issued_date",
            "due_date", "returned_date", "status", "fine_amount", "issued_by",
        )
        read_only_fields = ("issued_date", "returned_date", "status", "fine_amount", "issued_by")
        extra_kwargs = {"due_date": {"required": False}}

    def get_borrower_name(self, obj):
        borrower = obj.student or obj.teacher
        return borrower.user.get_full_name() if borrower else None

    def validate(self, attrs):
        student = attrs.get("student")
        teacher = attrs.get("teacher")
        if not student and not teacher:
            raise serializers.ValidationError("A borrowing record must have either a student or a teacher.")
        if student and teacher:
            raise serializers.ValidationError("A borrowing record cannot have both a student and a teacher.")
        return attrs

    def create(self, validated_data):
        book = validated_data["book"]
        if book.available_copies < 1:
            raise serializers.ValidationError("No available copies of this book.")
        book.available_copies -= 1
        book.save(update_fields=["available_copies"])
        return super().create(validated_data)
