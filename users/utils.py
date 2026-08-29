from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()


def create_default_admin():
    user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        }
    )

    if created:
        user.set_password("admin")
        user.save()

    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "role": "ADMIN",
        }
    )