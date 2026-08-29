from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User


# =========================================================
# USER PROFILE / ROLE
# =========================================================

class UserProfile(models.Model):

    ROLE_CHOICES = [
        ("ADMIN", "Administrator"),
        ("MANAGER", "Manager"),
        ("STAFF", "Staff"),
        ("CASHIER", "Cashier"),
        ("INVENTORY", "Inventory Staff"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="STAFF"
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# =========================================================
# SALESPERSON
# =========================================================

class Salesperson(models.Model):

    first_name = models.CharField(
        max_length=100
    )

    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    last_name = models.CharField(
        max_length=100
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    contact_number = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    email_address = models.EmailField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):

        if not self.employee_id:

            last_salesperson = (
                Salesperson.objects
                .filter(
                    employee_id__startswith="BPOS-"
                )
                .order_by("-id")
                .first()
            )

            if (
                last_salesperson
                and last_salesperson.employee_id
            ):
                try:
                    last_number = int(
                        last_salesperson.employee_id.replace(
                            "BPOS-",
                            ""
                        )
                    )

                    next_number = last_number + 1

                except ValueError:
                    next_number = 1

            else:
                next_number = 1

            self.employee_id = (
                f"BPOS-{next_number:04d}"
            )

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        name_parts = [
            self.first_name,
            self.middle_name,
            self.last_name
        ]

        return " ".join(
            part.strip()
            for part in name_parts
            if part
        )

    def __str__(self):
        if self.employee_id:
            return f"{self.full_name} ({self.employee_id})"

        return self.full_name

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
    # SALESPERSON
    # -----------------------------------------------------

    salesperson = models.ForeignKey(
        Salesperson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
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

    # -----------------------------------------------------
    # AMOUNT DUE
    # -----------------------------------------------------

    @property
    def amount_due(self):

        amount = self.total - self.payment

        if amount < 0:
            return Decimal("0.00")

        return amount

    # -----------------------------------------------------
    # SALESPERSON NAME
    # -----------------------------------------------------

    @property
    def salesperson_name(self):

        if self.salesperson:
            return self.salesperson.full_name

        return "No salesperson"

    # -----------------------------------------------------
    # STRING
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    # Price captured at time of sale
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # -----------------------------------------------------
    # SUBTOTAL
    # -----------------------------------------------------

    # Gross line subtotal
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # -----------------------------------------------------
    # ITEM DISCOUNT
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # FINAL TOTAL
    # -----------------------------------------------------

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