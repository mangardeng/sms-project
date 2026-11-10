from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.fees.views import (
    ArrearsView,
    CarryForwardViewSet,
    ExpenseViewSet,
    FeeBalanceView,
    FeeStructureViewSet,
    FinanceSummaryView,
    OtherIncomeViewSet,
    PaymentViewSet,
    SponsorshipViewSet,
    SponsorViewSet,
    StaffSalaryViewSet,
)

router = DefaultRouter()
router.register("structures", FeeStructureViewSet, basename="feestructure")
router.register("payments", PaymentViewSet, basename="payment")
router.register("balance", FeeBalanceView, basename="fee-balance")
router.register("sponsors", SponsorViewSet, basename="sponsor")
router.register("sponsorships", SponsorshipViewSet, basename="sponsorship")
router.register("carry-forward", CarryForwardViewSet, basename="carryforward")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("other-income", OtherIncomeViewSet, basename="otherincome")
router.register("salaries", StaffSalaryViewSet, basename="staffsalary")

urlpatterns = [
    path("finance/summary/", FinanceSummaryView.as_view(), name="finance-summary"),
    path("finance/arrears/", ArrearsView.as_view(), name="finance-arrears"),
    path("", include(router.urls)),
]
