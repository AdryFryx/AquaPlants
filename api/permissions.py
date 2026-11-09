
from rest_framework.permissions import BasePermission, SAFE_METHODS


# =====================================================
# FUNCIONES PARA IDENTIFICAR LOS ROLES
# =====================================================

def tiene_rol(usuario, rol):
    if not usuario or not usuario.is_authenticated:
        return False

    if usuario.is_superuser:
        return True

    return usuario.groups.filter(name=rol).exists()


def es_administrador(usuario):
    return tiene_rol(usuario, 'ADMINISTRADOR')


def es_supervisor(usuario):
    return tiene_rol(usuario, 'SUPERVISOR')


def es_cliente(usuario):
    return tiene_rol(usuario, 'CLIENTE')


# =====================================================
# PERMISO EXCLUSIVO PARA ADMINISTRADORES
# =====================================================

class EsAdministrador(BasePermission):

    message = 'No tienes permisos de administrador.'

    def has_permission(self, request, view):
        return es_administrador(request.user)


# =====================================================
# ADMINISTRADOR Y SUPERVISOR
# =====================================================

class EsAdministradorOSupervisor(BasePermission):

    message = 'No tienes permisos para acceder a este recurso.'

    def has_permission(self, request, view):
        usuario = request.user

        return (
            es_administrador(usuario)
            or es_supervisor(usuario)
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        if es_administrador(usuario):
            return True

        if es_supervisor(usuario):
            return request.method in SAFE_METHODS

        return False


# =====================================================
# PERMISO PARA CLIENTES
# =====================================================

class EsCliente(BasePermission):

    message = 'Este recurso está disponible para clientes.'

    def has_permission(self, request, view):
        return es_cliente(request.user)
