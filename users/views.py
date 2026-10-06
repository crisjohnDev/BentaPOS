from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .utils import create_default_admin
from core.models import UserProfile, AdminPortalLock
from django.utils import timezone

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

            return redirect("staff-dashboard")


        elif role == "CASHIER":

            return redirect("staff-dashboard")


        elif role == "INVENTORY":

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

            # --------------------------------------------------
            # CHECK ADMIN PORTAL LOCK
            # --------------------------------------------------

            lock, created = AdminPortalLock.objects.get_or_create(
                id=1
            )


            # --------------------------------------------------
            # ADMIN PORTAL ALREADY IN USE
            # --------------------------------------------------

            if lock.locked:

                return render(
                    request,
                    "login.html",
                    {
                        "error":
                            "The administrator portal is currently "
                            "being used on another computer."
                    }
                )


            # --------------------------------------------------
            # LOGIN SUPERUSER
            # --------------------------------------------------

            login(
                request,
                user
            )


            # --------------------------------------------------
            # CREATE ADMIN LOCK
            # --------------------------------------------------

            lock.locked = True

            lock.session_key = request.session.session_key

            lock.ip_address = request.META.get(
                "REMOTE_ADDR"
            )

            lock.last_activity = timezone.now()

            lock.save()


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
        # ADMIN ROLE
        # ======================================================

        if role == "ADMIN":

            # --------------------------------------------------
            # CHECK ADMIN PORTAL LOCK
            # --------------------------------------------------

            lock, created = AdminPortalLock.objects.get_or_create(
                id=1
            )


            # --------------------------------------------------
            # ADMIN PORTAL ALREADY IN USE
            # --------------------------------------------------

            if lock.locked:

                return render(
                    request,
                    "login.html",
                    {
                        "error":
                            "The administrator portal is currently "
                            "being used on another computer."
                    }
                )


            # --------------------------------------------------
            # LOGIN ADMIN
            # --------------------------------------------------

            login(
                request,
                user
            )


            # --------------------------------------------------
            # CREATE ADMIN PORTAL LOCK
            # --------------------------------------------------

            lock.locked = True

            lock.session_key = request.session.session_key

            lock.ip_address = request.META.get(
                "REMOTE_ADDR"
            )

            lock.last_activity = timezone.now()

            lock.save()


            return redirect(
                "admin-dashboard"
            )


        # ======================================================
        # NON-ADMIN USERS
        # ======================================================

        # ------------------------------------------------------
        # LOGIN USER
        #
        # IMPORTANT:
        # No AdminPortalLock is checked here.
        #
        # Therefore:
        #
        # MANAGER  -> normal login
        # STAFF    -> normal login
        # CASHIER  -> normal login
        # INVENTORY -> normal login
        # ------------------------------------------------------

        login(
            request,
            user
        )


        # ======================================================
        # ROLE-BASED REDIRECTION
        # ======================================================

        # ------------------------------------------------------
        # MANAGER
        # ------------------------------------------------------

        if role == "MANAGER":

            return redirect(
                "staff-dashboard"
            )


        # ------------------------------------------------------
        # CASHIER
        # ------------------------------------------------------

        elif role == "CASHIER":

            return redirect(
                "staff-dashboard"
            )


        # ------------------------------------------------------
        # INVENTORY
        # ------------------------------------------------------

        elif role == "INVENTORY":

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

    if request.user.is_authenticated:

        profile = getattr(
            request.user,
            "profile",
            None
        )

        is_admin = (
            request.user.is_superuser
            or (
                profile is not None
                and profile.role == "ADMIN"
            )
        )

        if is_admin:

            lock = AdminPortalLock.objects.filter(
                id=1,
                session_key=request.session.session_key,
                locked=True
            ).first()

            if lock:

                lock.locked = False
                lock.session_key = None
                lock.ip_address = None
                lock.last_activity = None

                lock.save()

    logout(request)

    return redirect("login")