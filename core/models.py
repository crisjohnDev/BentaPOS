from django.db import models

class Product(models.Model):

    # Product name/model
    product_model = models.CharField(
        max_length=150
    )

    # Product description
    description = models.TextField(
        blank=True,
        null=True
    )

    # Product category
    category = models.CharField(
        max_length=100
    )

    # Product selling price
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Available quantity
    qty = models.PositiveIntegerField(
        default=0
    )

    # Date created
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Date updated
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.product_model

    class Meta:
        ordering = ["product_model"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

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
        "auth.User",
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

class Sale(models.Model):

    staff = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True
    )

    discount_class = models.ForeignKey(
        DiscountClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    change = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Sale #{self.id}"


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

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.product.product_model} x {self.quantity}"