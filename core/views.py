from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import Product, InventoryTransaction, Sale, SaleItem, UserProfile, Salesperson, Client, DiscountClass, AdminPortalLock
from openpyxl import load_workbook
from django.db.models import Sum, Count, Avg, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.db.models import (
    Q,
    Sum,
    F,
    Case,
    When,
    Value,
    CharField,
)
from django.utils import timezone
from datetime import datetime, time, timedelta
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.core.paginator import Paginator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import os
import json
from django.db import models
from django.http import JsonResponse


def is_superuser(user):
    return user.is_authenticated and user.is_superuser

# def admin_portal_locked(request):

#     return render(
#         request,
#         "admin_portal_locked.html"
#     )

@login_required
def admin_heartbeat(request):

    user = request.user

    # ==========================================================
    # ONLY ADMIN CAN SEND HEARTBEAT
    # ==========================================================

    is_admin = False

    if user.is_superuser:

        is_admin = True

    else:

        profile = getattr(
            user,
            "profile",
            None
        )

        if profile is not None:

            if profile.role == "ADMIN":
                is_admin = True


    # ==========================================================
    # NON-ADMIN
    # ==========================================================

    if not is_admin:

        return JsonResponse({
            "success": False,
            "message": "Not an administrator."
        }, status=403)


    # ==========================================================
    # GET SESSION
    # ==========================================================

    session_key = request.session.session_key


    # ==========================================================
    # FIND LOCK
    # ==========================================================

    lock = AdminPortalLock.objects.filter(
        id=1,
        locked=True,
        session_key=session_key
    ).first()


    # ==========================================================
    # LOCK DOES NOT BELONG TO THIS SESSION
    # ==========================================================

    if lock is None:

        return JsonResponse({
            "success": False,
            "locked": True
        }, status=403)


    # ==========================================================
    # UPDATE ACTIVITY
    # ==========================================================

    lock.last_activity = timezone.now()

    lock.save(
        update_fields=[
            "last_activity",
            "updated_at"
        ]
    )


    return JsonResponse({
        "success": True,
        "locked": True
    })

@login_required(login_url="login")
def dashboard(request):

    # =========================================================
    # LOCAL DATE / TIME
    # =========================================================

    today = timezone.localdate()

    yesterday = today - timedelta(days=1)

    # ---------------------------------------------------------
    # TODAY START
    # ---------------------------------------------------------

    today_start = timezone.make_aware(
        datetime.combine(
            today,
            time.min
        )
    )

    # ---------------------------------------------------------
    # TOMORROW START
    # ---------------------------------------------------------

    tomorrow = today + timedelta(days=1)

    tomorrow_start = timezone.make_aware(
        datetime.combine(
            tomorrow,
            time.min
        )
    )

    # ---------------------------------------------------------
    # YESTERDAY START / END
    # ---------------------------------------------------------

    yesterday_start = timezone.make_aware(
        datetime.combine(
            yesterday,
            time.min
        )
    )

    yesterday_end = today_start

    # =========================================================
    # CURRENT MONTH
    # =========================================================

    current_month = today.month
    current_year = today.year

    # ---------------------------------------------------------
    # MONTH START
    # ---------------------------------------------------------

    month_start_date = today.replace(
        day=1
    )

    month_start = timezone.make_aware(
        datetime.combine(
            month_start_date,
            time.min
        )
    )

    # ---------------------------------------------------------
    # NEXT MONTH
    # ---------------------------------------------------------

    if current_month == 12:

        next_month_date = today.replace(
            year=current_year + 1,
            month=1,
            day=1
        )

    else:

        next_month_date = today.replace(
            month=current_month + 1,
            day=1
        )

    next_month_start = timezone.make_aware(
        datetime.combine(
            next_month_date,
            time.min
        )
    )

    # =========================================================
    # TODAY'S SALES
    # =========================================================

    today_sales_qs = Sale.objects.filter(
        created_at__gte=today_start,
        created_at__lt=tomorrow_start
    )

    # ---------------------------------------------------------
    # Today's Sales
    # ---------------------------------------------------------

    total_sales = (
        today_sales_qs.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # ---------------------------------------------------------
    # Today's Transactions
    # ---------------------------------------------------------

    total_transactions = (
        today_sales_qs.count()
    )

    # ---------------------------------------------------------
    # Today's Items Sold
    # ---------------------------------------------------------

    total_items = (
        SaleItem.objects
        .filter(
            sale__created_at__gte=today_start,
            sale__created_at__lt=tomorrow_start
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # ---------------------------------------------------------
    # Today's Discounts
    # ---------------------------------------------------------

    total_discount = (
        today_sales_qs.aggregate(
            total=Sum("discount_amount")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # TODAY'S PAID / UNPAID / PARTIAL
    # =========================================================

    today_paid_sales = (
        today_sales_qs
        .filter(
            payment_status="PAID"
        )
    )

    today_unpaid_sales = (
        today_sales_qs
        .filter(
            payment_status="UNPAID"
        )
    )

    today_partial_sales = (
        today_sales_qs
        .filter(
            payment_status="PARTIAL"
        )
    )

    today_paid_total = (
        today_paid_sales.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    today_unpaid_total = (
        today_unpaid_sales.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    today_partial_total = (
        today_partial_sales.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # PRODUCTS / INVENTORY
    # =========================================================

    # ---------------------------------------------------------
    # Total Products
    # ---------------------------------------------------------

    total_products = Product.objects.count()

    # ---------------------------------------------------------
    # Low Stock
    #
    # qty > 0
    # qty <= low_stock_threshold
    # ---------------------------------------------------------

    low_stock = Product.objects.filter(
        qty__gt=0,
        qty__lte=F("low_stock_threshold")
    ).count()

    # ---------------------------------------------------------
    # Out of Stock
    # ---------------------------------------------------------

    out_of_stock = Product.objects.filter(
        qty=0
    ).count()

    # ---------------------------------------------------------
    # Total Inventory Quantity
    # ---------------------------------------------------------

    total_inventory_quantity = (
        Product.objects.aggregate(
            total=Sum("qty")
        )["total"]
        or 0
    )

    # ---------------------------------------------------------
    # Total Inventory Value
    #
    # price * qty
    # ---------------------------------------------------------

    inventory_value_expression = ExpressionWrapper(
        F("price") * F("qty"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    total_inventory_value = (
        Product.objects.aggregate(
            total=Sum(
                inventory_value_expression
            )
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # MONTHLY SALES
    # =========================================================

    monthly_sales_qs = Sale.objects.filter(
        created_at__gte=month_start,
        created_at__lt=next_month_start
    )

    # ---------------------------------------------------------
    # Monthly Sales
    # ---------------------------------------------------------

    monthly_sales = (
        monthly_sales_qs.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # ---------------------------------------------------------
    # Monthly Transactions
    # ---------------------------------------------------------

    monthly_transactions = (
        monthly_sales_qs.count()
    )

    # ---------------------------------------------------------
    # Monthly Items Sold
    # ---------------------------------------------------------

    monthly_items_sold = (
        SaleItem.objects
        .filter(
            sale__created_at__gte=month_start,
            sale__created_at__lt=next_month_start
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # ---------------------------------------------------------
    # Monthly Discounts
    # ---------------------------------------------------------

    monthly_discount = (
        monthly_sales_qs.aggregate(
            total=Sum("discount_amount")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # YESTERDAY
    # =========================================================

    yesterday_sales_qs = Sale.objects.filter(
        created_at__gte=yesterday_start,
        created_at__lt=yesterday_end
    )

    yesterday_sales = (
        yesterday_sales_qs.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    yesterday_transactions = (
        yesterday_sales_qs.count()
    )

    # =========================================================
    # AVERAGE SALE
    # =========================================================

    if total_transactions > 0:

        average_sale = (
            total_sales /
            total_transactions
        )

    else:

        average_sale = Decimal("0.00")

    # =========================================================
    # SALES CHANGE
    # =========================================================

    if yesterday_sales > 0:

        sales_change_percent = (
            (
                total_sales -
                yesterday_sales
            )
            /
            yesterday_sales
        ) * Decimal("100")

    else:

        sales_change_percent = Decimal("0.00")

    # =========================================================
    # PAYMENT SUMMARY
    # =========================================================

    # ---------------------------------------------------------
    # PAID
    # ---------------------------------------------------------

    paid_sales_qs = (
        Sale.objects
        .filter(
            payment_status="PAID"
        )
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    # ---------------------------------------------------------
    # UNPAID
    # ---------------------------------------------------------

    unpaid_sales_qs = (
        Sale.objects
        .filter(
            payment_status="UNPAID"
        )
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    # ---------------------------------------------------------
    # PARTIALLY PAID
    # ---------------------------------------------------------

    partial_sales_qs = (
        Sale.objects
        .filter(
            payment_status="PARTIAL"
        )
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    # =========================================================
    # PAYMENT TOTALS
    # =========================================================

    paid_total = (
        Sale.objects
        .filter(
            payment_status="PAID"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    unpaid_total = (
        Sale.objects
        .filter(
            payment_status="UNPAID"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    partial_total = (
        Sale.objects
        .filter(
            payment_status="PARTIAL"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # PAYMENT COUNTS
    # =========================================================

    paid_count = (
        Sale.objects
        .filter(
            payment_status="PAID"
        )
        .count()
    )

    unpaid_count = (
        Sale.objects
        .filter(
            payment_status="UNPAID"
        )
        .count()
    )

    partial_count = (
        Sale.objects
        .filter(
            payment_status="PARTIAL"
        )
        .count()
    )

    # =========================================================
    # TOTAL AMOUNT DUE
    #
    # total - payment
    #
    # Correctly handles:
    # UNPAID
    # PARTIAL
    # =========================================================

    amount_due_expression = ExpressionWrapper(
        F("total") - F("payment"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    total_amount_due = (
        Sale.objects
        .filter(
            payment_status__in=[
                "UNPAID",
                "PARTIAL"
            ]
        )
        .aggregate(
            total=Sum(
                amount_due_expression
            )
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # TOTAL PAYMENTS RECEIVED
    # =========================================================

    total_payments_received = (
        Sale.objects.aggregate(
            total=Sum("payment")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # TOTAL CHANGE GIVEN
    # =========================================================

    total_change = (
        Sale.objects.aggregate(
            total=Sum("change")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # ALL-TIME SALES
    # =========================================================

    all_time_sales = (
        Sale.objects.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # ALL-TIME DISCOUNTS
    # =========================================================

    all_time_discount = (
        Sale.objects.aggregate(
            total=Sum("discount_amount")
        )["total"]
        or Decimal("0.00")
    )

    # =========================================================
    # ALL-TIME ITEMS SOLD
    # =========================================================

    all_time_items_sold = (
        SaleItem.objects.aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # =========================================================
    # SALESPEOPLE
    # =========================================================

    salesperson_count = (
        Salesperson.objects
        .filter(
            is_active=True
        )
        .count()
    )

    # =========================================================
    # CLIENTS
    # =========================================================

    total_clients = (
        Client.objects.count()
    )

    active_clients = (
        Client.objects
        .filter(
            is_active=True
        )
        .count()
    )

    # =========================================================
    # DISCOUNT CLASSES
    # =========================================================

    total_discount_classes = (
        DiscountClass.objects.count()
    )

    # =========================================================
    # INVENTORY TRANSACTIONS
    # =========================================================

    total_inventory_transactions = (
        InventoryTransaction.objects.count()
    )

    # ---------------------------------------------------------
    # Today's Inventory Transactions
    # ---------------------------------------------------------

    today_inventory_transactions = (
        InventoryTransaction.objects
        .filter(
            created_at__gte=today_start,
            created_at__lt=tomorrow_start
        )
        .count()
    )

    # ---------------------------------------------------------
    # Stock In Today
    # ---------------------------------------------------------

    stock_in_today = (
        InventoryTransaction.objects
        .filter(
            transaction_type="IN",
            created_at__gte=today_start,
            created_at__lt=tomorrow_start
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # ---------------------------------------------------------
    # Stock Out Today
    # ---------------------------------------------------------

    stock_out_today = (
        InventoryTransaction.objects
        .filter(
            transaction_type="OUT",
            created_at__gte=today_start,
            created_at__lt=tomorrow_start
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # ---------------------------------------------------------
    # Adjustments Today
    # ---------------------------------------------------------

    adjustments_today = (
        InventoryTransaction.objects
        .filter(
            transaction_type="ADJUSTMENT",
            created_at__gte=today_start,
            created_at__lt=tomorrow_start
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # =========================================================
    # CHART - LAST 30 DAYS
    # =========================================================

    chart_labels = []
    chart_sales = []
    chart_transactions = []

    for i in range(29, -1, -1):

        chart_date = (
            today -
            timedelta(days=i)
        )

        chart_day_start = timezone.make_aware(
            datetime.combine(
                chart_date,
                time.min
            )
        )

        chart_next_day = chart_date + timedelta(days=1)

        chart_day_end = timezone.make_aware(
            datetime.combine(
                chart_next_day,
                time.min
            )
        )

        day_qs = Sale.objects.filter(
            created_at__gte=chart_day_start,
            created_at__lt=chart_day_end
        )

        day_total = (
            day_qs.aggregate(
                total=Sum("total")
            )["total"]
            or Decimal("0.00")
        )

        day_transactions = (
            day_qs.count()
        )

        chart_labels.append(
            chart_date.strftime("%b %d")
        )

        chart_sales.append(
            float(day_total)
        )

        chart_transactions.append(
            day_transactions
        )

    # =========================================================
    # RECENT SALES
    # =========================================================

    recent_sales_qs = (
        Sale.objects
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    recent_paginator = Paginator(
        recent_sales_qs,
        10
    )

    recent_page_obj = (
        recent_paginator.get_page(
            request.GET.get(
                "recent_page",
                1
            )
        )
    )

    # =========================================================
    # PAID PAGINATION
    # =========================================================

    paid_paginator = Paginator(
        paid_sales_qs,
        10
    )

    paid_page_obj = (
        paid_paginator.get_page(
            request.GET.get(
                "paid_page",
                1
            )
        )
    )

    # =========================================================
    # UNPAID PAGINATION
    # =========================================================

    unpaid_paginator = Paginator(
        unpaid_sales_qs,
        10
    )

    unpaid_page_obj = (
        unpaid_paginator.get_page(
            request.GET.get(
                "unpaid_page",
                1
            )
        )
    )

    # =========================================================
    # PARTIAL PAGINATION
    # =========================================================

    partial_paginator = Paginator(
        partial_sales_qs,
        10
    )

    partial_page_obj = (
        partial_paginator.get_page(
            request.GET.get(
                "partial_page",
                1
            )
        )
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # =====================================================
        # TODAY
        # =====================================================

        "today": today,

        "today_start": today_start,

        "today_end": tomorrow_start,

        "total_sales": total_sales,

        "total_transactions":
            total_transactions,

        "total_items":
            total_items,

        "total_discount":
            total_discount,

        # =====================================================
        # TODAY PAYMENT BREAKDOWN
        # =====================================================

        "today_paid_total":
            today_paid_total,

        "today_unpaid_total":
            today_unpaid_total,

        "today_partial_total":
            today_partial_total,

        "today_paid_count":
            today_paid_sales.count(),

        "today_unpaid_count":
            today_unpaid_sales.count(),

        "today_partial_count":
            today_partial_sales.count(),

        # =====================================================
        # PRODUCTS
        # =====================================================

        "total_products":
            total_products,

        "low_stock":
            low_stock,

        "out_of_stock":
            out_of_stock,

        "total_inventory_quantity":
            total_inventory_quantity,

        "total_inventory_value":
            total_inventory_value,

        # =====================================================
        # MONTH
        # =====================================================

        "monthly_sales":
            monthly_sales,

        "monthly_transactions":
            monthly_transactions,

        "monthly_items_sold":
            monthly_items_sold,

        "monthly_discount":
            monthly_discount,

        # =====================================================
        # COMPARISON
        # =====================================================

        "yesterday_sales":
            yesterday_sales,

        "yesterday_transactions":
            yesterday_transactions,

        "average_sale":
            average_sale,

        "sales_change_percent":
            sales_change_percent,

        # =====================================================
        # PAYMENT
        # =====================================================

        "paid_total":
            paid_total,

        "paid_count":
            paid_count,

        "unpaid_total":
            unpaid_total,

        "unpaid_count":
            unpaid_count,

        "partial_total":
            partial_total,

        "partial_count":
            partial_count,

        "total_amount_due":
            total_amount_due,

        "total_payments_received":
            total_payments_received,

        "total_change":
            total_change,

        # =====================================================
        # ALL TIME
        # =====================================================

        "all_time_sales":
            all_time_sales,

        "all_time_discount":
            all_time_discount,

        "all_time_items_sold":
            all_time_items_sold,

        # =====================================================
        # CLIENT / SALESPERSON
        # =====================================================

        "total_clients":
            total_clients,

        "active_clients":
            active_clients,

        "salesperson_count":
            salesperson_count,

        "total_discount_classes":
            total_discount_classes,

        # =====================================================
        # INVENTORY TRANSACTIONS
        # =====================================================

        "total_inventory_transactions":
            total_inventory_transactions,

        "today_inventory_transactions":
            today_inventory_transactions,

        "stock_in_today":
            stock_in_today,

        "stock_out_today":
            stock_out_today,

        "adjustments_today":
            adjustments_today,

        # =====================================================
        # PAGINATED SALES
        # =====================================================

        "paid_page_obj":
            paid_page_obj,

        "unpaid_page_obj":
            unpaid_page_obj,

        "partial_page_obj":
            partial_page_obj,

        "recent_page_obj":
            recent_page_obj,

        # =====================================================
        # CHART
        # =====================================================

        "chart_labels":
            json.dumps(chart_labels),

        "chart_sales":
            json.dumps(chart_sales),

        "chart_transactions":
            json.dumps(chart_transactions),
    }

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "pages/dashboard.html",
        context
    )

@login_required
@user_passes_test(is_superuser)
def staff_list(request):

    users = (
        User.objects
        .filter(profile__role__in=[
            "MANAGER",
            "STAFF",
            "CASHIER",
            "INVENTORY",
        ])
        .select_related("profile")
        .order_by("username")
    )

    return render(
        request,
        "users/staff_list.html",
        {
            "users": users
        }
    )
# ==========================================================
# ADD STAFF / USER
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def add_staff(request):

    # ======================================================
    # GET / DEFAULT DATA
    # ======================================================

    context = {
        "is_edit": False,
        "user": None,
        "profile": None,
        "roles": UserProfile.ROLE_CHOICES,
        "error": None,
    }

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password1 = request.POST.get(
            "password1",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        # ==================================================
        # CHECKBOX
        # ==================================================

        is_staff = (
            request.POST.get("is_staff") == "on"
        )

        # ==================================================
        # ROLE
        # ==================================================

        role = request.POST.get(
            "role",
            "STAFF"
        ).strip().upper()

        # ==================================================
        # VALID ROLES
        # ==================================================

        valid_roles = [
            choice[0]
            for choice in UserProfile.ROLE_CHOICES
        ]

        if role not in valid_roles:

            context["error"] = (
                "Invalid user role selected."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # VALIDATE NAME
        # ==================================================

        if not name:

            context["error"] = (
                "Name is required."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # VALIDATE USERNAME
        # ==================================================

        if not username:

            context["error"] = (
                "Username is required."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # VALIDATE PASSWORD
        # ==================================================

        if not password1:

            context["error"] = (
                "Password is required."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # PASSWORD LENGTH
        # ==================================================

        if len(password1) < 8:

            context["error"] = (
                "Password must be at least 8 characters."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # PASSWORD CONFIRMATION
        # ==================================================

        if password1 != password2:

            context["error"] = (
                "Passwords do not match."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # CHECK USERNAME
        # ==================================================

        if User.objects.filter(
            username=username
        ).exists():

            context["error"] = (
                "Username already exists."
            )

            return render(
                request,
                "users/staff_form.html",
                context
            )

        # ==================================================
        # CREATE USER
        # ==================================================

        user = User(
            first_name=name,
            username=username,
            is_staff=is_staff,
            is_superuser=False
        )

        # Proper password hashing
        user.set_password(password1)

        user.save()

        # ==================================================
        # CREATE USER PROFILE
        # ==================================================

        UserProfile.objects.create(
            user=user,
            role=role
        )

        # ==================================================
        # REDIRECT AFTER SUCCESS
        # ======================================================

        return redirect("staff_list")

    # ======================================================
    # GET
    # ======================================================

    return render(
        request,
        "users/staff_form.html",
        context
    )


# ==========================================================
# EDIT USER
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def edit_user(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    # ======================================================
    # PROTECT SUPERUSER
    # ======================================================

    if user.is_superuser:

        return render(
            request,
            "users/staff_list.html",
            {
                "error": "The superuser account is protected."
            }
        )

    # ======================================================
    # GET OR CREATE PROFILE
    # ======================================================

    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "role": "STAFF"
        }
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password1 = request.POST.get(
            "password1",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        # ==================================================
        # CHECKBOX
        # ==================================================

        is_staff = (
            request.POST.get("is_staff") == "on"
        )

        # ==================================================
        # ROLE
        # ==================================================

        role = request.POST.get(
            "role",
            "STAFF"
        ).strip().upper()

        # ==================================================
        # VALID ROLES
        # ==================================================

        valid_roles = [
            choice[0]
            for choice in UserProfile.ROLE_CHOICES
        ]

        if role not in valid_roles:

            return render(
                request,
                "users/staff_form.html",
                {
                    "is_edit": True,
                    "user": user,
                    "profile": profile,
                    "roles": UserProfile.ROLE_CHOICES,
                    "error": "Invalid user role selected."
                }
            )

        # ==================================================
        # VALIDATE NAME
        # ==================================================

        if not name:

            return render(
                request,
                "users/staff_form.html",
                {
                    "is_edit": True,
                    "user": user,
                    "profile": profile,
                    "roles": UserProfile.ROLE_CHOICES,
                    "error": "Name is required."
                }
            )

        # ==================================================
        # VALIDATE USERNAME
        # ==================================================

        if not username:

            return render(
                request,
                "users/staff_form.html",
                {
                    "is_edit": True,
                    "user": user,
                    "profile": profile,
                    "roles": UserProfile.ROLE_CHOICES,
                    "error": "Username is required."
                }
            )

        # ==================================================
        # CHECK USERNAME
        # ==================================================

        if User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists():

            return render(
                request,
                "users/staff_form.html",
                {
                    "is_edit": True,
                    "user": user,
                    "profile": profile,
                    "roles": UserProfile.ROLE_CHOICES,
                    "error": "Username already exists."
                }
            )

        # ==================================================
        # PASSWORD
        # ==================================================

        if password1 or password2:

            # ----------------------------------------------
            # BOTH REQUIRED
            # ----------------------------------------------

            if not password1 or not password2:

                return render(
                    request,
                    "users/staff_form.html",
                    {
                        "is_edit": True,
                        "user": user,
                        "profile": profile,
                        "roles": UserProfile.ROLE_CHOICES,
                        "error": (
                            "Please enter and confirm "
                            "the new password."
                        )
                    }
                )

            # ----------------------------------------------
            # MATCH
            # ----------------------------------------------

            if password1 != password2:

                return render(
                    request,
                    "users/staff_form.html",
                    {
                        "is_edit": True,
                        "user": user,
                        "profile": profile,
                        "roles": UserProfile.ROLE_CHOICES,
                        "error": "Passwords do not match."
                    }
                )

            # ----------------------------------------------
            # PASSWORD LENGTH
            # ----------------------------------------------

            if len(password1) < 8:

                return render(
                    request,
                    "users/staff_form.html",
                    {
                        "is_edit": True,
                        "user": user,
                        "profile": profile,
                        "roles": UserProfile.ROLE_CHOICES,
                        "error": (
                            "Password must be at least "
                            "8 characters."
                        )
                    }
                )

            # ----------------------------------------------
            # SET PASSWORD
            # ----------------------------------------------

            user.set_password(password1)

        # ==================================================
        # UPDATE USER
        # ==================================================

        user.first_name = name
        user.username = username
        user.is_staff = is_staff

        # Never allow this page to create a superuser
        user.is_superuser = False

        user.save()

        # ==================================================
        # UPDATE USER PROFILE
        # ==================================================

        profile.role = role
        profile.save()

        # ==================================================
        # REDIRECT
        # ==================================================

        return redirect("staff_list")

    # ======================================================
    # DISPLAY FORM
    # ======================================================

    return render(
        request,
        "users/staff_form.html",
        {
            "is_edit": True,
            "user": user,
            "profile": profile,
            "roles": UserProfile.ROLE_CHOICES,
            "error": None,
        }
    )

@login_required
@user_passes_test(is_superuser)
def delete_user(request, user_id):

    user = get_object_or_404(User, id=user_id)

    # ==========================================
    # PROTECT SUPERUSER
    # ==========================================

    if user.is_superuser:

        messages.error(
            request,
            "The superuser account cannot be deleted."
        )

        return redirect("staff_list")


    # ==========================================
    # DELETE USER
    # ==========================================

    if request.method == "POST":

        username = user.username

        user.delete()

        messages.success(
            request,
            f"Staff account '{username}' deleted successfully."
        )

        return redirect("staff_list")


    # ==========================================
    # SHOW CONFIRMATION PAGE
    # ==========================================

    return render(
        request,
        "users/staff_delete.html",
        {
            "user": user
        }
    )


#Salesperson
# ==========================================================
# SALESPERSON LIST
# ==========================================================
# ==========================================================
# SALESPERSON LIST
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def salesperson_list(request):

    # ======================================================
    # GET SALESPERSONS
    # ======================================================

    salespersons = (
        Salesperson.objects
        .all()
        .order_by(
            "last_name",
            "first_name"
        )
    )

    # ======================================================
    # SEARCH
    # ======================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        salespersons = salespersons.filter(
            Q(last_name__icontains=search)
            | Q(first_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(contact_number__icontains=search)
            | Q(email_address__icontains=search)
        )

    # ======================================================
    # STATUS FILTER
    # ======================================================

    status = request.GET.get(
        "status",
        "all"
    )

    if status == "active":

        salespersons = salespersons.filter(
            is_active=True
        )

    elif status == "inactive":

        salespersons = salespersons.filter(
            is_active=False
        )

    # ======================================================
    # PAGINATION
    # ======================================================

    paginator = Paginator(
        salespersons,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # ======================================================
    # RENDER
    # ======================================================

    return render(
        request,
        "users/salesperson_list.html",
        {
            "salespersons": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "search": search,
            "status": status,
            "total_salespersons": paginator.count,
        }
    )

# ==========================================================
# ADD SALESPERSON
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def add_salesperson(request):

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        # ==================================================
        # GET FORM DATA
        # ==================================================

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        middle_name = request.POST.get(
            "middle_name",
            ""
        ).strip()

        contact_number = request.POST.get(
            "contact_number",
            ""
        ).strip()

        email_address = request.POST.get(
            "email_address",
            ""
        ).strip()

        is_active = (
            request.POST.get("is_active") == "on"
        )

        # ==================================================
        # VALIDATE LAST NAME
        # ==================================================

        if not last_name:

            return render(
                request,
                "users/salesperson_form.html",
                {
                    "is_edit": False,
                    "salesperson": None,
                    "error": "Last name is required.",
                }
            )

        # ==================================================
        # VALIDATE FIRST NAME
        # ==================================================

        if not first_name:

            return render(
                request,
                "users/salesperson_form.html",
                {
                    "is_edit": False,
                    "salesperson": None,
                    "error": "First name is required.",
                }
            )

        # ==================================================
        # VALIDATE EMAIL
        # ==================================================

        if email_address:

            try:

                validate_email(
                    email_address
                )

            except ValidationError:

                return render(
                    request,
                    "users/salesperson_form.html",
                    {
                        "is_edit": False,
                        "salesperson": None,
                        "error": (
                            "Please enter a valid "
                            "email address."
                        ),
                    }
                )

        # ==================================================
        # CREATE SALESPERSON
        # ==================================================

        Salesperson.objects.create(

            last_name=last_name,

            first_name=first_name,

            middle_name=(
                middle_name
                or None
            ),

            contact_number=(
                contact_number
                or None
            ),

            email_address=(
                email_address
                or None
            ),

            is_active=is_active,
        )

        # ==================================================
        # SUCCESS
        # ==================================================

        return redirect(
            "salesperson-list"
        )

    # ======================================================
    # GET REQUEST
    # ======================================================

    return render(
        request,
        "users/salesperson_form.html",
        {
            "is_edit": False,
            "salesperson": None,
            "error": None,
        }
    )

# ==========================================================
# EDIT SALESPERSON
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def edit_salesperson(request, salesperson_id):

    salesperson = get_object_or_404(
        Salesperson,
        id=salesperson_id
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        # ==================================================
        # GET FORM DATA
        # ==================================================

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        middle_name = request.POST.get(
            "middle_name",
            ""
        ).strip()

        contact_number = request.POST.get(
            "contact_number",
            ""
        ).strip()

        email_address = request.POST.get(
            "email_address",
            ""
        ).strip()

        is_active = (
            request.POST.get("is_active") == "on"
        )

        # ==================================================
        # VALIDATE LAST NAME
        # ==================================================

        if not last_name:

            return render(
                request,
                "users/salesperson_form.html",
                {
                    "is_edit": True,
                    "salesperson": salesperson,
                    "error": "Last name is required.",
                }
            )

        # ==================================================
        # VALIDATE FIRST NAME
        # ==================================================

        if not first_name:

            return render(
                request,
                "users/salesperson_form.html",
                {
                    "is_edit": True,
                    "salesperson": salesperson,
                    "error": "First name is required.",
                }
            )

        # ==================================================
        # VALIDATE EMAIL
        # ==================================================

        if email_address:

            try:

                validate_email(
                    email_address
                )

            except ValidationError:

                return render(
                    request,
                    "users/salesperson_form.html",
                    {
                        "is_edit": True,
                        "salesperson": salesperson,
                        "error": (
                            "Please enter a valid "
                            "email address."
                        ),
                    }
                )

        # ==================================================
        # UPDATE SALESPERSON
        # ==================================================

        salesperson.last_name = (
            last_name
        )

        salesperson.first_name = (
            first_name
        )

        salesperson.middle_name = (
            middle_name
            or None
        )

        salesperson.contact_number = (
            contact_number
            or None
        )

        salesperson.email_address = (
            email_address
            or None
        )

        salesperson.is_active = (
            is_active
        )

        salesperson.save()

        # ==================================================
        # SUCCESS
        # ==================================================

        return redirect(
            "salesperson-list"
        )

    # ======================================================
    # GET
    # ======================================================

    return render(
        request,
        "users/salesperson_form.html",
        {
            "is_edit": True,
            "salesperson": salesperson,
            "error": None,
        }
    )

# ==========================================================
# DELETE SALESPERSON
# ==========================================================

@login_required
@user_passes_test(is_superuser)
def delete_salesperson(request, salesperson_id):

    salesperson = get_object_or_404(
        Salesperson,
        id=salesperson_id
    )

    if request.method == "POST":

        salesperson.delete()

        return redirect(
            "salesperson-list"
        )

    return redirect(
        "salesperson-list"
    )


#Products
@login_required
@user_passes_test(is_superuser)
def product_list(request):

    # -----------------------------------------------------
    # GET SEARCH QUERY
    # -----------------------------------------------------

    search_query = request.GET.get("search", "").strip()

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    products = Product.objects.all().order_by("-id")

    # -----------------------------------------------------
    # LIVE SEARCH
    # -----------------------------------------------------

    if search_query:
        products = products.filter(
            Q(product_model__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__icontains=search_query)
        )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(products, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return render(
        request,
        "products/product_list.html",
        {
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "search_query": search_query,
        }
    )

@login_required
@user_passes_test(is_superuser)
def add_product(request):

    if request.method == "POST":

        product_model = request.POST.get(
            "product_model",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        qty = request.POST.get(
            "qty",
            ""
        ).strip()

        image = request.FILES.get("image")


        # ==========================================
        # VALIDATION
        # ==========================================

        if not product_model:

            messages.error(
                request,
                "Product name/model is required."
            )

            return redirect("add-product")


        if not category:

            messages.error(
                request,
                "Category is required."
            )

            return redirect("add-product")


        if not price:

            messages.error(
                request,
                "Price is required."
            )

            return redirect("add-product")


        if not qty:

            qty = 0


        # ==========================================
        # CREATE PRODUCT
        # ==========================================

        Product.objects.create(

            product_model=product_model,

            description=description,

            category=category,

            price=price,

            qty=qty,

            image=image

        )


        # ==========================================
        # SUCCESS
        # ==========================================

        messages.success(
            request,
            f"Product '{product_model}' added successfully."
        )

        return redirect("product_list")


    return render(
        request,
        "products/product_form.html",
        {
            "is_edit": False,
            "product": None,
        }
    )


@login_required
@user_passes_test(is_superuser)
def edit_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )


    if request.method == "POST":

        product_model = request.POST.get(
            "product_model",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        qty = request.POST.get(
            "qty",
            ""
        ).strip()

        image = request.FILES.get("image")


        # ==========================================
        # VALIDATION
        # ==========================================

        if not product_model:

            messages.error(
                request,
                "Product name/model is required."
            )

            return redirect(
                "edit-product",
                product_id=product.id
            )


        if not category:

            messages.error(
                request,
                "Category is required."
            )

            return redirect(
                "edit-product",
                product_id=product.id
            )


        if not price:

            messages.error(
                request,
                "Price is required."
            )

            return redirect(
                "edit-product",
                product_id=product.id
            )


        if not qty:

            qty = 0


        # ==========================================
        # UPDATE PRODUCT
        # ==========================================

        product.product_model = product_model

        product.description = description

        product.category = category

        product.price = price

        product.qty = qty


        # ==========================================
        # UPDATE IMAGE
        # ==========================================

        if image:

            product.image = image


        # ==========================================
        # SAVE
        # ==========================================

        product.save()


        # ==========================================
        # SUCCESS
        # ==========================================

        messages.success(
            request,
            f"Product '{product.product_model}' updated successfully."
        )

        return redirect("product_list")


    return render(
        request,
        "products/product_form.html",
        {
            "is_edit": True,
            "product": product,
        }
    )

@login_required
@user_passes_test(is_superuser)
def delete_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )


    if request.method == "POST":

        product_name = product.product_model

        product.delete()

        messages.success(
            request,
            f"Product '{product_name}' deleted successfully."
        )

        return redirect("product_list")


    return render(
        request,
        "products/product_delete.html",
        {
            "product": product
        }
    )

@login_required
@user_passes_test(is_superuser)
def import_products(request):

    if request.method == "POST":

        excel_file = request.FILES.get("excel_file")

        if not excel_file:

            messages.error(
                request,
                "Please select an Excel file."
            )

            return redirect("import-products")


        # ==========================================
        # CHECK FILE TYPE
        # ==========================================

        if not excel_file.name.lower().endswith(".xlsx"):

            messages.error(
                request,
                "Only .xlsx Excel files are allowed."
            )

            return redirect("import-products")


        try:

            workbook = load_workbook(
                excel_file,
                data_only=True
            )

            worksheet = workbook.active


            # ==========================================
            # EXPECTED HEADERS
            # IMAGE IS LAST
            # ==========================================

            expected_headers = [
                "product_model",
                "description",
                "category",
                "price",
                "qty",
                "image",
            ]


            headers = [
                str(cell.value).strip().lower()
                if cell.value is not None
                else ""
                for cell in worksheet[1]
            ]


            if headers != expected_headers:

                messages.error(
                    request,
                    "Invalid Excel format. Please use the provided template."
                )

                return redirect("import-products")


            # ==========================================
            # PROCESS ROWS
            # ==========================================

            created_count = 0
            error_count = 0
            errors = []


            for row_number, row in enumerate(
                worksheet.iter_rows(
                    min_row=2,
                    values_only=True
                ),
                start=2
            ):

                # ==========================================
                # SKIP EMPTY ROW
                # ==========================================

                if not any(
                    value is not None
                    for value in row
                ):
                    continue


                # ==========================================
                # GET VALUES
                # ==========================================

                product_model = (
                    str(row[0]).strip()
                    if row[0] is not None
                    else ""
                )

                description = (
                    str(row[1]).strip()
                    if row[1] is not None
                    else ""
                )

                category = (
                    str(row[2]).strip()
                    if row[2] is not None
                    else ""
                )

                price = row[3]

                qty = row[4]

                image_name = (
                    str(row[5]).strip()
                    if row[5] is not None
                    else ""
                )


                # ==========================================
                # REQUIRED FIELDS
                # ==========================================

                if not product_model:

                    errors.append(
                        f"Row {row_number}: Product Model is required."
                    )

                    error_count += 1

                    continue


                if not category:

                    errors.append(
                        f"Row {row_number}: Category is required."
                    )

                    error_count += 1

                    continue


                if price is None:

                    errors.append(
                        f"Row {row_number}: Price is required."
                    )

                    error_count += 1

                    continue


                # ==========================================
                # PRICE VALIDATION
                # ==========================================

                try:

                    price = float(price)

                    if price < 0:
                        raise ValueError

                except (ValueError, TypeError):

                    errors.append(
                        f"Row {row_number}: Invalid price."
                    )

                    error_count += 1

                    continue


                # ==========================================
                # QTY VALIDATION
                # ==========================================

                if qty is None:

                    qty = 0

                try:

                    qty = int(qty)

                    if qty < 0:
                        raise ValueError

                except (ValueError, TypeError):

                    errors.append(
                        f"Row {row_number}: Invalid quantity."
                    )

                    error_count += 1

                    continue


                # ==========================================
                # CREATE PRODUCT
                # ==========================================

                product = Product.objects.create(

                    product_model=product_model,

                    description=description,

                    category=category,

                    price=price,

                    qty=qty

                )


                # ==========================================
                # IMAGE
                # ==========================================
                #
                # IMPORTANT:
                #
                # The Excel image column only contains
                # the filename.
                #
                # If an image filename exists, save it
                # as the Product.image value.
                #
                # If empty, leave Product.image empty.
                #
                # The template will then show:
                #
                # static/images/defualt-product.png
                #
                # ==========================================

                if image_name:

                    image_filename = os.path.basename(
                        image_name
                    )

                    product.image = (
                        f"products/{image_filename}"
                    )

                    product.save(
                        update_fields=["image"]
                    )


                created_count += 1


            # ==========================================
            # RESULT
            # ==========================================

            if created_count > 0:

                messages.success(
                    request,
                    f"{created_count} product(s) imported successfully."
                )


            if error_count > 0:

                for error in errors:

                    messages.error(
                        request,
                        error
                    )


            return redirect("product_list")


        except Exception as e:

            messages.error(
                request,
                f"Unable to read Excel file: {str(e)}"
            )

            return redirect("import-products")


    return render(
        request,
        "products/import_products.html"
    )

# Inventory

@login_required
@user_passes_test(is_superuser)
def inventory(request):

    # =========================================================
    # PRODUCTS
    # =========================================================

    products = Product.objects.all().order_by(
        "product_model"
    )


    # =========================================================
    # SEARCH
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        products = products.filter(
            Q(product_model__icontains=search) |
            Q(category__icontains=search)
        )


    # =========================================================
    # CATEGORY
    # =========================================================

    selected_category = request.GET.get(
        "category",
        ""
    ).strip()

    if selected_category:

        products = products.filter(
            category=selected_category
        )


    # =========================================================
    # STOCK STATUS
    # =========================================================

    selected_status = request.GET.get(
        "stock_status",
        ""
    ).strip()


    # =========================================================
    # ANNOTATE STOCK STATUS
    #
    # 0                       = Out of Stock
    # 1 - threshold           = Low Stock
    # above threshold         = In Stock
    # =========================================================

    products = products.annotate(

        stock_status_value=Case(

            When(
                qty=0,
                then=Value("out")
            ),

            When(
                qty__lte=F("low_stock_threshold"),
                then=Value("low")
            ),

            default=Value("in"),

            output_field=CharField()
        )
    )


    # =========================================================
    # FILTER BY STOCK STATUS
    # =========================================================

    if selected_status in [
        "in",
        "low",
        "out"
    ]:

        products = products.filter(
            stock_status_value=selected_status
        )


    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        products,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    # =========================================================
    # SUMMARY
    # =========================================================

    total_products = Product.objects.count()


    total_stock = Product.objects.aggregate(
        total=Coalesce(
            Sum("qty"),
            0
        )
    )["total"]


    low_stock = Product.objects.filter(
        qty__gt=0,
        qty__lte=F("low_stock_threshold")
    ).count()


    out_of_stock = Product.objects.filter(
        qty=0
    ).count()


    # =========================================================
    # CATEGORIES
    # =========================================================

    categories = Product.objects.values_list(
        "category",
        flat=True
    ).distinct().order_by(
        "category"
    )


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "inventory/inventory.html",
        {
            "products": page_obj,

            "page_obj": page_obj,

            "paginator": paginator,

            "total_products": total_products,

            "total_stock": total_stock,

            "low_stock": low_stock,

            "out_of_stock": out_of_stock,

            "categories": categories,

            "search": search,

            "selected_category": selected_category,

            "selected_status": selected_status,
        }
    )

@login_required
@user_passes_test(is_superuser)
def stock_in(request):

    products = Product.objects.all().order_by(
        "product_model"
    )


    if request.method == "POST":

        product_id = request.POST.get(
            "product"
        )

        quantity = request.POST.get(
            "quantity"
        )

        reference = request.POST.get(
            "reference",
            ""
        ).strip()

        notes = request.POST.get(
            "notes",
            ""
        ).strip()


        # ==========================================
        # VALIDATE PRODUCT
        # ==========================================

        try:

            product = Product.objects.get(
                id=product_id
            )

        except Product.DoesNotExist:

            messages.error(
                request,
                "Product not found."
            )

            return redirect("stock-in")


        # ==========================================
        # VALIDATE QUANTITY
        # ==========================================

        try:

            quantity = int(quantity)

        except (TypeError, ValueError):

            messages.error(
                request,
                "Please enter a valid quantity."
            )

            return redirect("stock-in")


        if quantity <= 0:

            messages.error(
                request,
                "Quantity must be greater than zero."
            )

            return redirect("stock-in")


        # ==========================================
        # UPDATE STOCK
        # ==========================================

        previous_qty = product.qty

        product.qty += quantity

        new_qty = product.qty

        product.save()


        # ==========================================
        # CREATE TRANSACTION
        # ==========================================

        InventoryTransaction.objects.create(

            product=product,

            transaction_type="IN",

            quantity=quantity,

            previous_qty=previous_qty,

            new_qty=new_qty,

            reference=reference,

            notes=notes,

            created_by=request.user

        )


        messages.success(

            request,

            f"{quantity} units added to "
            f"{product.product_model}."

        )


        return redirect("inventory")


    return render(

        request,

        "inventory/stock_in.html",

        {
            "products": products
        }

    )


@login_required
@user_passes_test(is_superuser)
def inventory_history(request):

    transactions = InventoryTransaction.objects.select_related(
        "product",
        "created_by"
    ).order_by(
        "-created_at"
    )


    # ==========================================
    # SEARCH
    # ==========================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        transactions = transactions.filter(

            Q(product__product_model__icontains=search) |

            Q(product__category__icontains=search) |

            Q(reference__icontains=search) |

            Q(notes__icontains=search) |

            Q(created_by__username__icontains=search)

        )


    # ==========================================
    # TRANSACTION TYPE
    # ==========================================

    transaction_type = request.GET.get(
        "transaction_type",
        ""
    )

    if transaction_type:

        transactions = transactions.filter(
            transaction_type=transaction_type
        )


    # ==========================================
    # PRODUCT FILTER
    # ==========================================

    product_id = request.GET.get(
        "product",
        ""
    )

    if product_id:

        transactions = transactions.filter(
            product_id=product_id
        )


    # ==========================================
    # PRODUCTS FOR FILTER
    # ==========================================

    products = Product.objects.all().order_by(
        "product_model"
    )


    # ==========================================
    # SUMMARY
    # ==========================================

    total_transactions = transactions.count()


    stock_in_count = transactions.filter(
        transaction_type="IN"
    ).count()


    stock_out_count = transactions.filter(
        transaction_type="OUT"
    ).count()


    adjustment_count = transactions.filter(
        transaction_type="ADJUSTMENT"
    ).count()


    # ==========================================
    # PAGINATION
    # ==========================================

    paginator = Paginator(
        transactions,
        10
    )


    page_number = request.GET.get(
        "page"
    )


    page_obj = paginator.get_page(
        page_number
    )


    # ==========================================
    # RENDER
    # ==========================================

    return render(

        request,

        "inventory/inventory_history.html",

        {

            "transactions": page_obj,

            "page_obj": page_obj,

            "paginator": paginator,

            "products": products,

            "total_transactions": total_transactions,

            "stock_in_count": stock_in_count,

            "stock_out_count": stock_out_count,

            "adjustment_count": adjustment_count,

            "search": search,

            "transaction_type": transaction_type,

            "selected_product": product_id,

        }

    )


@login_required
@user_passes_test(is_superuser)
def product_inventory_history(request, product_id):

    # ==========================================
    # GET TARGET PRODUCT
    # ==========================================

    product = get_object_or_404(
        Product,
        id=product_id
    )


    # ==========================================
    # GET TRANSACTIONS FOR THIS PRODUCT ONLY
    # ==========================================

    transactions = InventoryTransaction.objects.filter(
        product=product
    ).select_related(
        "created_by"
    ).order_by(
        "-created_at"
    )


    # ==========================================
    # SUMMARY
    # ==========================================

    total_transactions = transactions.count()

    stock_in_count = transactions.filter(
        transaction_type="IN"
    ).count()

    stock_out_count = transactions.filter(
        transaction_type="OUT"
    ).count()

    adjustment_count = transactions.filter(
        transaction_type="ADJUSTMENT"
    ).count()


    # ==========================================
    # TOTAL STOCK IN
    # ==========================================

    from django.db.models import Sum

    total_stock_in = (
        transactions
        .filter(transaction_type="IN")
        .aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )


    # ==========================================
    # TOTAL STOCK OUT
    # ==========================================

    total_stock_out = (
        transactions
        .filter(transaction_type="OUT")
        .aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )


    # ==========================================
    # RENDER
    # ==========================================

    return render(

        request,

        "inventory/product_inventory_history.html",

        {

            "product": product,

            "transactions": transactions,

            "total_transactions": total_transactions,

            "stock_in_count": stock_in_count,

            "stock_out_count": stock_out_count,

            "adjustment_count": adjustment_count,

            "total_stock_in": total_stock_in,

            "total_stock_out": total_stock_out,

        }

    )


@login_required
def admin_pos(request):

    # =========================================================
    # TODAY
    # =========================================================

    today = timezone.localdate()


    # =========================================================
    # ALL TODAY'S SALES
    # =========================================================

    all_today_sales = list(
        Sale.objects
        .filter(
            created_at__date=today
        )
        .select_related(
            "salesperson",
            "staff",
            "discount_class",
            "client",
        )
        .prefetch_related(
            "items__product"
        )
        .order_by(
            "-created_at"
        )
    )


    # =========================================================
    # HELPER: GET SALESPERSON NAME
    # =========================================================

    def get_salesperson_name(sale):

        salesperson = getattr(
            sale,
            "salesperson",
            None
        )

        if not salesperson:
            return "No Salesperson"


        parts = [
            salesperson.first_name,
            salesperson.middle_name,
            salesperson.last_name,
        ]

        full_name = " ".join(
            str(part).strip()
            for part in parts
            if part
        ).strip()


        if full_name:
            return full_name


        return "No Salesperson"


    # =========================================================
    # HELPER: GET CLIENT / ORGANIZATION
    # =========================================================

    def get_client_organization(sale):

        client = getattr(
            sale,
            "client",
            None
        )

        if not client:
            return "Walk-in Customer"


        organization = (
            getattr(
                client,
                "organization",
                ""
            )
            or ""
        ).strip()


        if organization:
            return organization


        return "Walk-in Customer"


    # =========================================================
    # HELPER: GET PAYMENT STATUS
    # =========================================================

    def get_payment_status(sale):

        status = (
            getattr(
                sale,
                "payment_status",
                ""
            )
            or ""
        ).strip().upper()


        if status in [
            "PAID",
            "UNPAID",
            "PARTIAL",
        ]:

            return status


        # -----------------------------------------------------
        # Fallback calculation
        # -----------------------------------------------------

        total = (
            getattr(
                sale,
                "total",
                0
            )
            or 0
        )

        payment = (
            getattr(
                sale,
                "payment",
                0
            )
            or 0
        )


        if payment >= total:
            return "PAID"

        elif payment > 0:
            return "PARTIAL"

        return "UNPAID"


    # =========================================================
    # HELPER: GET BALANCE
    # =========================================================

    def get_balance(sale):

        total = (
            getattr(
                sale,
                "total",
                0
            )
            or 0
        )

        payment = (
            getattr(
                sale,
                "payment",
                0
            )
            or 0
        )

        balance = total - payment


        if balance < 0:
            return 0


        return balance


    # =========================================================
    # ADD DISPLAY INFORMATION
    # =========================================================

    for sale in all_today_sales:

        sale.display_salesperson = (
            get_salesperson_name(sale)
        )

        sale.display_salesman = (
            sale.display_salesperson
        )

        sale.display_client = (
            get_client_organization(sale)
        )

        sale.display_payment_status = (
            get_payment_status(sale)
        )

        sale.display_balance = (
            get_balance(sale)
        )


    # =========================================================
    # SUMMARY
    # =========================================================

    total_sales = sum(
        (
            sale.total
            or 0
        )
        for sale in all_today_sales
    )


    total_transactions = len(
        all_today_sales
    )


    total_items = 0


    for sale in all_today_sales:

        for item in sale.items.all():

            total_items += (
                item.quantity
                or 0
            )


    total_discount = sum(
        (
            sale.discount_amount
            or 0
        )
        for sale in all_today_sales
    )


    total_payment = sum(
        (
            sale.payment
            or 0
        )
        for sale in all_today_sales
    )


    # =========================================================
    # AVERAGE TRANSACTION
    # =========================================================

    if total_transactions > 0:

        average_transaction = (
            total_sales
            /
            total_transactions
        )

    else:

        average_transaction = 0


    # =========================================================
    # TOTAL AMOUNT DUE
    # =========================================================

    total_due = sum(
        sale.display_balance
        for sale in all_today_sales
    )


    # =========================================================
    # PAYMENT STATUS COUNTS
    # =========================================================

    paid_transactions = sum(
        1
        for sale in all_today_sales
        if sale.display_payment_status
        == "PAID"
    )


    partial_transactions = sum(
        1
        for sale in all_today_sales
        if sale.display_payment_status
        == "PARTIAL"
    )


    unpaid_transactions = sum(
        1
        for sale in all_today_sales
        if sale.display_payment_status
        == "UNPAID"
    )


    # =========================================================
    # SALESPERSON OPTIONS
    # =========================================================

    salesperson_options = sorted(
        {
            sale.display_salesperson
            for sale in all_today_sales
            if (
                sale.display_salesperson
                and
                sale.display_salesperson
                != "No Salesperson"
            )
        },
        key=lambda name: name.lower()
    )


    # =========================================================
    # GET FILTERS
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()


    salesperson_filter = request.GET.get(
        "salesperson",
        ""
    ).strip()


    # ---------------------------------------------------------
    # Support old "salesman" URL parameter
    # ---------------------------------------------------------

    if not salesperson_filter:

        salesperson_filter = request.GET.get(
            "salesman",
            ""
        ).strip()


    payment_filter = request.GET.get(
        "payment_status",
        ""
    ).strip().upper()


    # =========================================================
    # FILTER SALES
    # =========================================================

    filtered_sales = []


    for sale in all_today_sales:

        # -----------------------------------------------------
        # SEARCH
        # -----------------------------------------------------

        if search:

            search_lower = search.lower()


            sale_id_text = str(
                sale.id
            ).lower()


            salesperson_text = (
                sale.display_salesperson
                or ""
            ).lower()


            client_text = (
                sale.display_client
                or ""
            ).lower()


            staff_text = ""


            if sale.staff:

                try:

                    staff_text = (
                        sale.staff.get_full_name()
                        or sale.staff.username
                        or ""
                    ).lower()

                except Exception:

                    staff_text = (
                        getattr(
                            sale.staff,
                            "username",
                            ""
                        )
                        or ""
                    ).lower()


            if (
                search_lower
                not in sale_id_text
                and
                search_lower
                not in salesperson_text
                and
                search_lower
                not in client_text
                and
                search_lower
                not in staff_text
            ):

                continue


        # -----------------------------------------------------
        # SALESPERSON FILTER
        # -----------------------------------------------------

        if salesperson_filter:

            if (
                sale.display_salesperson
                != salesperson_filter
            ):

                continue


        # -----------------------------------------------------
        # PAYMENT FILTER
        # -----------------------------------------------------

        if payment_filter:

            if (
                sale.display_payment_status
                != payment_filter
            ):

                continue


        filtered_sales.append(
            sale
        )


    # =========================================================
    # SALES PAGINATION
    # =========================================================

    sales_paginator = Paginator(
        filtered_sales,
        10
    )


    sales_page_number = request.GET.get(
        "page",
        1
    )


    sales_page_obj = (
        sales_paginator.get_page(
            sales_page_number
        )
    )


    # =========================================================
    # SALESPERSON PERFORMANCE
    # =========================================================

    salesperson_data = {}


    for sale in all_today_sales:

        salesperson_name = (
            sale.display_salesperson
        )


        if salesperson_name not in salesperson_data:

            salesperson_data[
                salesperson_name
            ] = {

                "salesman":
                    salesperson_name,

                "salesperson":
                    salesperson_name,

                "transactions":
                    0,

                "total_sales":
                    0,

                "total_paid":
                    0,

                "items_sold":
                    0,

            }


        # -----------------------------------------------------
        # TRANSACTIONS
        # -----------------------------------------------------

        salesperson_data[
            salesperson_name
        ]["transactions"] += 1


        # -----------------------------------------------------
        # TOTAL SALES
        # -----------------------------------------------------

        salesperson_data[
            salesperson_name
        ]["total_sales"] += (
            sale.total
            or 0
        )


        # -----------------------------------------------------
        # TOTAL PAYMENT
        # -----------------------------------------------------

        salesperson_data[
            salesperson_name
        ]["total_paid"] += (
            sale.payment
            or 0
        )


        # -----------------------------------------------------
        # ITEMS SOLD
        # -----------------------------------------------------

        for item in sale.items.all():

            salesperson_data[
                salesperson_name
            ]["items_sold"] += (
                item.quantity
                or 0
            )


    # =========================================================
    # SALESPERSON LIST
    # =========================================================

    salesman_sales = list(
        salesperson_data.values()
    )


    salesman_sales.sort(
        key=lambda item: item["total_sales"],
        reverse=True
    )


    # =========================================================
    # UNPAID + PARTIAL SALES
    # =========================================================

    unpaid_sales_list = [

        sale

        for sale in all_today_sales

        if sale.display_payment_status
        in [
            "UNPAID",
            "PARTIAL",
        ]

    ]


    # =========================================================
    # UNPAID TOTAL
    # =========================================================

    unpaid_total = sum(
        sale.display_balance
        for sale in unpaid_sales_list
    )


    # =========================================================
    # UNPAID PAGINATION
    # =========================================================

    unpaid_paginator = Paginator(
        unpaid_sales_list,
        10
    )


    unpaid_page_number = request.GET.get(
        "unpaid_page",
        1
    )


    unpaid_page_obj = (
        unpaid_paginator.get_page(
            unpaid_page_number
        )
    )


    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "today":
            today,


        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        "total_sales":
            total_sales,

        "total_transactions":
            total_transactions,

        "total_items":
            total_items,

        "total_discount":
            total_discount,

        "total_payment":
            total_payment,

        "average_transaction":
            average_transaction,

        "total_due":
            total_due,


        # -----------------------------------------------------
        # PAYMENT STATUS
        # -----------------------------------------------------

        "paid_transactions":
            paid_transactions,

        "unpaid_transactions":
            unpaid_transactions,

        "partial_transactions":
            partial_transactions,


        # -----------------------------------------------------
        # SALES
        # -----------------------------------------------------

        "recent_sales":
            sales_page_obj,

        "sales_page_obj":
            sales_page_obj,

        "sales_paginator":
            sales_paginator,


        # -----------------------------------------------------
        # SALESPERSON
        # -----------------------------------------------------

        "salesman_sales":
            salesman_sales,

        "salesperson_sales":
            salesman_sales,

        "salesman_options":
            salesperson_options,

        "salesperson_options":
            salesperson_options,


        # -----------------------------------------------------
        # UNPAID
        # -----------------------------------------------------

        "unpaid_sales":
            unpaid_page_obj,

        "unpaid_page_obj":
            unpaid_page_obj,

        "unpaid_paginator":
            unpaid_paginator,

        "unpaid_total":
            unpaid_total,


        # -----------------------------------------------------
        # FILTERS
        # -----------------------------------------------------

        "search":
            search,

        "salesman_filter":
            salesperson_filter,

        "salesperson_filter":
            salesperson_filter,

        "payment_filter":
            payment_filter,
    }


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "pages/pos.html",
        context
    )

@login_required
def admin_pos_detail(
    request,
    sale_id
):

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
        "admin/pos_detail.html",
        {
            "sale": sale
        }
    )


# ==========================================================
# SALES
# ==========================================================

@login_required
def sales(request):

    # =========================================================
    # BASE SALES QUERY
    # =========================================================

    sales_queryset = (
        Sale.objects
        .select_related(
            "staff",
            "salesperson",
            "discount_class",
        )
        .prefetch_related(
            "items__product",
        )
        .order_by("-created_at")
    )

    # =========================================================
    # SEARCH
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        search_filter = (

            # -------------------------------------------------
            # SALESPERSON
            # -------------------------------------------------

            Q(
                salesperson__first_name__icontains=search
            )

            |

            Q(
                salesperson__middle_name__icontains=search
            )

            |

            Q(
                salesperson__last_name__icontains=search
            )

            |

            Q(
                salesperson__contact_number__icontains=search
            )

            |

            Q(
                salesperson__email_address__icontains=search
            )

            # -------------------------------------------------
            # STAFF / USER
            # -------------------------------------------------

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

            # -------------------------------------------------
            # DATE SEARCH
            # -------------------------------------------------

            |

            Q(
                created_at__icontains=search
            )
        )

        # -----------------------------------------------------
        # SALE ID SEARCH
        # -----------------------------------------------------

        if search.isdigit():

            search_filter |= Q(
                id=int(search)
            )

        sales_queryset = (
            sales_queryset
            .filter(
                search_filter
            )
            .distinct()
        )

    # =========================================================
    # SALESPERSON FILTER
    # =========================================================

    salesperson_filter = request.GET.get(
        "salesperson",
        ""
    ).strip()

    if salesperson_filter:

        if salesperson_filter.isdigit():

            sales_queryset = sales_queryset.filter(
                salesperson_id=int(
                    salesperson_filter
                )
            )

    # =========================================================
    # PAYMENT STATUS FILTER
    # =========================================================

    payment_status = request.GET.get(
        "payment_status",
        ""
    ).strip().upper()

    if payment_status in [
        "PAID",
        "PARTIAL",
        "UNPAID",
    ]:

        sales_queryset = sales_queryset.filter(
            payment_status=payment_status
        )

    # =========================================================
    # DATE FILTER
    # =========================================================

    date_filter = request.GET.get(
        "date",
        ""
    ).strip()

    if date_filter:

        sales_queryset = sales_queryset.filter(
            created_at__date=date_filter
        )

    # =========================================================
    # SALESPERSON OPTIONS
    # =========================================================

    salesperson_options = (
        Salesperson.objects
        .filter(
            sales__isnull=False
        )
        .values(
            "id",
            "first_name",
            "middle_name",
            "last_name",
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
        )
    )

    # =========================================================
    # SUMMARY
    # =========================================================

    summary = sales_queryset.aggregate(

        total_sales=Sum(
            "total"
        ),

        total_discount=Sum(
            "discount_amount"
        ),

        average_sale=Avg(
            "total"
        ),

        total_payment=Sum(
            "payment"
        ),
    )

    total_transactions = (
        sales_queryset.count()
    )

    total_sales = (
        summary["total_sales"]
        or Decimal("0.00")
    )

    total_discount = (
        summary["total_discount"]
        or Decimal("0.00")
    )

    average_sale = (
        summary["average_sale"]
        or Decimal("0.00")
    )

    total_payment = (
        summary["total_payment"]
        or Decimal("0.00")
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        sales_queryset,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # Sales
        "sales": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,

        # Summary
        "total_transactions": total_transactions,
        "total_sales": total_sales,
        "total_discount": total_discount,
        "average_sale": average_sale,
        "total_payment": total_payment,

        # Filters
        "search": search,
        "salesperson_filter": salesperson_filter,
        "payment_status": payment_status,
        "date_filter": date_filter,

        # Salesperson options
        "salesperson_options": salesperson_options,
    }

    return render(
        request,
        "pages/sales.html",
        context
    )

@login_required
def sale_detail(request, sale_id):

    sale = get_object_or_404(
        Sale.objects
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class",
        )
        .prefetch_related(
            "items__product",
        ),
        id=sale_id
    )

    # =========================================================
    # AMOUNT DUE
    # =========================================================

    amount_due = sale.amount_due

    # =========================================================
    # PAYMENT STATUS
    # =========================================================

    payment_status = sale.payment_status

    context = {
        "sale": sale,
        "amount_due": amount_due,
        "payment_status": payment_status,
    }

    return render(
        request,
        "pages/sale_detail.html",
        context
    )

@login_required
def reports(request):

    # =========================================================
    # CURRENT DATE / TIME
    # =========================================================

    now = timezone.now()
    local_now = timezone.localtime(now)
    today = local_now.date()


    # =========================================================
    # PERIOD
    # =========================================================

    period = request.GET.get(
        "period",
        "daily"
    )

    if period not in [
        "daily",
        "weekly",
        "monthly",
    ]:
        period = "daily"


    # =========================================================
    # PERIOD RANGE
    # =========================================================

    if period == "daily":

        start_date = today
        end_date = today

    elif period == "weekly":

        days_since_monday = today.weekday()

        start_date = (
            today -
            timedelta(
                days=days_since_monday
            )
        )

        end_date = (
            start_date +
            timedelta(days=6)
        )

    else:

        start_date = today.replace(
            day=1
        )

        if today.month == 12:

            next_month = today.replace(
                year=today.year + 1,
                month=1,
                day=1
            )

        else:

            next_month = today.replace(
                month=today.month + 1,
                day=1
            )

        end_date = (
            next_month -
            timedelta(days=1)
        )


    # =========================================================
    # PERIOD DATETIME
    # =========================================================

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            datetime.min.time()
        )
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date,
            datetime.max.time()
        )
    )


    # =========================================================
    # SALES FOR SELECTED PERIOD
    # =========================================================

    period_sales = (
        Sale.objects
        .filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        )
        .select_related(
            "staff",
            "salesperson",
            "client",
            "discount_class",
        )
        .prefetch_related(
            "items__product"
        )
        .order_by(
            "-created_at"
        )
    )


    # =========================================================
    # SALES TOTALS
    # =========================================================

    sales_summary = (
        period_sales.aggregate(
            total_sales=Sum("total"),
            subtotal=Sum("subtotal"),
            discount_amount=Sum("discount_amount"),
            payment=Sum("payment"),
            change=Sum("change"),
        )
    )


    total_sales = (
        sales_summary["total_sales"]
        or Decimal("0.00")
    )

    total_subtotal = (
        sales_summary["subtotal"]
        or Decimal("0.00")
    )

    total_discount = (
        sales_summary["discount_amount"]
        or Decimal("0.00")
    )

    total_payment = (
        sales_summary["payment"]
        or Decimal("0.00")
    )

    total_change = (
        sales_summary["change"]
        or Decimal("0.00")
    )


    # =========================================================
    # TRANSACTIONS
    # =========================================================

    total_transactions = (
        period_sales.count()
    )


    # =========================================================
    # PAYMENT STATUS COUNTS
    # =========================================================

    paid_sales = (
        period_sales
        .filter(
            payment_status="PAID"
        )
        .count()
    )

    unpaid_sales = (
        period_sales
        .filter(
            payment_status="UNPAID"
        )
        .count()
    )

    partial_sales = (
        period_sales
        .filter(
            payment_status="PARTIAL"
        )
        .count()
    )


    # =========================================================
    # AMOUNT DUE
    # =========================================================

    total_amount_due = (
        total_sales -
        total_payment
    )

    if total_amount_due < 0:

        total_amount_due = Decimal(
            "0.00"
        )


    # =========================================================
    # AVERAGE SALE
    # =========================================================

    if total_transactions > 0:

        average_sale = (
            total_sales /
            Decimal(
                str(total_transactions)
            )
        )

    else:

        average_sale = Decimal(
            "0.00"
        )


    # =========================================================
    # TOTAL ITEMS SOLD
    # =========================================================

    items_summary = (
        SaleItem.objects
        .filter(
            sale__in=period_sales
        )
        .aggregate(
            quantity=Sum("quantity")
        )
    )

    total_items = (
        items_summary["quantity"]
        or 0
    )


    # =========================================================
    # SALE ITEM DISCOUNTS
    # =========================================================

    item_discount_summary = (
        SaleItem.objects
        .filter(
            sale__in=period_sales
        )
        .aggregate(
            total=Sum("discount_amount")
        )
    )

    total_item_discount = (
        item_discount_summary["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # CHART DATA
    #
    # We intentionally do not use:
    #
    # TruncDay
    # TruncWeek
    # TruncMonth
    #
    # This avoids SQLite timezone issues.
    # =========================================================

    chart_data = {}


    for sale in period_sales:

        if not sale.created_at:
            continue


        sale_datetime = timezone.localtime(
            sale.created_at
        )

        sale_date = sale_datetime.date()


        # =====================================================
        # DAILY
        # =====================================================

        if period == "daily":

            key = sale_date.strftime(
                "%b %d"
            )


        # =====================================================
        # WEEKLY
        # =====================================================

        elif period == "weekly":

            monday = (
                sale_date -
                timedelta(
                    days=sale_date.weekday()
                )
            )

            key = monday.strftime(
                "%b %d, %Y"
            )


        # =====================================================
        # MONTHLY
        # =====================================================

        else:

            key = sale_date.strftime(
                "%b %Y"
            )


        # =====================================================
        # CREATE ENTRY
        # =====================================================

        if key not in chart_data:

            chart_data[key] = {
                "sales": Decimal(
                    "0.00"
                ),
                "transactions": 0,
            }


        # =====================================================
        # ADD SALE
        # =====================================================

        chart_data[key]["sales"] += (
            sale.total
            or Decimal("0.00")
        )

        chart_data[key]["transactions"] += 1


    # =========================================================
    # CHART ARRAYS
    # =========================================================

    chart_labels = []
    chart_sales = []
    chart_transactions = []


    for label, values in chart_data.items():

        chart_labels.append(
            label
        )

        chart_sales.append(
            float(
                values["sales"]
            )
        )

        chart_transactions.append(
            values["transactions"]
        )


    # =========================================================
    # CLIENT SALES
    # =========================================================

    client_sales = (
        period_sales
        .filter(
            client__isnull=False
        )
        .values(
            "client",
            "client__first_name",
            "client__middle_name",
            "client__last_name",
            "client__organization",
        )
        .annotate(
            total_sales=Sum("total"),
            transaction_count=Count("id"),
        )
        .order_by(
            "-total_sales"
        )
    )


    # =========================================================
    # SALESPERSON SALES
    # =========================================================

    salesperson_sales = (
        period_sales
        .filter(
            salesperson__isnull=False
        )
        .values(
            "salesperson",
            "salesperson__first_name",
            "salesperson__middle_name",
            "salesperson__last_name",
        )
        .annotate(
            total_sales=Sum("total"),
            transaction_count=Count("id"),
        )
        .order_by(
            "-total_sales"
        )
    )


    # =========================================================
    # DISCOUNT CLASS SALES
    # =========================================================

    discount_class_sales = (
        period_sales
        .filter(
            discount_class__isnull=False
        )
        .values(
            "discount_class",
            "discount_class__code",
            "discount_class__name",
        )
        .annotate(
            total_sales=Sum("total"),
            discount_total=Sum("discount_amount"),
            transaction_count=Count("id"),
        )
        .order_by(
            "-total_sales"
        )
    )


    # =========================================================
    # PRODUCT SALES
    # =========================================================

    product_sales = (
        SaleItem.objects
        .filter(
            sale__in=period_sales
        )
        .values(
            "product",
            "product__product_model",
            "product__description",
            "product__category",
        )
        .annotate(
            quantity_sold=Sum("quantity"),
            gross_sales=Sum("subtotal"),
            discount_total=Sum("discount_amount"),
            net_sales=Sum("total"),
            transaction_count=Count(
                "sale",
                distinct=True
            ),
        )
        .order_by(
            "-net_sales"
        )
    )


    # =========================================================
    # INVENTORY TRANSACTIONS
    # =========================================================

    inventory_transactions = (
        InventoryTransaction.objects
        .filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        )
        .select_related(
            "product",
            "created_by",
        )
        .order_by(
            "-created_at"
        )
    )


    # =========================================================
    # INVENTORY SUMMARY
    # =========================================================

    inventory_summary = (
        inventory_transactions
        .values(
            "transaction_type"
        )
        .annotate(
            quantity=Sum("quantity"),
            transactions=Count("id"),
        )
    )


    inventory_stock_in = 0
    inventory_stock_out = 0
    inventory_adjustment = 0

    inventory_stock_in_transactions = 0
    inventory_stock_out_transactions = 0
    inventory_adjustment_transactions = 0


    for row in inventory_summary:

        transaction_type = (
            row["transaction_type"]
        )

        quantity = (
            row["quantity"]
            or 0
        )

        transactions = (
            row["transactions"]
            or 0
        )


        if transaction_type == "IN":

            inventory_stock_in = quantity

            inventory_stock_in_transactions = (
                transactions
            )


        elif transaction_type == "OUT":

            inventory_stock_out = quantity

            inventory_stock_out_transactions = (
                transactions
            )


        elif transaction_type == "ADJUSTMENT":

            inventory_adjustment = quantity

            inventory_adjustment_transactions = (
                transactions
            )


    # =========================================================
    # PRODUCT / INVENTORY OVERVIEW
    # =========================================================

    products = (
        Product.objects.all()
    )


    # =========================================================
    # TOTAL PRODUCTS
    # =========================================================

    total_products = (
        products.count()
    )


    # =========================================================
    # TOTAL STOCK QUANTITY
    # =========================================================

    total_stock_quantity = (
        products.aggregate(
            total=Sum("qty")
        )["total"]
        or 0
    )


    # =========================================================
    # TOTAL STOCK VALUE
    #
    # Calculate in Python:
    #
    # price * qty
    #
    # This avoids database expression problems between
    # DecimalField and IntegerField, especially with SQLite.
    # =========================================================

    total_stock_value = Decimal(
        "0.00"
    )


    for product in products:

        price = (
            product.price
            or Decimal("0.00")
        )

        quantity = (
            product.qty
            or 0
        )

        total_stock_value += (
            price *
            quantity
        )


    # =========================================================
    # LOW STOCK
    # =========================================================

    low_stock_products = (
        products
        .filter(
            qty__gt=0,
            qty__lte=models.F(
                "low_stock_threshold"
            )
        )
        .order_by(
            "qty",
            "product_model"
        )
    )


    # =========================================================
    # OUT OF STOCK
    # =========================================================

    out_of_stock_products = (
        products
        .filter(
            qty=0
        )
        .order_by(
            "product_model"
        )
    )


    # =========================================================
    # IN STOCK
    # =========================================================

    in_stock_products = (
        products
        .filter(
            qty__gt=0
        )
    )


    # =========================================================
    # PRODUCT COUNTS
    # =========================================================

    low_stock_count = (
        low_stock_products.count()
    )

    out_of_stock_count = (
        out_of_stock_products.count()
    )

    in_stock_count = (
        in_stock_products.count()
    )


    # =========================================================
    # CLIENT COUNTS
    #
    # These are overall client records, not period-limited.
    # =========================================================

    total_clients = (
        Client.objects.count()
    )

    active_clients = (
        Client.objects
        .filter(
            is_active=True
        )
        .count()
    )

    inactive_clients = (
        Client.objects
        .filter(
            is_active=False
        )
        .count()
    )


    # =========================================================
    # SALESPERSON COUNTS
    #
    # These are overall salesperson records.
    # =========================================================

    total_salespersons = (
        Salesperson.objects.count()
    )

    active_salespersons = (
        Salesperson.objects
        .filter(
            is_active=True
        )
        .count()
    )

    inactive_salespersons = (
        Salesperson.objects
        .filter(
            is_active=False
        )
        .count()
    )


    # =========================================================
    # DISCOUNT CLASS COUNTS
    # =========================================================

    total_discount_classes = (
        DiscountClass.objects.count()
    )


    # =========================================================
    # RECENT SALES
    # =========================================================

    recent_sales = (
        period_sales[:10]
    )


    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # -----------------------------------------------------
        # PERIOD
        # -----------------------------------------------------

        "period": period,

        "start_date": start_date,

        "end_date": end_date,

        "current_date": local_now,


        # -----------------------------------------------------
        # SALES
        # -----------------------------------------------------

        "total_sales": total_sales,

        "total_subtotal": total_subtotal,

        "total_transactions": total_transactions,

        "total_items": total_items,

        "average_sale": average_sale,

        "total_discount": total_discount,

        "total_item_discount": total_item_discount,

        "total_payment": total_payment,

        "total_change": total_change,

        "total_amount_due": total_amount_due,


        # -----------------------------------------------------
        # PAYMENT STATUS
        # -----------------------------------------------------

        "paid_sales": paid_sales,

        "unpaid_sales": unpaid_sales,

        "partial_sales": partial_sales,


        # -----------------------------------------------------
        # CHART
        # -----------------------------------------------------

        "chart_labels": chart_labels,

        "chart_sales": chart_sales,

        "chart_transactions": chart_transactions,


        # -----------------------------------------------------
        # CLIENT REPORT
        # -----------------------------------------------------

        "client_sales": client_sales,

        "total_clients": total_clients,

        "active_clients": active_clients,

        "inactive_clients": inactive_clients,


        # -----------------------------------------------------
        # SALESPERSON REPORT
        # -----------------------------------------------------

        "salesperson_sales": salesperson_sales,

        "total_salespersons": total_salespersons,

        "active_salespersons": active_salespersons,

        "inactive_salespersons": inactive_salespersons,


        # -----------------------------------------------------
        # DISCOUNT REPORT
        # -----------------------------------------------------

        "discount_class_sales": discount_class_sales,

        "total_discount_classes": total_discount_classes,


        # -----------------------------------------------------
        # PRODUCT SALES REPORT
        # -----------------------------------------------------

        "product_sales": product_sales,


        # -----------------------------------------------------
        # INVENTORY
        # -----------------------------------------------------

        "inventory_transactions": inventory_transactions,

        "inventory_stock_in": inventory_stock_in,

        "inventory_stock_out": inventory_stock_out,

        "inventory_adjustment": inventory_adjustment,

        "inventory_stock_in_transactions":
            inventory_stock_in_transactions,

        "inventory_stock_out_transactions":
            inventory_stock_out_transactions,

        "inventory_adjustment_transactions":
            inventory_adjustment_transactions,


        # -----------------------------------------------------
        # PRODUCT / STOCK
        # -----------------------------------------------------

        "total_products": total_products,

        "total_stock_quantity": total_stock_quantity,

        "total_stock_value": total_stock_value,

        "in_stock_count": in_stock_count,

        "low_stock_count": low_stock_count,

        "out_of_stock_count": out_of_stock_count,

        "low_stock_products": low_stock_products,

        "out_of_stock_products": out_of_stock_products,


        # -----------------------------------------------------
        # RECENT SALES
        # -----------------------------------------------------

        "recent_sales": recent_sales,

    }


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "pages/reports.html",
        context
    )
# =========================================================
# CLIENT LIST
# =========================================================

@login_required
def client_list(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()

    # ======================================================
    # GET ACTIVE CLIENTS ONLY
    # ======================================================

    clients = (
        Client.objects
        .filter(is_active=True)
        .order_by("-id")
    )

    # ======================================================
    # SEARCH
    # ======================================================

    if search:

        clients = clients.filter(

            Q(
                first_name__icontains=search
            )

            | Q(
                middle_name__icontains=search
            )

            | Q(
                last_name__icontains=search
            )

            | Q(
                organization__icontains=search
            )

            | Q(
                address__icontains=search
            )

            | Q(
                contact_number__icontains=search
            )

            | Q(
                email_address__icontains=search
            )

        )

    # ======================================================
    # TOTAL ACTIVE CLIENTS
    # ======================================================

    total_clients = clients.count()

    # ======================================================
    # PAGINATION
    # ======================================================

    paginator = Paginator(
        clients,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # ======================================================
    # RENDER
    # ======================================================

    return render(
        request,
        "client/client.html",
        {
            "clients": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "search": search,
            "total_clients": total_clients,
        },
    )


# =========================================================
# ADD CLIENT
# =========================================================

@login_required
def add_client(request):

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        # ==================================================
        # GET FORM DATA
        # ==================================================

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        middle_name = request.POST.get(
            "middle_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        organization = request.POST.get(
            "organization",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        contact_number = request.POST.get(
            "contact_number",
            ""
        ).strip()

        email_address = request.POST.get(
            "email_address",
            ""
        ).strip()

        # ==================================================
        # SALESPERSON
        # ==================================================

        salesperson_id = request.POST.get(
            "salesperson",
            ""
        ).strip()

        # ==================================================
        # BUSINESS PERMIT
        # ==================================================

        business_permit = request.FILES.get(
            "business_permit"
        )

        # ==================================================
        # STATUS
        # ==================================================

        is_active = (
            request.POST.get("is_active") == "on"
        )

        # ==================================================
        # VALIDATION
        # ==================================================

        if not first_name:

            return render(
                request,
                "client/client_form.html",
                {
                    "error": "First name is required.",
                    "is_edit": False,
                    "client": None,

                    "salespersons": Salesperson.objects.filter(
                        is_active=True
                    ),
                }
            )

        if not last_name:

            return render(
                request,
                "client/client_form.html",
                {
                    "error": "Last name is required.",
                    "is_edit": False,
                    "client": None,

                    "salespersons": Salesperson.objects.filter(
                        is_active=True
                    ),
                }
            )

        # ==================================================
        # VALIDATE EMAIL
        # ==================================================

        if email_address:

            try:

                validate_email(
                    email_address
                )

            except ValidationError:

                return render(
                    request,
                    "client/client_form.html",
                    {
                        "error": (
                            "Please enter a valid "
                            "email address."
                        ),

                        "is_edit": False,
                        "client": None,

                        "salespersons": Salesperson.objects.filter(
                            is_active=True
                        ),
                    }
                )

        # ==================================================
        # GET SALESPERSON
        # ==================================================

        salesperson = None

        if salesperson_id:

            salesperson = get_object_or_404(
                Salesperson,
                id=salesperson_id,
                is_active=True
            )

        # ==================================================
        # CREATE CLIENT
        # ==================================================

        client = Client.objects.create(

            first_name=first_name,

            middle_name=(
                middle_name
                or None
            ),

            last_name=last_name,

            organization=(
                organization
                or None
            ),

            address=(
                address
                or None
            ),

            contact_number=(
                contact_number
                or None
            ),

            email_address=(
                email_address
                or None
            ),

            salesperson=salesperson,

            business_permit=business_permit,

            is_active=is_active,
        )

        # ==================================================
        # SUCCESS
        # ==================================================

        return redirect(
            "client-list"
        )

    # ======================================================
    # GET
    # ======================================================

    return render(
        request,
        "client/client_form.html",
        {
            "is_edit": False,
            "client": None,
            "error": None,

            "salespersons": Salesperson.objects.filter(
                is_active=True
            ),
        }
    )


# =========================================================
# UPDATE CLIENT
# =========================================================

@login_required
def update_client(
    request,
    client_id
):

    client = get_object_or_404(
        Client,
        id=client_id
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        # ==================================================
        # GET FORM DATA
        # ==================================================

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        middle_name = request.POST.get(
            "middle_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        organization = request.POST.get(
            "organization",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        contact_number = request.POST.get(
            "contact_number",
            ""
        ).strip()

        email_address = request.POST.get(
            "email_address",
            ""
        ).strip()

        # ==================================================
        # SALESPERSON
        # ==================================================

        salesperson_id = request.POST.get(
            "salesperson",
            ""
        ).strip()

        # ==================================================
        # BUSINESS PERMIT
        # ==================================================

        business_permit = request.FILES.get(
            "business_permit"
        )

        # ==================================================
        # STATUS
        # ==================================================

        is_active = (
            request.POST.get("is_active") == "on"
        )

        # ==================================================
        # VALIDATION
        # ==================================================

        if not first_name:

            return render(
                request,
                "client/client_form.html",
                {
                    "client": client,

                    "error": (
                        "First name is required."
                    ),

                    "is_edit": True,

                    "salespersons": Salesperson.objects.filter(
                        is_active=True
                    ),
                }
            )

        if not last_name:

            return render(
                request,
                "client/client_form.html",
                {
                    "client": client,

                    "error": (
                        "Last name is required."
                    ),

                    "is_edit": True,

                    "salespersons": Salesperson.objects.filter(
                        is_active=True
                    ),
                }
            )

        # ==================================================
        # VALIDATE EMAIL
        # ==================================================

        if email_address:

            try:

                validate_email(
                    email_address
                )

            except ValidationError:

                return render(
                    request,
                    "client/client_form.html",
                    {
                        "client": client,

                        "error": (
                            "Please enter a valid "
                            "email address."
                        ),

                        "is_edit": True,

                        "salespersons": Salesperson.objects.filter(
                            is_active=True
                        ),
                    }
                )

        # ==================================================
        # GET SALESPERSON
        # ==================================================

        salesperson = None

        if salesperson_id:

            salesperson = get_object_or_404(
                Salesperson,
                id=salesperson_id,
                is_active=True
            )

        # ==================================================
        # UPDATE CLIENT
        # ==================================================

        client.first_name = first_name

        client.middle_name = (
            middle_name
            or None
        )

        client.last_name = last_name

        client.organization = (
            organization
            or None
        )

        client.address = (
            address
            or None
        )

        client.contact_number = (
            contact_number
            or None
        )

        client.email_address = (
            email_address
            or None
        )

        # ==================================================
        # SALESPERSON
        # ==================================================

        client.salesperson = salesperson

        # ==================================================
        # BUSINESS PERMIT
        # ==================================================

        if business_permit:

            client.business_permit = business_permit

        # ==================================================
        # STATUS
        # ==================================================

        client.is_active = is_active

        # ==================================================
        # SAVE
        # ==================================================

        client.save()

        # ==================================================
        # SUCCESS
        # ==================================================

        return redirect(
            "client-list"
        )

    # ======================================================
    # GET
    # ======================================================

    return render(
        request,
        "client/client_form.html",
        {
            "client": client,
            "is_edit": True,
            "error": None,

            "salespersons": Salesperson.objects.filter(
                is_active=True
            ),
        }
    )

@login_required
def delete_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method == "POST":
        client.is_active = False
        client.save(update_fields=["is_active"])

        return redirect("client-list")

    return redirect("client-list")

@login_required
@user_passes_test(is_superuser)
def transactions(request):

    # =========================================================
    # BASE QUERY
    # =========================================================

    transactions = (
        Sale.objects
        .select_related(
            "staff",
            "salesperson",
            "discount_class",
            "client",
        )
        .prefetch_related(
            "items__product",
        )
        .order_by("-created_at")
    )


    # =========================================================
    # SEARCH
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        search_filter = (
            Q(
                salesperson__first_name__icontains=search
            )
            | Q(
                salesperson__middle_name__icontains=search
            )
            | Q(
                salesperson__last_name__icontains=search
            )
            | Q(
                staff__username__icontains=search
            )
            | Q(
                client__organization__icontains=search
            )
        )

        # -----------------------------------------------------
        # Search transaction ID if number
        # -----------------------------------------------------

        if search.isdigit():

            search_filter |= Q(
                id=int(search)
            )

        transactions = (
            transactions
            .filter(search_filter)
            .distinct()
        )


    # =========================================================
    # SALESPERSON FILTER
    # =========================================================

    salesperson_id = request.GET.get(
        "salesperson",
        ""
    ).strip()

    if salesperson_id:

        transactions = transactions.filter(
            salesperson_id=salesperson_id
        )


    # =========================================================
    # PAYMENT STATUS
    # =========================================================

    payment_status = request.GET.get(
        "payment_status",
        ""
    ).strip()

    if payment_status:

        transactions = transactions.filter(
            payment_status=payment_status
        )


    # =========================================================
    # DATE FROM
    # =========================================================

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    if date_from:

        transactions = transactions.filter(
            created_at__date__gte=date_from
        )


    # =========================================================
    # DATE TO
    # =========================================================

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    if date_to:

        transactions = transactions.filter(
            created_at__date__lte=date_to
        )


    # =========================================================
    # SALESPERSON LIST
    # =========================================================

    salespersons = (
        Salesperson.objects
        .filter(
            is_active=True
        )
        .order_by(
            "last_name",
            "first_name"
        )
    )


    # =========================================================
    # CLIENT LIST
    #
    # Client is completely independent from Salesperson.
    #
    # IMPORTANT:
    # Do NOT use client.salespersons.
    # =========================================================

    clients = (
        Client.objects
        .filter(
            is_active=True
        )
        .order_by(
            "last_name",
            "first_name"
        )
    )


    # =========================================================
    # ORGANIZATION LIST
    # =========================================================

    organizations = (
        Client.objects
        .exclude(
            organization__isnull=True
        )
        .exclude(
            organization__exact=""
        )
        .values_list(
            "organization",
            flat=True
        )
        .distinct()
        .order_by(
            "organization"
        )
    )


    # =========================================================
    # SUMMARY
    # =========================================================

    total_transactions = transactions.count()

    total_sales = (
        transactions.aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    total_paid = (
        transactions.aggregate(
            total=Sum("payment")
        )["total"]
        or 0
    )

    total_due = (
        total_sales
        - total_paid
    )

    if total_due < 0:
        total_due = 0


    # =========================================================
    # PAYMENT COUNTS
    # =========================================================

    paid_count = (
        transactions
        .filter(
            payment_status="PAID"
        )
        .count()
    )

    unpaid_count = (
        transactions
        .filter(
            payment_status="UNPAID"
        )
        .count()
    )

    partial_count = (
        transactions
        .filter(
            payment_status="PARTIAL"
        )
        .count()
    )


    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        transactions,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    # =========================================================
    # KEEP FILTERS DURING PAGINATION
    # =========================================================

    filter_params = request.GET.copy()

    if "page" in filter_params:

        del filter_params["page"]


    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "page_obj":
            page_obj,

        "transactions":
            page_obj.object_list,

        "salespersons":
            salespersons,

        "clients":
            clients,

        "organizations":
            organizations,

        "search":
            search,

        "selected_salesperson":
            salesperson_id,

        "selected_payment_status":
            payment_status,

        "date_from":
            date_from,

        "date_to":
            date_to,

        "filter_params":
            filter_params.urlencode(),

        "total_transactions":
            total_transactions,

        "total_sales":
            total_sales,

        "total_paid":
            total_paid,

        "total_due":
            total_due,

        "paid_count":
            paid_count,

        "unpaid_count":
            unpaid_count,

        "partial_count":
            partial_count,
    }


    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "transactions/transactions.html",
        context
    )