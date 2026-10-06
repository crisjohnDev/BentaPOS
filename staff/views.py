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
    Salesperson,
    Client
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

    # =====================================================
    # ENSURE DISCOUNT CLASSES EXIST
    # =====================================================

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


    # =====================================================
    # PRODUCTS
    # =====================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    products = (
        Product.objects
        .filter(qty__gt=0)
        .order_by("product_model")
    )

    if search:

        products = products.filter(
            Q(product_model__icontains=search)
            |
            Q(description__icontains=search)
            |
            Q(category__icontains=search)
        )


    # =====================================================
    # DISCOUNT CLASSES
    # =====================================================

    discount_classes = (
        DiscountClass.objects
        .all()
        .order_by("code")
    )


    # =====================================================
    # SALESPERSONS
    # =====================================================

    salespersons = (
        Salesperson.objects
        .filter(is_active=True)
        .order_by(
            "first_name",
            "last_name"
        )
    )


    # =====================================================
    # CLIENTS
    # =====================================================

    clients = (
        Client.objects
        .filter(is_active=True)
        .select_related(
            "salesperson",
            "discount_class"
        )
        .order_by(
            "last_name",
            "first_name"
        )
    )


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "staff/staff_dashboard.html",
        {
            "products": products,
            "discount_classes": discount_classes,
            "salespersons": salespersons,
            "clients": clients,
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

        # =====================================================
        # BASIC INFORMATION
        # =====================================================

        salesperson_id = request.POST.get(
            "salesperson",
            ""
        ).strip()

        client_id = request.POST.get(
            "client",
            ""
        ).strip()

        discount_class_id = request.POST.get(
            "discount_class",
            ""
        ).strip()

        payment_status_raw = request.POST.get(
            "payment_status",
            "PAID"
        ).strip().upper()

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

        # =====================================================
        # DEBUG
        # =====================================================

        print("========== COMPLETE SALE DEBUG ==========")
        print("salesperson:", salesperson_id)
        print("client:", client_id)
        print("discount_class:", discount_class_id)
        print("payment_status:", payment_status_raw)
        print("discount_percent:", discount_percent)
        print("payment:", payment)
        print("product_ids:", request.POST.getlist("product_ids[]"))
        print("quantities:", request.POST.getlist("quantities[]"))
        print("prices:", request.POST.getlist("prices[]"))
        print(
            "item_discount_percentages:",
            request.POST.getlist("item_discount_percentages[]")
        )
        print("=========================================")

        # =====================================================
        # SALESPERSON
        # =====================================================

        if not salesperson_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Please select a salesperson."
                },
                status=400
            )

        try:

            salesperson = Salesperson.objects.get(
                id=int(salesperson_id),
                is_active=True
            )

        except (
            Salesperson.DoesNotExist,
            ValueError,
            TypeError
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": "Selected salesperson does not exist."
                },
                status=400
            )

        # =====================================================
        # CLIENT
        # =====================================================

        client = None

        if client_id:

            try:

                client = Client.objects.get(
                    id=int(client_id),
                    is_active=True
                )

            except (
                Client.DoesNotExist,
                ValueError,
                TypeError
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "message": "Selected client does not exist."
                    },
                    status=400
                )

        # =====================================================
        # DISCOUNT CLASS
        # =====================================================

        discount_class = None

        if discount_class_id:

            try:

                discount_class = DiscountClass.objects.get(
                    id=int(discount_class_id)
                )

            except (
                DiscountClass.DoesNotExist,
                ValueError,
                TypeError
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "message": "Selected discount class does not exist."
                    },
                    status=400
                )

        # =====================================================
        # DISCOUNT VALIDATION
        # =====================================================

        if discount_percent < 0:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Discount cannot be negative."
                },
                status=400
            )

        # No client = no client discount

        if not client and discount_percent != 0:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Please select a client before applying "
                        "a client discount."
                    )
                },
                status=400
            )

        # Discount percentage requires discount class

        if discount_percent != 0 and not discount_class:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Please select a discount class before "
                        "applying a client discount."
                    )
                },
                status=400
            )

        # Validate maximum discount

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

        # =====================================================
        # PAYMENT STATUS
        # =====================================================

        if payment_status_raw == "PAID":

            payment_status = "PAID"

        elif payment_status_raw == "PARTIAL":

            payment_status = "PARTIAL"

        elif payment_status_raw == "UNPAID":

            payment_status = "UNPAID"

        else:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid payment status."
                },
                status=400
            )

        # =====================================================
        # PAYMENT BASIC VALIDATION
        # =====================================================

        if payment < 0:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Payment cannot be negative."
                },
                status=400
            )

        # =====================================================
        # READ CART
        #
        # Frontend sends:
        #
        # product_ids[]
        # quantities[]
        # prices[]
        # item_discount_percentages[]
        # item_discount_amounts[]
        #
        # =====================================================

        product_ids = request.POST.getlist(
            "product_ids[]"
        )

        quantities = request.POST.getlist(
            "quantities[]"
        )

        item_discount_percentages = request.POST.getlist(
            "item_discount_percentages[]"
        )

        if not product_ids:

            return JsonResponse(
                {
                    "success": False,
                    "message": "No products were added."
                },
                status=400
            )

        if len(product_ids) != len(quantities):

            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid cart data."
                },
                status=400
            )

        # =====================================================
        # BUILD CART ITEMS
        # =====================================================

        items = []

        for index, product_id_raw in enumerate(product_ids):

            quantity_raw = (
                quantities[index]
                if index < len(quantities)
                else "0"
            )

            item_discount_raw = (
                item_discount_percentages[index]
                if index < len(item_discount_percentages)
                else "0"
            )

            try:

                product_id = int(product_id_raw)

                quantity = int(quantity_raw)

                item_discount = decimal_value(
                    item_discount_raw
                )

            except (
                ValueError,
                TypeError,
                InvalidOperation
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid cart item."
                    },
                    status=400
                )

            # =================================================
            # QUANTITY
            # =================================================

            if quantity <= 0:

                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Quantity must be greater than zero."
                        )
                    },
                    status=400
                )

            # =================================================
            # ITEM DISCOUNT
            # =================================================

            if item_discount < 0:

                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Item discount cannot be negative."
                        )
                    },
                    status=400
                )

            # =================================================
            # DETERMINE ITEM DISCOUNT CLUSTER
            #
            # Frontend sends the percentage.
            #
            # 0       = A
            # <= 10   = B
            # <= 100  = C
            #
            # =================================================

            if item_discount <= Decimal("0.00"):

                item_discount = Decimal("0.00")

                item_discount_cluster = "A"

            elif item_discount <= Decimal("10.00"):

                item_discount_cluster = "B"

            elif item_discount <= Decimal("100.00"):

                item_discount_cluster = "C"

            else:

                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Item discount cannot exceed 100%."
                        )
                    },
                    status=400
                )

            items.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "item_discount": item_discount,
                    "discount_cluster": item_discount_cluster,
                }
            )

        # =====================================================
        # PROCESS SALE
        # =====================================================

        try:

            with transaction.atomic():

                # =============================================
                # LOCK PRODUCTS
                # =============================================

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
                            "discount_cluster": (
                                cart_item["discount_cluster"]
                            ),
                        }
                    )

                # =============================================
                # CALCULATE ITEMS
                # =============================================

                sale_subtotal = Decimal("0.00")

                item_discount_total = Decimal("0.00")

                calculated_items = []

                for item in locked_items:

                    product = item["product"]

                    quantity = item["quantity"]

                    item_discount_percent = (
                        item["item_discount"]
                    )

                    discount_cluster = (
                        item["discount_cluster"]
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

                    if item_total < 0:

                        item_total = Decimal("0.00")

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
                            "discount_cluster": (
                                discount_cluster
                            ),
                        }
                    )

                sale_subtotal = money(
                    sale_subtotal
                )

                item_discount_total = money(
                    item_discount_total
                )

                # =============================================
                # AMOUNT AFTER ITEM DISCOUNT
                # =============================================

                amount_after_item_discount = money(
                    sale_subtotal
                    -
                    item_discount_total
                )

                # =============================================
                # CLIENT DISCOUNT
                # =============================================

                class_discount_amount = money(
                    amount_after_item_discount
                    *
                    (
                        discount_percent
                        /
                        Decimal("100")
                    )
                )

                # =============================================
                # FINAL TOTAL
                # =============================================

                final_total = money(
                    amount_after_item_discount
                    -
                    class_discount_amount
                )

                if final_total < 0:

                    final_total = Decimal("0.00")

                # =============================================
                # PAYMENT
                # =============================================

                if payment_status == "PAID":

                    if payment < final_total:

                        raise ValueError(
                            "Cash received is not enough "
                            "for a fully paid sale."
                        )

                    actual_payment = payment

                    actual_change = money(
                        payment
                        -
                        final_total
                    )

                elif payment_status == "PARTIAL":

                    if payment <= 0:

                        raise ValueError(
                            "Partial payment must be "
                            "greater than zero."
                        )

                    if payment >= final_total:

                        raise ValueError(
                            "For a partially paid sale, "
                            "payment must be less than "
                            "the total amount."
                        )

                    actual_payment = payment

                    actual_change = Decimal("0.00")

                else:

                    # UNPAID

                    actual_payment = Decimal("0.00")

                    actual_change = Decimal("0.00")

                # =============================================
                # TOTAL DISCOUNT
                # =============================================

                total_discount_amount = money(
                    item_discount_total
                    +
                    class_discount_amount
                )

                # =============================================
                # CREATE SALE
                # =============================================

                sale = Sale.objects.create(

                    staff=request.user,

                    salesperson=salesperson,

                    client=client,

                    discount_class=discount_class,

                    subtotal=sale_subtotal,

                    discount_percent=discount_percent,

                    discount_amount=(
                        total_discount_amount
                    ),

                    total=final_total,

                    payment_status=payment_status,

                    payment=actual_payment,

                    change=actual_change,

                )

                # =============================================
                # CREATE SALE ITEMS
                # =============================================

                for item in calculated_items:

                    product = item["product"]

                    quantity = item["quantity"]

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

                    # =========================================
                    # STOCK
                    # =========================================

                    previous_qty = product.qty

                    product.qty = (
                        product.qty
                        -
                        quantity
                    )

                    product.save(
                        update_fields=[
                            "qty",
                            "updated_at",
                        ]
                    )

                    # =========================================
                    # INVENTORY TRANSACTION
                    # =========================================

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

        # =====================================================
        # PRODUCT DOES NOT EXIST
        # =====================================================

        except Product.DoesNotExist:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "One of the selected products "
                        "no longer exists."
                    )
                },
                status=400
            )

        # =====================================================
        # SALESPERSON DOES NOT EXIST
        # =====================================================

        except Salesperson.DoesNotExist:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "The selected salesperson "
                        "no longer exists."
                    )
                },
                status=400
            )

        # =====================================================
        # CLIENT DOES NOT EXIST
        # =====================================================

        except Client.DoesNotExist:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "The selected client "
                        "no longer exists."
                    )
                },
                status=400
            )

        # =====================================================
        # VALIDATION ERROR
        # =====================================================

        except ValueError as error:

            return JsonResponse(
                {
                    "success": False,
                    "message": str(error)
                },
                status=400
            )

        # =====================================================
        # DATABASE / OTHER ERROR
        # =====================================================

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

        # =====================================================
        # RECEIPT ITEMS
        # =====================================================

        receipt_items = []

        for item in (
            sale.items
            .select_related("product")
            .all()
        ):

            receipt_items.append(
                {
                    "name": (
                        item.product.product_model
                    ),

                    "quantity": (
                        item.quantity
                    ),

                    "price": (
                        f"{item.price:.2f}"
                    ),

                    "subtotal": (
                        f"{item.subtotal:.2f}"
                    ),

                    "discount_percent": (
                        f"{item.discount_percent:.2f}"
                    ),

                    "discount_amount": (
                        f"{item.discount_amount:.2f}"
                    ),

                    "total": (
                        f"{item.total:.2f}"
                    ),
                }
            )

        # =====================================================
        # JSON RESPONSE
        # =====================================================

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

                # =============================================
                # SALESPERSON
                # =============================================

                "salesperson": (
                    salesperson.full_name
                ),

                "salesperson_id": (
                    salesperson.id
                ),

                # =============================================
                # CLIENT
                # =============================================

                "client": (
                    client.full_name
                    if client
                    else "Walk-in Client"
                ),

                "client_id": (
                    client.id
                    if client
                    else None
                ),

                "client_organization": (
                    client.organization
                    if client and client.organization
                    else ""
                ),

                # =============================================
                # DISCOUNT
                # =============================================

                "discount_class": (
                    discount_class.name
                    if discount_class
                    else "No Discount"
                ),

                "discount_class_code": (
                    discount_class.code
                    if discount_class
                    else ""
                ),

                "discount_percent": (
                    f"{sale.discount_percent:.2f}"
                ),

                "subtotal": (
                    f"{sale.subtotal:.2f}"
                ),

                "item_discount_amount": (
                    f"{item_discount_total:.2f}"
                ),

                "client_discount_amount": (
                    f"{class_discount_amount:.2f}"
                ),

                "discount_amount": (
                    f"{sale.discount_amount:.2f}"
                ),

                "total": (
                    f"{sale.total:.2f}"
                ),

                # =============================================
                # PAYMENT
                # =============================================

                "payment_status": (
                    sale.payment_status
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

                # =============================================
                # ITEMS
                # =============================================

                "items": receipt_items,
            }
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation
    ) as error:

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
# SALE RECEIPT
# =========================================================

@login_required
@user_passes_test(is_staff)
def sale_receipt(request, sale_id):

    sale = get_object_or_404(
        Sale.objects
        .select_related(
            "staff",
            "salesperson",
            "client",
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
                |
                Q(
                    items__product__description__icontains=search
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

        for item in sale.items.all():

            total_items += (
                item.quantity or 0
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