from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='admin-dashboard'),
    path("users/", views.staff_list, name="staff_list"),
    path('users/add/', views.add_staff, name='add-user'),
    path("users/<int:user_id>/edit/", views.edit_user, name="edit-user"),
    path("users/<int:user_id>/delete/", views.delete_user, name="delete-user"),
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.add_product, name="add-product"),
    path("products/<int:product_id>/edit/", views.edit_product, name="edit-product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="delete-product"),
    path("products/import/", views.import_products, name="import-products"),
    path("inventory/", views.inventory, name="inventory"),
    path("inventory/stock-in/", views.stock_in, name="stock-in"),
    path("inventory/history/", views.inventory_history, name="inventory-history"),
    path("inventory/<int:product_id>/history/", views.product_inventory_history, name="product-inventory-history"),
    path(
        "pos/",
        views.admin_pos,
        name="admin-pos"
    ),

    path(
        "pos/<int:sale_id>/",
        views.admin_pos_detail,
        name="admin-pos-detail"
    ),
    path(
        "sales/",
        views.sales,
        name="sales"
    ),

    path(
        "sales/<int:sale_id>/",
        views.sale_detail,
        name="sale-detail"
    ),
    path(
        "reports/",
        views.reports,
        name="reports"
    ),
]
