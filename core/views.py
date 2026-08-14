from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import Product, InventoryTransaction, Sale, SaleItem
from openpyxl import load_workbook
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import Coalesce
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time, timedelta
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@login_required(login_url="login")
def dashboard(request):

    today = timezone.localdate()

    # -----------------------------------------
    # TODAY'S SALES
    # -----------------------------------------

    today_sales_qs = Sale.objects.filter(
        created_at__date=today
    )

    total_sales = today_sales_qs.aggregate(
        total=Sum("total")
    )["total"] or 0

    total_transactions = today_sales_qs.count()


    # -----------------------------------------
    # ITEMS SOLD TODAY
    # -----------------------------------------

    total_items = SaleItem.objects.filter(
        sale__created_at__date=today
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0


    # -----------------------------------------
    # DISCOUNTS
    # -----------------------------------------

    total_discount = today_sales_qs.aggregate(
        total=Sum("discount_amount")
    )["total"] or 0


    # -----------------------------------------
    # INVENTORY
    # -----------------------------------------

    total_products = Product.objects.count()

    low_stock = Product.objects.filter(
        qty__gt=0,
        qty__lte=10
    ).count()

    out_of_stock = Product.objects.filter(
        qty=0
    ).count()


    # -----------------------------------------
    # MONTHLY SALES
    # -----------------------------------------

    current_month = today.month
    current_year = today.year

    monthly_sales = Sale.objects.filter(
        created_at__year=current_year,
        created_at__month=current_month
    ).aggregate(
        total=Sum("total")
    )["total"] or 0


    # -----------------------------------------
    # YESTERDAY
    # -----------------------------------------

    yesterday = today - timezone.timedelta(days=1)

    yesterday_sales = Sale.objects.filter(
        created_at__date=yesterday
    ).aggregate(
        total=Sum("total")
    )["total"] or 0


    return render(
        request,
        "pages/dashboard.html",
        {
            "total_sales": total_sales,
            "total_transactions": total_transactions,
            "total_items": total_items,
            "total_discount": total_discount,

            "total_products": total_products,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,

            "monthly_sales": monthly_sales,
            "yesterday_sales": yesterday_sales,

            "today": today,
        }
    )

@login_required
@user_passes_test(is_superuser)
def staff_list(request):

    users = User.objects.all().order_by("username")

    return render(request, "users/staff_list.html", {
        "users": users
    })

@login_required
@user_passes_test(is_superuser)
def add_staff(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        # Checkbox
        is_staff = request.POST.get("is_staff") == "on"

        # ==============================
        # VALIDATION
        # ==============================

        if not name:
            messages.error(request, "Name is required.")
            return redirect("add_staff")

        if not username:
            messages.error(request, "Username is required.")
            return redirect("add_staff")

        if not password1:
            messages.error(request, "Password is required.")
            return redirect("add_staff")

        if password1 != password2:
            messages.error(
                request,
                "Passwords do not match."
            )
            return redirect("add_staff")

        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                "Username already exists."
            )
            return redirect("add_staff")

        # ==============================
        # CREATE STAFF
        # ==============================

        user = User.objects.create(
            first_name=name,
            username=username,
            password=make_password(password1),
            is_staff=is_staff,
            is_superuser=False
        )

        messages.success(
            request,
            f"Staff account '{user.username}' created successfully."
        )

        return redirect("staff_list")

    return render(
        request,
        "users/staff_form.html"
    )


@login_required
@user_passes_test(is_superuser)
def add_staff(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        is_staff = request.POST.get("is_staff") == "on"

        # ==============================
        # VALIDATION
        # ==============================

        if not name:
            messages.error(request, "Name is required.")
            return redirect("add-user")

        if not username:
            messages.error(request, "Username is required.")
            return redirect("add-user")

        if not password1:
            messages.error(request, "Password is required.")
            return redirect("add-user")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("add-user")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("add-user")

        # ==============================
        # CREATE USER
        # ==============================

        user = User.objects.create(
            first_name=name,
            username=username,
            is_staff=is_staff,
            is_superuser=False
        )

        user.set_password(password1)
        user.save()

        messages.success(
            request,
            f"Staff account '{user.username}' created successfully."
        )

        return redirect("staff_list")

    return render(
        request,
        "users/staff_form.html",
        {
            "is_edit": False,
            "user": None,
        }
    )


@login_required
@user_passes_test(is_superuser)
def edit_user(request, user_id):

    user = get_object_or_404(
        User,
        id=user_id
    )

    # ==========================================
    # PROTECT SUPERUSER
    # ==========================================

    if user.is_superuser:

        messages.error(
            request,
            "The superuser account is protected."
        )

        return redirect("staff_list")


    # ==========================================
    # POST
    # ==========================================

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

        is_staff = (
            request.POST.get("is_staff") == "on"
        )


        # ==========================================
        # VALIDATE NAME
        # ==========================================

        if not name:

            messages.error(
                request,
                "Name is required."
            )

            return redirect(
                "edit-user",
                user_id=user.id
            )


        # ==========================================
        # VALIDATE USERNAME
        # ==========================================

        if not username:

            messages.error(
                request,
                "Username is required."
            )

            return redirect(
                "edit-user",
                user_id=user.id
            )


        # ==========================================
        # CHECK USERNAME
        # ==========================================

        if User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "Username already exists."
            )

            return redirect(
                "edit-user",
                user_id=user.id
            )


        # ==========================================
        # PASSWORD
        # ==========================================

        if password1 or password2:

            if password1 != password2:

                messages.error(
                    request,
                    "Passwords do not match."
                )

                return redirect(
                    "edit-user",
                    user_id=user.id
                )

            if len(password1) < 8:

                messages.error(
                    request,
                    "Password must be at least 8 characters."
                )

                return redirect(
                    "edit-user",
                    user_id=user.id
                )

            user.set_password(password1)


        # ==========================================
        # UPDATE USER
        # ==========================================

        user.first_name = name
        user.username = username
        user.is_staff = is_staff

        # Never allow this page to create a superuser
        user.is_superuser = False

        user.save()


        messages.success(
            request,
            f"Staff account '{user.username}' updated successfully."
        )

        return redirect("staff_list")


    # ==========================================
    # DISPLAY FORM
    # ==========================================

    return render(
        request,
        "users/staff_form.html",
        {
            "is_edit": True,
            "user": user,
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


#Products
@login_required
@user_passes_test(is_superuser)
def product_list(request):

    products = Product.objects.all()

    return render(
        request,
        "products/product_list.html",
        {
            "products": products
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

            qty=qty

        )


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
        # UPDATE
        # ==========================================

        product.product_model = product_model

        product.description = description

        product.category = category

        product.price = price

        product.qty = qty

        product.save()


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
            # ==========================================

            expected_headers = [
                "product_model",
                "description",
                "category",
                "price",
                "qty",
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

                # Skip completely empty rows

                if not any(
                    value is not None
                    for value in row
                ):
                    continue


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

                Product.objects.create(

                    product_model=product_model,

                    description=description,

                    category=category,

                    price=price,

                    qty=qty

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

    products = Product.objects.all().order_by(
        "product_model"
    )


    # ==========================================
    # SEARCH
    # ==========================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        products = products.filter(
            Q(product_model__icontains=search) |
            Q(category__icontains=search)
        )


    # ==========================================
    # CATEGORY
    # ==========================================

    selected_category = request.GET.get(
        "category",
        ""
    )


    if selected_category:

        products = products.filter(
            category=selected_category
        )


    # ==========================================
    # STATUS
    # ==========================================

    selected_status = request.GET.get(
        "stock_status",
        ""
    )


    if selected_status == "in":

        products = products.filter(
            qty__gt=10
        )


    elif selected_status == "low":

        products = products.filter(
            qty__gt=0,
            qty__lte=10
        )


    elif selected_status == "out":

        products = products.filter(
            qty=0
        )


    # ==========================================
    # STOCK VALUE
    # ==========================================

    products = products.annotate(
        stock_value=F("price") * F("qty")
    )


    # ==========================================
    # SUMMARY
    # ==========================================

    total_products = Product.objects.count()


    total_stock = Product.objects.aggregate(
        total=Coalesce(
            Sum("qty"),
            0
        )
    )["total"]


    low_stock = Product.objects.filter(
        qty__gt=0,
        qty__lte=10
    ).count()


    out_of_stock = Product.objects.filter(
        qty=0
    ).count()


    categories = Product.objects.values_list(
        "category",
        flat=True
    ).distinct().order_by(
        "category"
    )


    return render(
        request,
        "inventory/inventory.html",
        {
            "products": products,

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


    return render(

        request,

        "inventory/inventory_history.html",

        {

            "transactions": transactions,

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

    today = timezone.localdate()

    # ==========================================
    # TODAY'S SALES
    # ==========================================

    today_sales = Sale.objects.filter(
        created_at__date=today
    )

    total_sales = today_sales.aggregate(
        total=Sum("total")
    )["total"] or 0

    total_transactions = today_sales.count()

    total_items = today_sales.aggregate(
        items=Sum("items__quantity")
    )["items"] or 0

    total_discount = today_sales.aggregate(
        discount=Sum("discount_amount")
    )["discount"] or 0

    total_payment = today_sales.aggregate(
        payment=Sum("payment")
    )["payment"] or 0

    average_transaction = today_sales.aggregate(
        average=Avg("total")
    )["average"] or 0

    # ==========================================
    # RECENT TRANSACTIONS
    # ==========================================

    recent_sales = Sale.objects.select_related(
        "staff",
        "discount_class"
    ).prefetch_related(
        "items__product"
    ).order_by(
        "-created_at"
    )[:20]

    # ==========================================
    # STAFF PERFORMANCE
    # ==========================================

    staff_sales = (
        today_sales
        .values(
            "staff__id",
            "staff__username",
            "staff__first_name",
            "staff__last_name"
        )
        .annotate(
            transactions=Count("id"),
            total_sales=Sum("total"),
            items_sold=Sum("items__quantity")
        )
        .order_by("-total_sales")
    )

    # ==========================================
    # CONTEXT
    # ==========================================

    context = {
        "today": today,

        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "total_items": total_items,
        "total_discount": total_discount,
        "total_payment": total_payment,
        "average_transaction": average_transaction,

        "recent_sales": recent_sales,
        "staff_sales": staff_sales,
    }

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


@login_required
def sales(request):
    sales = (
        Sale.objects
        .select_related("staff", "discount_class")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    return render(
        request,
        "pages/sales.html",
        {
            "sales": sales,
        }
    )


@login_required
def sale_detail(request, sale_id):
    sale = get_object_or_404(
        Sale.objects
        .select_related("staff", "discount_class")
        .prefetch_related("items__product"),
        id=sale_id
    )

    return render(
        request,
        "pages/sale_detail.html",
        {
            "sale": sale,
        }
    )

@login_required
def reports(request):

    # =========================================================
    # CURRENT DATE / TIME
    # =========================================================
    now = timezone.localtime()

    # =========================================================
    # PERIOD
    # =========================================================
    period = request.GET.get("period", "daily")

    if period not in ["daily", "weekly", "monthly"]:
        period = "daily"

    # =========================================================
    # BASE SALES QUERY
    # =========================================================
    sales = Sale.objects.all()

    # =========================================================
    # TOTAL SALES
    # =========================================================
    total_sales = sales.aggregate(
        total=Sum("total")
    )["total"] or 0

    # =========================================================
    # TOTAL TRANSACTIONS
    # =========================================================
    total_transactions = sales.count()

    # =========================================================
    # TOTAL ITEMS SOLD
    # =========================================================
    total_items = SaleItem.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    # =========================================================
    # AVERAGE SALE
    # =========================================================
    average_sale = (
        total_sales / total_transactions
        if total_transactions > 0
        else 0
    )

    # =========================================================
    # CHART DATA
    # =========================================================

    if period == "daily":

        chart_queryset = (
            sales
            .annotate(period_date=TruncDay("created_at"))
            .values("period_date")
            .annotate(
                sales_total=Sum("total"),
                transaction_count=Count("id")
            )
            .order_by("period_date")
        )

    elif period == "weekly":

        chart_queryset = (
            sales
            .annotate(period_date=TruncWeek("created_at"))
            .values("period_date")
            .annotate(
                sales_total=Sum("total"),
                transaction_count=Count("id")
            )
            .order_by("period_date")
        )

    else:

        chart_queryset = (
            sales
            .annotate(period_date=TruncMonth("created_at"))
            .values("period_date")
            .annotate(
                sales_total=Sum("total"),
                transaction_count=Count("id")
            )
            .order_by("period_date")
        )

    # =========================================================
    # PREPARE CHART DATA
    # =========================================================

    chart_labels = []
    chart_sales = []
    chart_transactions = []

    for row in chart_queryset:

        date_value = row["period_date"]

        if period == "daily":
            label = timezone.localtime(date_value).strftime("%b %d")

        elif period == "weekly":
            label = timezone.localtime(date_value).strftime(
                "%b %d, %Y"
            )

        else:
            label = timezone.localtime(date_value).strftime(
                "%b %Y"
            )

        chart_labels.append(label)

        chart_sales.append(
            float(row["sales_total"] or 0)
        )

        chart_transactions.append(
            row["transaction_count"]
        )

    # =========================================================
    # RECENT SALES
    # =========================================================

    recent_sales = (
        Sale.objects
        .select_related("staff", "discount_class")
        .prefetch_related("items__product")
        .order_by("-created_at")[:10]
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {
        "period": period,

        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "total_items": total_items,
        "average_sale": average_sale,

        "chart_labels": chart_labels,
        "chart_sales": chart_sales,
        "chart_transactions": chart_transactions,

        "recent_sales": recent_sales,

        "current_date": now,
    }

    return render(
        request,
        "pages/reports.html",
        context
    )