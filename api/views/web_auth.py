from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages

from ..permissions import es_administrador, es_supervisor


def login_web(request):
    if request.user.is_authenticated:
        return redirect('dashboard_admin')

    if request.method == 'POST':
        usuario = request.POST.get('username')
        contrasena = request.POST.get('password')

        user = authenticate(request, username=usuario, password=contrasena)

        if user is not None:
            if es_administrador(user) or es_supervisor(user):
                auth_login(request, user)
                return redirect('dashboard_admin')
            else:
                messages.error(request, 'No tienes permisos de Administrador o Supervisor para entrar aquí.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'api/login_web.html')


def logout_web(request):
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login_web')