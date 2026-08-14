from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

def login_view(request):

    # Already logged in
    if request.user.is_authenticated:

        if request.user.is_superuser:
            return redirect("admin-dashboard")

        elif request.user.is_staff:
            return redirect("staff-dashboard")

        else:
            return redirect("user-dashboard")


    # Login
    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(
                request,
                user
            )


            # ==========================================
            # SUPERUSER
            # ==========================================

            if user.is_superuser:

                return redirect(
                    "admin-dashboard"
                )


            # ==========================================
            # STAFF
            # ==========================================

            elif user.is_staff:

                return redirect(
                    "staff-dashboard"
                )


            # ==========================================
            # REGULAR USER
            # ==========================================

            else:

                return redirect(
                    "user-dashboard"
                )


        return render(
            request,
            "login.html",
            {
                "error": "Invalid username or password."
            }
        )


    return render(
        request,
        "login.html"
    )

#logout
def logout_view(request):

    logout(request)

    return redirect("login")