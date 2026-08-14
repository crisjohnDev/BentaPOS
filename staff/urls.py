from django.urls import path

from . import views


urlpatterns = [

    # Staff POS
    path(
        "dashboard/",
        views.staff_dashboard,
        name="staff-dashboard"
    ),

    # Process sale
    path(
        "complete-sale/",
        views.complete_sale,
        name="complete-sale"
    ),

    # Receipt
    path(
        "staff/sale/<int:sale_id>/receipt/",
        views.sale_receipt,
        name="sale-receipt"
    ),
    path(
        "staff/transactions/",
        views.transaction_history,
        name="transaction-history"
    ),
    path(
        "inventory/",
        views.inventory,
        name="staff-inventory"
    ),

]