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
        return (
            f"{self.user.username} - "
            f"{self.get_role_display()}"
        )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class AdminPortalLock(models.Model):
    locked = models.BooleanField(default=False)

    session_key = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    last_activity = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Admin Portal Lock"

    class Meta:
        verbose_name = "Admin Portal Lock"
        verbose_name_plural = "Admin Portal Locks"


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

    # =====================================================
    # FULL NAME
    # =====================================================

    @property
    def full_name(self):
        name_parts = [
            self.first_name
        ]

        if self.middle_name:
            name_parts.append(
                self.middle_name
            )

        name_parts.append(
            self.last_name
        )

        return " ".join(name_parts)

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.full_name

    class Meta:

        ordering = [
            "last_name",
            "first_name"
        ]

        verbose_name = "Salesperson"
        verbose_name_plural = "Salespersons"


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
        default=Decimal("0.00")
    )

    open_discount = models.BooleanField(
        default=False
    )

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.name}"
        )

    class Meta:
        ordering = ["code"]
        verbose_name = "Discount Class"
        verbose_name_plural = "Discount Classes"


# =========================================================
# CLIENT
# =========================================================

class Client(models.Model):

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

    organization = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    address = models.TextField(
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

    business_permit = models.FileField(
        upload_to="business_permits/", 
        blank=True, 
        null=True 
    )

    # =====================================================
    # SALESPERSON
    # =====================================================

    salesperson = models.ForeignKey(
        Salesperson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients"
    )

    # =====================================================
    # DISCOUNT CLASS
    # =====================================================

    #
    # NULL = Client does not receive a discount.
    #
    # Class A = Maximum 0%
    # Class B = Maximum 10%
    # Class C = Maximum 100%
    #

    discount_class = models.ForeignKey(
        DiscountClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients"
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # =====================================================
    # FULL NAME
    # =====================================================

    @property
    def full_name(self):
        name_parts = [
            self.first_name
        ]

        if self.middle_name:
            name_parts.append(
                self.middle_name
            )

        name_parts.append(
            self.last_name
        )

        return " ".join(name_parts)

    # =====================================================
    # DISCOUNT STATUS
    # =====================================================

    @property
    def has_discount(self):
        return self.discount_class is not None

    # =====================================================
    # SALESPERSON STATUS
    # =====================================================

    @property
    def has_salesperson(self):
        return self.salesperson is not None

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.full_name

    class Meta:

        ordering = [
            "last_name",
            "first_name"
        ]

        verbose_name = "Client"
        verbose_name_plural = "Clients"


# =========================================================
# PRODUCT
# =========================================================

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

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # =====================================================
    # CURRENT STOCK
    # =====================================================

    qty = models.PositiveIntegerField(
        default=0
    )

    # =====================================================
    # LOW STOCK THRESHOLD
    # =====================================================
    #
    # When current qty is equal to or below this value,
    # the product is considered Low Stock.
    #
    # Example:
    #
    # qty = 10
    # threshold = 10
    # -> Low Stock
    #
    # qty = 11
    # threshold = 10
    # -> In Stock
    #
    # qty = 0
    # -> Out of Stock
    #
    # =====================================================

    low_stock_threshold = models.PositiveIntegerField(
        default=10
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # STOCK VALUE
    # =====================================================

    @property
    def stock_value(self):

        return self.price * self.qty

    # =====================================================
    # STOCK STATUS
    # =====================================================

    @property
    def stock_status(self):

        if self.qty == 0:
            return "out"

        if self.qty <= self.low_stock_threshold:
            return "low"

        return "in"

    # =====================================================
    # STOCK STATUS DISPLAY
    # =====================================================

    @property
    def stock_status_display(self):

        if self.stock_status == "out":
            return "Out of Stock"

        if self.stock_status == "low":
            return "Low Stock"

        return "In Stock"

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.product_model

    class Meta:

        ordering = [
            "product_model"
        ]

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
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"


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
    # CLIENT
    # -----------------------------------------------------
    #
    # Client and Salesperson are independent.
    #
    # A Sale can have:
    #
    # - Staff
    # - Salesperson
    # - Client
    #
    # But Client is NOT related to Salesperson.
    #
    # -----------------------------------------------------

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales"
    )

    # -----------------------------------------------------
    # DISCOUNT CLASS USED
    # -----------------------------------------------------
    #
    # This stores the discount class actually used for
    # this particular transaction.
    #
    # Client.discount_class = current client eligibility
    #
    # Sale.discount_class = discount class used in this sale
    #
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

    # Total discount amount

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # Final total after all discounts

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

    # -----------------------------------------------------
    # CREATED
    # -----------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # -----------------------------------------------------
    # AMOUNT DUE
    # -----------------------------------------------------

    @property
    def amount_due(self):

        amount = (
            self.total -
            self.payment
        )

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
    # CLIENT NAME
    # -----------------------------------------------------

    @property
    def client_name(self):

        if self.client:

            return self.client.full_name

        return "No Client"

    # -----------------------------------------------------
    # CLIENT ORGANIZATION
    # -----------------------------------------------------

    @property
    def client_organization(self):

        if self.client:

            return (
                self.client.organization
                or ""
            )

        return ""

    # -----------------------------------------------------
    # DISCOUNT ALLOWED
    # -----------------------------------------------------

    @property
    def discount_allowed(self):

        return (
            self.client is not None
            and self.client.discount_class is not None
        )

    # -----------------------------------------------------
    # STRING
    # -----------------------------------------------------

    def __str__(self):
        return f"Sale #{self.id}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sale"
        verbose_name_plural = "Sales"


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
    #
    # Price captured at time of sale.
    #
    # -----------------------------------------------------

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # -----------------------------------------------------
    # SUBTOTAL
    # -----------------------------------------------------
    #
    # Gross line subtotal before item discount.
    #
    # -----------------------------------------------------

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

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # -----------------------------------------------------
    # STRING
    # -----------------------------------------------------

    def __str__(self):

        return (
            f"{self.product.product_model} "
            f"x {self.quantity}"
        )

    class Meta:
        ordering = ["id"]
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"