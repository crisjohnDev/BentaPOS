from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

def login_view(request):

    # ==========================================
    # ALREADY LOGGED IN
    # ==========================================

    if request.user.is_authenticated:

        if request.user.is_superuser:
            return redirect("admin-dashboard")

        elif request.user.is_staff:
            return redirect("staff-dashboard")

        else:
            return redirect("user-dashboard")

    # ==========================================
    # LOGIN
    # ==========================================
    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Check empty fields
        if not username or not password:

            return render(
                request,
                "login.html",
                {
                    "error": "Please enter your username and password."
                }
            )

        # Authenticate user
        user = authenticate(
            request,
            username=username,
            password=password
        )

        # ==========================================
        # INVALID LOGIN
        # ==========================================
        if user is None:

            return render(
                request,
                "login.html",
                {
                    "error": "Invalid username or password."
                }
            )

        # ==========================================
        # CHECK ACCOUNT ACTIVE
        # ==========================================

        if not user.is_active:

            return render(
                request,
                "login.html",
                {
                    "error": "Your account is inactive. Please contact the administrator."
                }
            )

        # ==========================================
        # CHECK SYSTEM PERMISSION
        # ==========================================
        if not user.is_superuser and not user.is_staff:

            return render(
                request,
                "login.html",
                {
                    "error": "Your account does not have permission to access this system."
                }
            )

        # ==========================================
        # LOGIN USER
        # ==========================================

        login(request, user)

        # ==========================================
        # SUPERUSER
        # ==========================================
        if user.is_superuser:

            return redirect("admin-dashboard")

        # ==========================================
        # STAFF
        # ==========================================

        if user.is_staff:

            return redirect("staff-dashboard")

        # ==========================================
        # FALLBACK
        # ==========================================
        return render(
            request,
            "login.html",
            {
                "error": "Your account does not have permission to access this system."
            }
        )

    # ==========================================
    # GET REQUEST
    # ==========================================
    return render(request, "login.html")
#logout
def logout_view(request):

    logout(request)
    return redirect("login")