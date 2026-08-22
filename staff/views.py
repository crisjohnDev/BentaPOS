from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import (
    Product,
    InventoryTransaction,
    DiscountClass,
    Sale,
    SaleItem,
)


# =========================================================
# STAFF CHECK
# =========================================================

def is_staff(user):
    return user.is_authenticated and user.is_staff


# =========================================================
# DECIMAL HELPER
# =========================================================

def decimal_value(value, default="0.00"):

    try:
        return Decimal(str(value or default))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid monetary value.")


# =========================================================
# MONEY ROUNDING
# =========================================================

def money(value):

    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# =========================================================
# STAFF DASHBOARD / POS
# =========================================================

@login_required
@user_passes_test(is_staff)
def staff_dashboard(request):

    # -----------------------------------------------------
    # ENSURE DISCOUNT CLASSES EXIST
    # -----------------------------------------------------

    DiscountClass.objects.update_or_create(
        code="A",
        defaults={
            "name": "Class A",
            "max_discount": Decimal("0.00"),
            "open_discount": False,
        }
    )

    DiscountClass.objects.update_or_create(
        code="B",
        defaults={
            "name": "Class B",
            "max_discount": Decimal("10.00"),
            "open_discount": False,
        }
    )

    DiscountClass.objects.update_or_create(
        code="C",
        defaults={
            "name": "Class C",
            "max_discount": Decimal("100.00"),
            "open_discount": True,
        }
    )

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    products = Product.objects.filter(
        qty__gt=0
    ).order_by(
        "product_model"
    )

    if search:

        products = products.filter(
            Q(product_model__icontains=search)
            |
            Q(description__icontains=search)
            |
            Q(category__icontains=search)
        )

    # -----------------------------------------------------
    # DISCOUNTS
    # -----------------------------------------------------

    discount_classes = DiscountClass.objects.all().order_by(
        "code"
    )

    return render(
        request,
        "staff/staff_dashboard.html",
        {
            "products": products,
            "discount_classes": discount_classes,
            "search": search,
        }
    )


# =========================================================
# COMPLETE SALE
# =========================================================

@login_required
@user_passes_test(is_staff)
def complete_sale(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request."
            },
            status=400
        )

    try:

        # =================================================
        # BASIC INFORMATION
        # =================================================

        salesman = (
            request.POST.get(
                "salesman_name",
                ""
            ).strip()
        )

        payment_status_raw = (
            request.POST.get(
                "payment_status",
                "paid"
            ).strip().lower()
        )

        discount_class_id = (
            request.POST.get(
                "discount_class"
            )
        )

        discount_percent = decimal_value(
            request.POST.get(
                "discount_percent",
                "0"
            )
        )

        payment = decimal_value(
            request.POST.get(
                "payment",
                "0"
            )
        )

    except ValueError as error:

        return JsonResponse(
            {
                "success": False,
                "message": str(error)
            },
            status=400
        )

    # =========================================================
    # SALESMAN
    # =========================================================

    if not salesman:

        return JsonResponse(
            {
                "success": False,
                "message": "Please enter the salesperson name."
            },
            status=400
        )

    # =========================================================
    # PAYMENT STATUS
    # =========================================================

    if payment_status_raw == "paid":

        payment_status = "PAID"

    elif payment_status_raw == "unpaid":

        payment_status = "UNPAID"

    elif payment_status_raw == "partial":

        payment_status = "PARTIAL"

    else:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid payment status."
            },
            status=400
        )

    # =========================================================
    # DISCOUNT CLASS
    # =========================================================

    discount_class = None

    if discount_class_id:

        discount_class = get_object_or_404(
            DiscountClass,
            id=discount_class_id
        )

    # =========================================================
    # VALIDATE DISCOUNT
    # =========================================================

    if discount_percent < 0:

        return JsonResponse(
            {
                "success": False,
                "message": "Discount cannot be negative."
            },
            status=400
        )

    if discount_class:

        maximum = discount_class.max_discount

        if discount_percent > maximum:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"{discount_class.name} allows "
                        f"up to {maximum:.2f}% discount."
                    )
                },
                status=400
            )

    else:

        if discount_percent != 0:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "A discount class is required "
                        "for a discount."
                    )
                },
                status=400
            )

    # =========================================================
    # PAYMENT VALIDATION
    # =========================================================

    if payment < 0:

        return JsonResponse(
            {
                "success": False,
                "message": "Payment cannot be negative."
            },
            status=400
        )

    # =========================================================
    # READ CART
    # =========================================================

    items = []

    index = 0

    while True:

        product_id = request.POST.get(
            f"items[{index}][product_id]"
        )

        quantity_raw = request.POST.get(
            f"items[{index}][quantity]"
        )

        item_discount_raw = request.POST.get(
            f"items[{index}][discount_percent]",
            "0"
        )

        if not product_id:

            break

        try:

            quantity = int(
                quantity_raw
            )

            item_discount = decimal_value(
                item_discount_raw
            )

        except (ValueError, TypeError, InvalidOperation):

            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid cart item."
                },
                status=400
            )

        if quantity <= 0:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Quantity must be greater than zero."
                },
                status=400
            )

        if item_discount < 0 or item_discount > 100:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Item discount must be between "
                        "0% and 100%."
                    )
                },
                status=400
            )

        try:

            product_id = int(product_id)

        except (ValueError, TypeError):

            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid product."
                },
                status=400
            )

        items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "item_discount": item_discount,
            }
        )

        index += 1

    # =========================================================
    # CART REQUIRED
    # =========================================================

    if not items:

        return JsonResponse(
            {
                "success": False,
                "message": "No products were added."
            },
            status=400
        )

    # =========================================================
    # PROCESS SALE
    # =========================================================

    try:

        with transaction.atomic():

            # -------------------------------------------------
            # LOCK PRODUCTS
            # -------------------------------------------------

            locked_items = []

            for cart_item in items:

                product = (
                    Product.objects
                    .select_for_update()
                    .get(
                        id=cart_item["product_id"]
                    )
                )

                quantity = cart_item["quantity"]

                if product.qty < quantity:

                    raise ValueError(
                        f"Not enough stock for "
                        f"{product.product_model}. "
                        f"Available: {product.qty}"
                    )

                locked_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "item_discount": (
                            cart_item["item_discount"]
                        ),
                    }
                )

            # -------------------------------------------------
            # CALCULATE EVERYTHING SERVER SIDE
            # -------------------------------------------------

            sale_subtotal = Decimal("0.00")

            item_discount_total = Decimal("0.00")

            calculated_items = []

            for item in locked_items:

                product = item["product"]

                quantity = item["quantity"]

                item_discount_percent = (
                    item["item_discount"]
                )

                gross_subtotal = money(
                    product.price * quantity
                )

                item_discount_amount = money(
                    gross_subtotal
                    *
                    (
                        item_discount_percent
                        /
                        Decimal("100")
                    )
                )

                item_total = money(
                    gross_subtotal
                    -
                    item_discount_amount
                )

                sale_subtotal += gross_subtotal

                item_discount_total += (
                    item_discount_amount
                )

                calculated_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "price": product.price,
                        "subtotal": gross_subtotal,
                        "discount_percent": (
                            item_discount_percent
                        ),
                        "discount_amount": (
                            item_discount_amount
                        ),
                        "total": item_total,
                    }
                )

            sale_subtotal = money(
                sale_subtotal
            )

            item_discount_total = money(
                item_discount_total
            )

            # -------------------------------------------------
            # CLASS DISCOUNT
            #
            # Applied AFTER item discounts.
            # -------------------------------------------------

            amount_after_item_discount = money(
                sale_subtotal
                -
                item_discount_total
            )

            class_discount_amount = money(
                amount_after_item_discount
                *
                (
                    discount_percent
                    /
                    Decimal("100")
                )
            )

            final_total = money(
                amount_after_item_discount
                -
                class_discount_amount
            )

            # -------------------------------------------------
            # PAYMENT
            # -------------------------------------------------

            if payment_status == "PAID":

                if payment < final_total:

                    raise ValueError(
                        "Cash received is not enough."
                    )

                actual_payment = payment

                actual_change = money(
                    payment - final_total
                )

            elif payment_status == "UNPAID":

                actual_payment = Decimal("0.00")

                actual_change = Decimal("0.00")

            else:

                # PARTIAL
                if payment <= 0:

                    raise ValueError(
                        "Partial payment must be greater than zero."
                    )

                if payment >= final_total:

                    # If they pay the full amount,
                    # automatically make it PAID.
                    payment_status = "PAID"

                    actual_payment = payment

                    actual_change = money(
                        payment - final_total
                    )

                else:

                    actual_payment = payment

                    actual_change = Decimal("0.00")

            # -------------------------------------------------
            # TOTAL DISCOUNT STORED ON SALE
            #
            # This contains BOTH:
            # item discounts + class discount.
            # -------------------------------------------------

            total_discount_amount = money(
                item_discount_total
                +
                class_discount_amount
            )

            # -------------------------------------------------
            # CREATE SALE
            # -------------------------------------------------

            sale = Sale.objects.create(

                staff=request.user,

                salesman=salesman,

                discount_class=discount_class,

                subtotal=sale_subtotal,

                discount_percent=discount_percent,

                discount_amount=total_discount_amount,

                total=final_total,

                payment_status=payment_status,

                payment=actual_payment,

                change=actual_change,
            )

            # -------------------------------------------------
            # CREATE SALE ITEMS
            # -------------------------------------------------

            for item in calculated_items:

                product = item["product"]

                quantity = item["quantity"]

                # ---------------------------------------------
                # SALE ITEM
                # ---------------------------------------------

                SaleItem.objects.create(

                    sale=sale,

                    product=product,

                    quantity=quantity,

                    price=item["price"],

                    subtotal=item["subtotal"],

                    discount_percent=(
                        item["discount_percent"]
                    ),

                    discount_amount=(
                        item["discount_amount"]
                    ),

                    total=item["total"],
                )

                # ---------------------------------------------
                # STOCK
                # ---------------------------------------------

                previous_qty = product.qty

                product.qty = (
                    product.qty -
                    quantity
                )

                product.save(
                    update_fields=[
                        "qty",
                        "updated_at",
                    ]
                )

                # ---------------------------------------------
                # INVENTORY TRANSACTION
                # ---------------------------------------------

                InventoryTransaction.objects.create(

                    product=product,

                    transaction_type="OUT",

                    quantity=quantity,

                    previous_qty=previous_qty,

                    new_qty=product.qty,

                    reference=f"SALE-{sale.id}",

                    notes=(
                        f"Sale #{sale.id} - "
                        f"{product.product_model}"
                    ),

                    created_by=request.user,
                )

    except Product.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "One of the selected products no longer exists."
            },
            status=400
        )

    except ValueError as error:

        return JsonResponse(
            {
                "success": False,
                "message": str(error)
            },
            status=400
        )

    except Exception as error:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    f"Unable to complete sale: {error}"
                )
            },
            status=500
        )

    # =========================================================
    # RECEIPT ITEMS
    # =========================================================

    receipt_items = []

    for item in (
        sale.items
        .select_related("product")
        .all()
    ):

        receipt_items.append(
            {
                "name": item.product.product_model,
                "quantity": item.quantity,
                "price": f"{item.price:.2f}",
                "subtotal": f"{item.subtotal:.2f}",
                "discount_percent": (
                    f"{item.discount_percent:.2f}"
                ),
                "discount_amount": (
                    f"{item.discount_amount:.2f}"
                ),
                "total": f"{item.total:.2f}",
            }
        )

    # =========================================================
    # JSON RESPONSE
    # =========================================================

    return JsonResponse(
        {
            "success": True,

            "sale_id": sale.id,

            "date": sale.created_at.strftime(
                "%b %d, %Y %I:%M %p"
            ),

            "staff": (
                request.user.get_full_name()
                or request.user.username
            ),

            "salesman": sale.salesman or "",

            "payment_status": sale.payment_status,

            "discount_class": (
                discount_class.name
                if discount_class
                else "No Discount"
            ),

            "discount_percent": (
                f"{sale.discount_percent:.2f}"
            ),

            "subtotal": (
                f"{sale.subtotal:.2f}"
            ),

            "discount_amount": (
                f"{sale.discount_amount:.2f}"
            ),

            "total": (
                f"{sale.total:.2f}"
            ),

            "payment": (
                f"{sale.payment:.2f}"
            ),

            "change": (
                f"{sale.change:.2f}"
            ),

            "amount_due": (
                f"{sale.amount_due:.2f}"
            ),

            "items": receipt_items,
        }
    )


# =========================================================
# SALE RECEIPT
# =========================================================

@login_required
@user_passes_test(is_staff)
def sale_receipt(request, sale_id):

    sale = get_object_or_404(
        Sale.objects
        .select_related(
            "staff",
            "discount_class"
        )
        .prefetch_related(
            "items__product"
        ),
        id=sale_id
    )

    return render(
        request,
        "staff/receipt.html",
        {
            "sale": sale,
        }
    )


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@login_required
@user_passes_test(is_staff)
def transaction_history(request):

    # =========================================================
    # GET SALES
    # =========================================================

    sales = (
        Sale.objects
        .filter(
            staff=request.user
        )
        .select_related(
            "staff",
            "discount_class"
        )
        .prefetch_related(
            "items__product"
        )
        .order_by(
            "-created_at"
        )
    )

    # =========================================================
    # SEARCH
    #
    # Search:
    # - Sale ID
    # - Salesperson
    # - Product
    # - Staff username
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        if search.isdigit():

            sales = sales.filter(
                id=int(search)
            )

        else:

            sales = sales.filter(
                Q(
                    salesman__icontains=search
                )
                |
                Q(
                    staff__username__icontains=search
                )
                |
                Q(
                    staff__first_name__icontains=search
                )
                |
                Q(
                    staff__last_name__icontains=search
                )
                |
                Q(
                    items__product__product_model__icontains=search
                )
            ).distinct()

    # =========================================================
    # DATE FILTER
    # =========================================================

    selected_date = request.GET.get(
        "date",
        ""
    ).strip()

    if selected_date:

        sales = sales.filter(
            created_at__date=selected_date
        )

    # =========================================================
    # PAYMENT STATUS FILTER
    #
    # PAID
    # UNPAID
    # PARTIAL
    # =========================================================

    selected_status = request.GET.get(
        "status",
        ""
    ).strip().upper()

    if selected_status in [
        "PAID",
        "UNPAID",
        "PARTIAL",
    ]:

        sales = sales.filter(
            payment_status=selected_status
        )

    # =========================================================
    # TOTAL TRANSACTIONS
    # =========================================================

    total_transactions = sales.count()

    # =========================================================
    # TOTAL SALES
    # =========================================================

    total_sales = (
        sales.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # TOTAL ITEMS
    # =========================================================

    total_items = 0

    for sale in sales:

        total_items += sum(
            item.quantity
            for item in sale.items.all()
        )

    # =========================================================
    # TODAY'S TRANSACTIONS
    # =========================================================

    today = timezone.localdate()

    today_transactions = (
        Sale.objects
        .filter(
            staff=request.user,
            created_at__date=today
        )
        .count()
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        sales,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    transactions = paginator.get_page(
        page_number
    )

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "staff/transaction_history.html",
        {
            "transactions": transactions,

            "total_transactions": (
                total_transactions
            ),

            "total_sales": (
                total_sales
            ),

            "total_items": (
                total_items
            ),

            "today_transactions": (
                today_transactions
            ),

            "selected_status": (
                selected_status
            ),
        }
    )

# =========================================================
# INVENTORY
# =========================================================

@login_required
@user_passes_test(is_staff)
def inventory(request):

    products = (
        Product.objects
        .all()
        .order_by(
            "product_model"
        )
    )

    return render(
        request,
        "staff/inventory.html",
        {
            "products": products,
        }
    )