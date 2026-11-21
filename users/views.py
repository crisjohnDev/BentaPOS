from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .utils import create_default_admin
from core.models import UserProfile, AdminPortalLock
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.db import transaction

def login_view(request):
    # Create the default admin if required.
    create_default_admin()

    # ---------------------------------------------------------
    # HANDLE ALREADY AUTHENTICATED USERS
    # ---------------------------------------------------------
    if request.user.is_authenticated:
        user = request.user

        if user.is_superuser:
            return redirect("admin-dashboard")

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(
                user=user,
                role="STAFF",
            )

        if profile.role == "ADMIN":
            return redirect("admin-dashboard")

        return redirect("staff-dashboard")

    # ---------------------------------------------------------
    # HANDLE LOGIN FORM
    # ---------------------------------------------------------
    if request.method != "POST":
        return render(request, "login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    if not username or not password:
        return render(
            request,
            "login.html",
            {"error": "Please enter your username and password."},
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return render(
            request,
            "login.html",
            {"error": "Invalid username or password."},
        )

    if not user.is_active:
        return render(
            request,
            "login.html",
            {
                "error": (
                    "Your account is inactive. "
                    "Please contact the administrator."
                )
            },
        )

    # ---------------------------------------------------------
    # DETERMINE USER ROLE
    # ---------------------------------------------------------
    if user.is_superuser:
        role = "ADMIN"
    else:
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(
                user=user,
                role="STAFF",
            )

        role = profile.role

    allowed_roles = {
        "ADMIN",
        "MANAGER",
        "STAFF",
        "CASHIER",
        "INVENTORY",
    }

    if role not in allowed_roles:
        return render(
            request,
            "login.html",
            {
                "error": (
                    "Your account does not have a valid role. "
                    "Please contact the administrator."
                )
            },
        )

    # ---------------------------------------------------------
    # ADMIN / MANAGER SINGLE-SESSION LOCK
    # ---------------------------------------------------------
    if role in {"ADMIN", "MANAGER"}:
        try:
            with transaction.atomic():
                # Ensure the singleton lock record exists.
                AdminPortalLock.objects.get_or_create(id=1)

                # Lock the database row to serialize login attempts.
                lock = AdminPortalLock.objects.select_for_update().get(
                    id=1
                )

                # Recover a lock whose Django session has expired.
                if lock.locked:
                    session_is_valid = False

                    if lock.session_key:
                        session_is_valid = Session.objects.filter(
                            session_key=lock.session_key,
                            expire_date__gt=timezone.now(),
                        ).exists()

                    if session_is_valid:
                        return render(
                            request,
                            "login.html",
                            {
                                "error": (
                                    "The administrator portal is "
                                    "currently in use. Please try again "
                                    "after the active session ends."
                                )
                            },
                        )

                    # The recorded session no longer exists or expired.
                    lock.locked = False
                    lock.session_key = None
                    lock.user = None
                    lock.ip_address = None
                    lock.last_activity = None
                    lock.save()

                # Log in while holding the database lock.
                login(request, user)

                # Save the session key AFTER Django login.
                lock.locked = True
                lock.session_key = request.session.session_key
                lock.user = user
                lock.ip_address = request.META.get("REMOTE_ADDR")
                lock.last_activity = timezone.now()
                lock.save()

        except Exception:
            # Log the actual exception in production rather than
            # silently swallowing it.
            import logging
            logging.getLogger(__name__).exception(
                "Unable to acquire the admin portal lock."
            )

            return render(
                request,
                "login.html",
                {
                    "error": (
                        "Unable to sign in right now. "
                        "Please try again."
                    )
                },
            )

        if role == "ADMIN":
            return redirect("admin-dashboard")

        return redirect("staff-dashboard")

    # ---------------------------------------------------------
    # NORMAL USERS: NO ADMIN LOCK
    # ---------------------------------------------------------
    login(request, user)

    # Cashiers, staff and inventory users remain independent.
    return redirect("staff-dashboard")


#logout

def logout_view(request):
    if request.user.is_authenticated:
        user = request.user

        is_admin_portal_user = user.is_superuser

        if not user.is_superuser:
            try:
                is_admin_portal_user = (
                    user.profile.role in {"ADMIN", "MANAGER"}
                )
            except UserProfile.DoesNotExist:
                is_admin_portal_user = False

        if is_admin_portal_user:
            session_key = request.session.session_key

            if session_key:
                with transaction.atomic():
                    lock = (
                        AdminPortalLock.objects
                        .select_for_update()
                        .filter(
                            id=1,
                            locked=True,
                            session_key=session_key,
                        )
                        .first()
                    )

                    if lock:
                        lock.locked = False
                        lock.session_key = None
                        lock.user = None
                        lock.ip_address = None
                        lock.last_activity = None
                        lock.save()

    logout(request)
    return redirect("login")
