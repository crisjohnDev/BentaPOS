from django.contrib import admin
from django.utils.html import format_html

from .models import (
    UserProfile,
    Salesperson,
    DiscountClass,
    Client,
    Product,
    InventoryTransaction,
    Sale,
    SaleItem,
)


# =========================================================
# USER PROFILE
# =========================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "role",
        "get_full_name",
        "get_email",
    )

    list_filter = (
        "role",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    autocomplete_fields = (
        "user",
    )

    list_per_page = 25

    @admin.display(
        description="Name",
        ordering="user__first_name",
    )
    def get_full_name(self, obj):

        full_name = obj.user.get_full_name()

        return full_name or "-"

    @admin.display(
        description="Email",
        ordering="user__email",
    )
    def get_email(self, obj):

        return obj.user.email or "-"


# =========================================================
# SALESPERSON
# =========================================================

@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):

    list_display = (
        "display_full_name",
        "contact_number",
        "email_address",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "first_name",
        "middle_name",
        "last_name",
        "contact_number",
        "email_address",
    )

    ordering = (
        "last_name",
        "first_name",
    )

    list_per_page = 25

    date_hierarchy = "created_at"

    @admin.display(
        description="Salesperson",
        ordering="last_name",
    )
    def display_full_name(self, obj):

        return obj.full_name


# =========================================================
# DISCOUNT CLASS
# =========================================================

@admin.register(DiscountClass)
class DiscountClassAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "max_discount",
        "open_discount",
    )

    list_filter = (
        "open_discount",
        "code",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )

    list_per_page = 25


# =========================================================
# CLIENT
# =========================================================

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "organization",
        "salesperson",
        "discount_class",
        "contact_number",
        "email_address",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "salesperson",
        "discount_class",
        "created_at",
    )

    search_fields = (
        "first_name",
        "middle_name",
        "last_name",
        "organization",
        "address",
        "contact_number",
        "email_address",
        "salesperson__first_name",
        "salesperson__middle_name",
        "salesperson__last_name",
    )

    autocomplete_fields = (
        "salesperson",
        "discount_class",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "last_name",
        "first_name",
    )

    list_per_page = 25

    date_hierarchy = "created_at"

    fieldsets = (

        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "middle_name",
                    "last_name",
                    "organization",
                )
            },
        ),

        (
            "Contact Information",
            {
                "fields": (
                    "address",
                    "contact_number",
                    "email_address",
                )
            },
        ),

        (
            "Sales & Discount",
            {
                "fields": (
                    "salesperson",
                    "discount_class",
                )
            },
        ),

        (
            "Business Permit",
            {
                "fields": (
                    "business_permit",
                )
            },
        ),

        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "created_at",
                )
            },
        ),

    )


# =========================================================
# PRODUCT
# =========================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "product_image",
        "product_model",
        "category",
        "price",
        "qty",
        "stock_status",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "category",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "product_model",
        "description",
        "category",
    )

    readonly_fields = (
        "product_image_preview",
        "created_at",
        "updated_at",
    )

    ordering = (
        "product_model",
    )

    list_per_page = 25

    fieldsets = (

        (
            "Product Information",
            {
                "fields": (
                    "product_model",
                    "description",
                    "category",
                    "price",
                    "qty",
                )
            },
        ),

        (
            "Product Image",
            {
                "fields": (
                    "image",
                    "product_image_preview",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),

    )

    # =====================================================
    # IMAGE IN PRODUCT LIST
    # =====================================================

    @admin.display(
        description="Image",
    )
    def product_image(self, obj):

        if obj.image:

            return format_html(
                '<img src="{}" '
                'style="width:50px; height:50px; '
                'object-fit:cover; border-radius:6px; '
                'border:1px solid #ddd;">',
                obj.image.url
            )

        return format_html(
            '<div style="'
            'width:50px;'
            'height:50px;'
            'display:flex;'
            'align-items:center;'
            'justify-content:center;'
            'background:#f5f5f5;'
            'border:1px solid #ddd;'
            'border-radius:6px;'
            'font-size:10px;'
            'color:#999;'
            'text-align:center;'
            '">No Image</div>'
        )

    # =====================================================
    # IMAGE PREVIEW IN PRODUCT EDIT PAGE
    # =====================================================

    @admin.display(
        description="Current Image",
    )
    def product_image_preview(self, obj):

        if obj and obj.image:

            return format_html(
                '<div style="margin-top:10px;">'
                '<img src="{}" '
                'style="'
                'width:180px;'
                'height:180px;'
                'object-fit:cover;'
                'border:1px solid #ddd;'
                'border-radius:8px;'
                'display:block;'
                '">'
                '</div>',
                obj.image.url
            )

        return format_html(
            '<div style="'
            'width:180px;'
            'height:180px;'
            'display:flex;'
            'align-items:center;'
            'justify-content:center;'
            'background:#f5f5f5;'
            'border:1px solid #ddd;'
            'border-radius:8px;'
            'color:#999;'
            '">'
            'No Image'
            '</div>'
        )

    # =====================================================
    # STOCK STATUS
    # =====================================================

    @admin.display(
        description="Stock",
        ordering="qty",
    )
    def stock_status(self, obj):

        if obj.qty == 0:
            return "Out of Stock"

        if obj.qty <= 10:
            return "Low Stock"

        return "In Stock"


# =========================================================
# INVENTORY TRANSACTION
# =========================================================

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "transaction_type",
        "quantity",
        "previous_qty",
        "new_qty",
        "reference",
        "created_by",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    search_fields = (
        "product__product_model",
        "reference",
        "notes",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
    )

    autocomplete_fields = (
        "product",
        "created_by",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    date_hierarchy = "created_at"


# =========================================================
# SALE ITEM INLINE
# =========================================================

class SaleItemInline(admin.TabularInline):

    model = SaleItem

    extra = 0

    autocomplete_fields = (
        "product",
    )

    fields = (
        "product",
        "quantity",
        "price",
        "subtotal",
        "discount_percent",
        "discount_amount",
        "total",
    )

    readonly_fields = (
        "subtotal",
        "discount_amount",
        "total",
    )


# =========================================================
# SALE
# =========================================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "created_at",
        "client_name_display",
        "salesperson_name_display",
        "staff",
        "subtotal",
        "discount_percent",
        "discount_amount",
        "total",
        "payment",
        "amount_due_display",
        "payment_status",
    )

    list_filter = (
        "payment_status",
        "discount_class",
        "salesperson",
        "created_at",
    )

    search_fields = (
        "id",
        "client__first_name",
        "client__middle_name",
        "client__last_name",
        "client__organization",
        "salesperson__first_name",
        "salesperson__middle_name",
        "salesperson__last_name",
        "staff__username",
        "staff__first_name",
        "staff__last_name",
        "notes",
    )

    autocomplete_fields = (
        "staff",
        "salesperson",
        "client",
        "discount_class",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = (
        SaleItemInline,
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    date_hierarchy = "created_at"

    fieldsets = (

        (
            "Sale Information",
            {
                "fields": (
                    "staff",
                    "salesperson",
                    "client",
                    "discount_class",
                )
            },
        ),

        (
            "Sale Totals",
            {
                "fields": (
                    "subtotal",
                    "discount_percent",
                    "discount_amount",
                    "total",
                )
            },
        ),

        (
            "Payment",
            {
                "fields": (
                    "payment_status",
                    "payment",
                    "change",
                )
            },
        ),

        (
            "Additional Information",
            {
                "fields": (
                    "notes",
                    "created_at",
                )
            },
        ),

    )

    @admin.display(
        description="Client",
        ordering="client__last_name",
    )
    def client_name_display(self, obj):

        return obj.client_name

    @admin.display(
        description="Salesperson",
        ordering="salesperson__last_name",
    )
    def salesperson_name_display(self, obj):

        return obj.salesperson_name

    @admin.display(
        description="Amount Due",
        ordering="total",
    )
    def amount_due_display(self, obj):

        return obj.amount_due


# =========================================================
# SALE ITEM
# =========================================================

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):

    list_display = (
        "sale",
        "product",
        "quantity",
        "price",
        "subtotal",
        "discount_percent",
        "discount_amount",
        "total",
    )

    list_filter = (
        "sale__payment_status",
        "sale__created_at",
    )

    search_fields = (
        "product__product_model",
        "sale__client__first_name",
        "sale__client__last_name",
        "sale__client__organization",
    )

    autocomplete_fields = (
        "sale",
        "product",
    )

    readonly_fields = (
        "subtotal",
        "discount_amount",
        "total",
    )

    ordering = (
        "-sale__created_at",
        "id",
    )

    list_per_page = 25