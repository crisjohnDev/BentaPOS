from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .utils import create_default_admin
from core.models import UserProfile

def login_view(request):

    # ==========================================================
    # CREATE DEFAULT ADMIN
    # ==========================================================

    create_default_admin()


    # ==========================================================
    # ALREADY LOGGED IN
    # ==========================================================

    if request.user.is_authenticated:

        user = request.user


        # ------------------------------------------------------
        # SUPERUSER
        # ------------------------------------------------------

        if user.is_superuser:

            return redirect("admin-dashboard")


        # ------------------------------------------------------
        # GET USER PROFILE
        # ------------------------------------------------------

        try:

            profile = user.profile

        except UserProfile.DoesNotExist:

            # --------------------------------------------------
            # CREATE PROFILE IF MISSING
            # --------------------------------------------------

            profile = UserProfile.objects.create(
                user=user,
                role="STAFF"
            )


        # ------------------------------------------------------
        # GET ROLE
        # ------------------------------------------------------

        role = profile.role


        # ------------------------------------------------------
        # ROLE-BASED REDIRECT
        # ------------------------------------------------------

        if role == "ADMIN":

            return redirect("admin-dashboard")


        elif role == "MANAGER":

            # If you already have a manager dashboard,
            # change this to:
            #
            # return redirect("manager-dashboard")

            return redirect("staff-dashboard")


        elif role == "CASHIER":

            # If you already have a cashier dashboard,
            # change this to:
            #
            # return redirect("cashier-dashboard")

            return redirect("staff-dashboard")


        elif role == "INVENTORY":

            # If you already have an inventory dashboard,
            # change this to:
            #
            # return redirect("inventory-dashboard")

            return redirect("staff-dashboard")


        elif role == "STAFF":

            return redirect("staff-dashboard")


        # ------------------------------------------------------
        # FALLBACK
        # ------------------------------------------------------

        return redirect("staff-dashboard")


    # ==========================================================
    # LOGIN
    # ==========================================================

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )


        # ======================================================
        # CHECK EMPTY FIELDS
        # ======================================================

        if not username or not password:

            return render(
                request,
                "login.html",
                {
                    "error":
                        "Please enter your username and password."
                }
            )


        # ======================================================
        # AUTHENTICATE USER
        # ======================================================

        user = authenticate(
            request,
            username=username,
            password=password
        )


        # ======================================================
        # INVALID LOGIN
        # ======================================================

        if user is None:

            return render(
                request,
                "login.html",
                {
                    "error":
                        "Invalid username or password."
                }
            )


        # ======================================================
        # CHECK ACCOUNT ACTIVE
        # ======================================================

        if not user.is_active:

            return render(
                request,
                "login.html",
                {
                    "error":
                        "Your account is inactive. "
                        "Please contact the administrator."
                }
            )


        # ======================================================
        # SUPERUSER
        # ======================================================

        if user.is_superuser:

            login(request, user)

            return redirect(
                "admin-dashboard"
            )


        # ======================================================
        # CHECK USER PROFILE
        # ======================================================

        try:

            profile = user.profile

        except UserProfile.DoesNotExist:

            # --------------------------------------------------
            # CREATE PROFILE FOR OLD USERS
            # --------------------------------------------------

            profile = UserProfile.objects.create(
                user=user,
                role="STAFF"
            )


        # ======================================================
        # GET USER ROLE
        # ======================================================

        role = profile.role


        # ======================================================
        # CHECK SYSTEM PERMISSION
        # ======================================================

        # User must either be a Django staff account
        # OR have an allowed BentaPOS role.

        allowed_roles = [
            "ADMIN",
            "MANAGER",
            "STAFF",
            "CASHIER",
            "INVENTORY",
        ]


        if role not in allowed_roles:

            return render(
                request,
                "login.html",
                {
                    "error":
                        "Your account does not have a valid "
                        "role. Please contact the administrator."
                }
            )


        # ======================================================
        # LOGIN USER
        # ======================================================

        login(
            request,
            user
        )


        # ======================================================
        # ROLE-BASED REDIRECTION
        # ======================================================

        # ------------------------------------------------------
        # ADMINISTRATOR
        # ------------------------------------------------------

        if role == "ADMIN":

            return redirect(
                "admin-dashboard"
            )


        # ------------------------------------------------------
        # MANAGER
        # ------------------------------------------------------

        elif role == "MANAGER":

            # Change to "manager-dashboard" later if you
            # create a dedicated manager dashboard.

            return redirect(
                "staff-dashboard"
            )


        # ------------------------------------------------------
        # CASHIER
        # ------------------------------------------------------

        elif role == "CASHIER":

            # Change to "cashier-dashboard" later if you
            # create a dedicated cashier dashboard.

            return redirect(
                "staff-dashboard"
            )


        # ------------------------------------------------------
        # INVENTORY
        # ------------------------------------------------------

        elif role == "INVENTORY":

            # Change to "inventory-dashboard" later if you
            # create a dedicated inventory dashboard.

            return redirect(
                "staff-dashboard"
            )


        # ------------------------------------------------------
        # STAFF
        # ------------------------------------------------------

        elif role == "STAFF":

            return redirect(
                "staff-dashboard"
            )


        # ======================================================
        # FALLBACK
        # ======================================================

        return render(
            request,
            "login.html",
            {
                "error":
                    "Your account does not have permission "
                    "to access this system."
            }
        )


    # ==========================================================
    # GET REQUEST
    # ==========================================================

    return render(
        request,
        "login.html"
    )


#logout
def logout_view(request):

    logout(request)
    return redirect("login")