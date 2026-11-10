from rest_framework.routers import DefaultRouter

from apps.library.views import BookViewSet, BorrowingRecordViewSet

router = DefaultRouter()
router.register("borrowing", BorrowingRecordViewSet, basename="borrowingrecord")
router.register("", BookViewSet, basename="book")

urlpatterns = router.urls
