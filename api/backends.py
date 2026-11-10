from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Buscamos al usuario ya sea por su username O por su email (sin distinguir mayúsculas/minúsculas)
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            # Si no existe ni el username ni el email, rechazamos el login
            return None
        
        # Si el usuario existe, verificamos que su contraseña sea correcta
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None