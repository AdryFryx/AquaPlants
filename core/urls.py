from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView)
from api.views import (DispositivoViewSet,MedicionViewSet,actualizar_configuracion,gestionar_alertas,registrar_usuario)
from api.views import login_web, dashboard_admin, crear_informe_falla, crear_cliente_web, editar_cliente_web, eliminar_cliente_web, resolver_informe, cambiar_estado_dispositivo

# ENRUTADOR DE LA API
router = DefaultRouter()

router.register(r'dispositivos',DispositivoViewSet,basename='dispositivo')
router.register(r'mediciones',MedicionViewSet,basename='medicion')

urlpatterns = [
    path('admin/', admin.site.urls),
    # AUTENTICACION JWT
    path('api/token/',TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    # REGISTRO DE CLIENTES
    path('api/registro/',registrar_usuario,name='registro'),
    # CONFIGURACION
    path('api/configuracion/',actualizar_configuracion,name='actualizar_configuracion'),
    # ALERTAS
    path('api/alertas/',gestionar_alertas,name='gestionar_alertas'),
    # DISPOSITIVOS Y MEDICIONES
    path('api/', include(router.urls)),
    path('login-admin/', login_web, name='login_web'),
    path('dashboard-admin/', dashboard_admin, name='dashboard_admin'),
    path('crear-informe/', crear_informe_falla, name='crear_informe'),
    path('crear-cliente-web/', crear_cliente_web, name='crear_cliente_web'),
    path('editar-cliente-web/', editar_cliente_web, name='editar_cliente_web'),
    path('eliminar-cliente-web/', eliminar_cliente_web, name='eliminar_cliente_web'),
    path('resolver-informe/', resolver_informe, name='resolver_informe'),
    path('cambiar-estado-dispositivo/', cambiar_estado_dispositivo, name='cambiar_estado_dispositivo'),
]
