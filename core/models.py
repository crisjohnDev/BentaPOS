from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User


# =========================================================
# PRODUCT
# =========================================================

class Product(models.Model):

    product_model = models.CharField(
        max_length=150
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    category = models.CharField(
        max_length=100
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    qty = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.product_model

    class Meta:
        ordering = ["product_model"]
        verbose_name = "Product"
        verbose_name_plural = "Products"


# =========================================================
# INVENTORY TRANSACTION
# =========================================================

class InventoryTransaction(models.Model):

    TRANSACTION_TYPES = [
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    quantity = models.PositiveIntegerField()

    previous_qty = models.PositiveIntegerField(
        default=0
    )

    new_qty = models.PositiveIntegerField(
        default=0
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.product.product_model} - "
            f"{self.transaction_type} - "
            f"{self.quantity}"
        )

    class Meta:
        ordering = ["-created_at"]


# =========================================================
# DISCOUNT CLASS
# =========================================================

class DiscountClass(models.Model):

    CLASS_CHOICES = [
        ("A", "Class A"),
        ("B", "Class B"),
        ("C", "Class C"),
    ]

    code = models.CharField(
        max_length=1,
        choices=CLASS_CHOICES,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    max_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    open_discount = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ["code"]


# =========================================================
# SALE
# =========================================================

class Sale(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ("PAID", "Paid"),
        ("UNPAID", "Unpaid"),
        ("PARTIAL", "Partially Paid"),
    ]

    # -----------------------------------------------------
    # STAFF
    # -----------------------------------------------------

    staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_sales"
    )

    # -----------------------------------------------------
    # SALESMAN / SALESPERSON
    # -----------------------------------------------------

    salesman = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    # -----------------------------------------------------
    # DISCOUNT CLASS
    # -----------------------------------------------------

    discount_class = models.ForeignKey(
        DiscountClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
    )

    # -----------------------------------------------------
    # TOTALS
    # -----------------------------------------------------

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Class discount percentage
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Class discount amount
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Total after all discounts
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default="UNPAID"
    )

    payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    change = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # -----------------------------------------------------
    # NOTES
    # -----------------------------------------------------

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def amount_due(self):
        amount = self.total - self.payment

        if amount < 0:
            return Decimal("0.00")

        return amount

    def __str__(self):
        return f"Sale #{self.id}"

    class Meta:
        ordering = ["-created_at"]


# =========================================================
# SALE ITEM
# =========================================================

class SaleItem(models.Model):

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField()

    # Price captured at time of sale
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Gross line subtotal
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Item discount
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Final line total after item discount
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def __str__(self):
        return (
            f"{self.product.product_model} "
            f"x {self.quantity}"
        )

    class Meta:
        ordering = ["id"]