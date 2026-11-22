from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        usuarios = User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        )

        for user in usuarios:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None