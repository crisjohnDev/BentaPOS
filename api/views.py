from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):

    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    # =========================================
    # VALIDATION
    # =========================================

    if not username:
        return Response(
            {
                "success": False,
                "message": "Please enter your username."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not password:
        return Response(
            {
                "success": False,
                "message": "Please enter your password."
            },
            status=status.HTTP_400_BAD_REQUEST
        )


    # =========================================
    # AUTHENTICATE
    # =========================================

    user = authenticate(
        username=username,
        password=password
    )


    if user is None:

        return Response(
            {
                "success": False,
                "message": "Invalid username or password."
            },
            status=status.HTTP_401_UNAUTHORIZED
        )


    # =========================================
    # CHECK ACTIVE USER
    # =========================================

    if not user.is_active:

        return Response(
            {
                "success": False,
                "message": "This account is inactive."
            },
            status=status.HTTP_403_FORBIDDEN
        )


    # =========================================
    # CREATE JWT
    # =========================================

    refresh = RefreshToken.for_user(user)

    access_token = str(refresh.access_token)
    refresh_token = str(refresh)


    # =========================================
    # ROLE
    # =========================================

    role = getattr(user, "role", None)


    # =========================================
    # RESPONSE
    # =========================================

    return Response(
        {
            "success": True,
            "message": "Login successful.",

            "access": access_token,

            "refresh": refresh_token,

            "user": {
                "id": user.id,
                "username": user.username,
                "role": role,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        },
        status=status.HTTP_200_OK
    )