from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Sum
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
# STAFF DASHBOARD
# =========================================================

@login_required
@user_passes_test(is_staff)
def staff_dashboard(request):

    # ==========================================
    # CREATE DEFAULT DISCOUNT CLASSES
    # ==========================================

    # CLASS A - NO DISCOUNT
    DiscountClass.objects.get_or_create(
        code="A",
        defaults={
            "name": "No Discount",
            "max_discount": 0,
            "open_discount": False,
        }
    )

    # CLASS B - 1% TO 10%
    DiscountClass.objects.get_or_create(
        code="B",
        defaults={
            "name": "Discount 1-10%",
            "max_discount": 10,
            "open_discount": False,
        }
    )

    # CLASS C - OPEN DISCOUNT
    DiscountClass.objects.get_or_create(
        code="C",
        defaults={
            "name": "Open Discount",
            "max_discount": 100,
            "open_discount": True,
        }
    )

    # ==========================================
    # PRODUCTS
    # ==========================================

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

            Q(
                product_model__icontains=search
            )

            |

            Q(
                description__icontains=search
            )

            |

            Q(
                category__icontains=search
            )

        )

    # ==========================================
    # DISCOUNT CLASSES
    # ==========================================

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
def complete_sale(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request."
        }, status=400)

    try:

        discount_class_id = request.POST.get(
            "discount_class"
        )

        discount_percent = Decimal(
            request.POST.get(
                "discount_percent",
                "0"
            )
        )

        subtotal = Decimal(
            request.POST.get(
                "subtotal",
                "0"
            )
        )

        discount_amount = Decimal(
            request.POST.get(
                "discount_amount",
                "0"
            )
        )

        total = Decimal(
            request.POST.get(
                "total",
                "0"
            )
        )

        payment = Decimal(
            request.POST.get(
                "payment",
                "0"
            )
        )

        change = Decimal(
            request.POST.get(
                "change",
                "0"
            )
        )

    except (InvalidOperation, TypeError, ValueError):

        return JsonResponse({
            "success": False,
            "message": "Invalid sale information."
        }, status=400)

    # =========================================================
    # VALIDATION
    # =========================================================

    if discount_percent < 0 or discount_percent > 100:

        return JsonResponse({
            "success": False,
            "message": "Invalid discount percentage."
        }, status=400)

    if subtotal < 0 or total < 0:

        return JsonResponse({
            "success": False,
            "message": "Invalid sale amount."
        }, status=400)

    if payment < total:

        return JsonResponse({
            "success": False,
            "message": "Cash received is not enough."
        }, status=400)

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
    # CART
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

        if not product_id:
            break

        try:

            quantity = int(quantity_raw)

        except (TypeError, ValueError):

            return JsonResponse({
                "success": False,
                "message": "Invalid quantity."
            }, status=400)

        if quantity <= 0:

            return JsonResponse({
                "success": False,
                "message": "Invalid quantity."
            }, status=400)

        product = get_object_or_404(
            Product,
            id=product_id
        )

        items.append({
            "product": product,
            "quantity": quantity,
        })

        index += 1

    if not items:

        return JsonResponse({
            "success": False,
            "message": "No products were added."
        }, status=400)

    # =========================================================
    # SAVE EVERYTHING
    # =========================================================

    try:

        with transaction.atomic():

            # -----------------------------------------------
            # LOCK PRODUCTS
            # -----------------------------------------------

            for item in items:

                product = (
                    Product.objects
                    .select_for_update()
                    .get(
                        id=item["product"].id
                    )
                )

                quantity = item["quantity"]

                if product.qty < quantity:

                    raise ValueError(
                        f"Not enough stock for "
                        f"{product.product_model}. "
                        f"Available stock: {product.qty}"
                    )

                item["product"] = product

            # -----------------------------------------------
            # CREATE SALE
            # -----------------------------------------------

            sale = Sale.objects.create(

                staff=request.user,

                discount_class=discount_class,

                subtotal=subtotal,

                discount_percent=discount_percent,

                discount_amount=discount_amount,

                total=total,

                payment=payment,

                change=change,
            )

            # -----------------------------------------------
            # SALE ITEMS + INVENTORY
            # -----------------------------------------------

            for item in items:

                product = item["product"]

                quantity = item["quantity"]

                item_subtotal = (
                    product.price *
                    quantity
                )

                SaleItem.objects.create(

                    sale=sale,

                    product=product,

                    quantity=quantity,

                    price=product.price,

                    subtotal=item_subtotal,
                )

                # -------------------------------------------
                # STOCK
                # -------------------------------------------

                previous_qty = product.qty

                product.qty -= quantity

                product.save(
                    update_fields=[
                        "qty",
                        "updated_at",
                    ]
                )

                # -------------------------------------------
                # INVENTORY TRANSACTION
                # -------------------------------------------

                InventoryTransaction.objects.create(

                    product=product,

                    transaction_type="OUT",

                    quantity=quantity,

                    previous_qty=previous_qty,

                    new_qty=product.qty,

                    reference=f"SALE-{sale.id}",

                    notes=(
                        f"Sale #{sale.id}"
                    ),

                    created_by=request.user,
                )

    except ValueError as error:

        return JsonResponse({
            "success": False,
            "message": str(error)
        }, status=400)

    except Exception as error:

        return JsonResponse({
            "success": False,
            "message": (
                f"Unable to complete sale: {error}"
            )
        }, status=500)

    # =========================================================
    # PREPARE RECEIPT DATA
    # =========================================================

    receipt_items = []

    for item in sale.items.select_related("product").all():

        receipt_items.append({

            "name":
                item.product.product_model,

            "quantity":
                item.quantity,

            "price":
                f"{item.price:.2f}",

            "subtotal":
                f"{item.subtotal:.2f}",
        })

    # =========================================================
    # RETURN JSON
    # =========================================================

    return JsonResponse({

        "success": True,

        "sale_id":
            sale.id,

        "date":
            sale.created_at.strftime(
                "%b %d, %Y %I:%M %p"
            ),

        "staff":
            request.user.get_full_name()
            or request.user.username,

        "discount_class":
            discount_class.name
            if discount_class
            else "No Discount",

        "discount_percent":
            f"{sale.discount_percent:.2f}",

        "subtotal":
            f"{sale.subtotal:.2f}",

        "discount_amount":
            f"{sale.discount_amount:.2f}",

        "total":
            f"{sale.total:.2f}",

        "payment":
            f"{sale.payment:.2f}",

        "change":
            f"{sale.change:.2f}",

        "items":
            receipt_items,
    })
# =========================================================
# SALE RECEIPT
# =========================================================

@login_required
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



@login_required
def transaction_history(request):

    # =====================================================
    # ONLY CURRENT STAFF'S TRANSACTIONS
    # =====================================================

    sales = (
        Sale.objects
        .filter(staff=request.user)
        .select_related(
            "staff",
            "discount_class"
        )
        .prefetch_related(
            "items__product"
        )
        .order_by("-created_at")
    )


    # =====================================================
    # SEARCH
    # =====================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        # Search by Sale ID
        if search.isdigit():

            sales = sales.filter(
                id=int(search)
            )

        else:

            # Search by product name
            sales = sales.filter(
                items__product__product_model__icontains=search
            ).distinct()


    # =====================================================
    # DATE FILTER
    # =====================================================

    selected_date = request.GET.get(
        "date",
        ""
    ).strip()

    if selected_date:

        sales = sales.filter(
            created_at__date=selected_date
        )


    # =====================================================
    # TOTAL TRANSACTIONS
    # =====================================================

    total_transactions = sales.count()


    # =====================================================
    # TOTAL SALES
    # =====================================================

    total_sales = (
        sales.aggregate(
            total=Sum("total")
        )["total"] or 0
    )


    # =====================================================
    # TOTAL ITEMS SOLD
    # =====================================================

    total_items = 0

    for sale in sales:

        total_items += sum(
            item.quantity
            for item in sale.items.all()
        )


    # =====================================================
    # TODAY'S TRANSACTIONS
    # =====================================================

    today = timezone.localdate()

    today_transactions = (
        Sale.objects
        .filter(
            staff=request.user,
            created_at__date=today
        )
        .count()
    )


    # =====================================================
    # PAGINATION
    # =====================================================

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


    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "transactions": transactions,

        "total_transactions":
            total_transactions,

        "total_sales":
            total_sales,

        "total_items":
            total_items,

        "today_transactions":
            today_transactions,

    }


    return render(
        request,
        "staff/transaction_history.html",
        context
    )


@login_required
def inventory(request):
    products = Product.objects.all().order_by("product_model")

    return render(
        request,
        "staff/inventory.html",
        {
            "products": products,
        }
    )