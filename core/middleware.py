from django.shortcuts import redirect

from .models import AdminPortalLock


class SingleAdminPortalMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # ======================================================
        # LOGIN PAGE MUST ALWAYS BE ACCESSIBLE
        # ======================================================

        if request.path.endswith("/login/"):
            return self.get_response(request)


        # ======================================================
        # LOGOUT MUST ALWAYS BE ACCESSIBLE
        # ======================================================

        if request.path.endswith("/logout/"):
            return self.get_response(request)


        # ======================================================
        # LOCKED PAGE MUST ALWAYS BE ACCESSIBLE
        # ======================================================

        if request.path.endswith("/admin-portal-locked/"):
            return self.get_response(request)


        # ======================================================
        # NOT LOGGED IN
        # ======================================================

        if not request.user.is_authenticated:
            return self.get_response(request)


        # ======================================================
        # DETERMINE CURRENT USER ROLE
        # ======================================================

        user = request.user

        is_admin = False


        # ------------------------------------------------------
        # SUPERUSER
        # ------------------------------------------------------

        if user.is_superuser:

            is_admin = True


        # ------------------------------------------------------
        # NORMAL USER
        # ------------------------------------------------------

        else:

            profile = getattr(
                user,
                "profile",
                None
            )

            if profile is not None:

                if profile.role == "ADMIN":

                    is_admin = True


        # ======================================================
        # NOT ADMIN
        #
        # MANAGER
        # STAFF
        # CASHIER
        # INVENTORY
        #
        # ARE NEVER AFFECTED BY ADMIN LOCK
        # ======================================================

        if not is_admin:

            return self.get_response(request)


        # ======================================================
        # CURRENT USER IS ADMIN
        # ======================================================

        lock = AdminPortalLock.objects.filter(
            id=1,
            locked=True
        ).first()


        # ======================================================
        # NO LOCK
        # ======================================================

        if lock is None:

            return self.get_response(request)


        # ======================================================
        # GET CURRENT SESSION
        # ======================================================

        current_session = request.session.session_key


        # ======================================================
        # ADMIN OWNS THE LOCK
        # ======================================================

        if (
            lock.session_key
            and lock.session_key == current_session
        ):

            return self.get_response(request)


        # ======================================================
        # DIFFERENT ADMIN SESSION
        # ======================================================

        return redirect(
            "admin_portal_locked"
        )