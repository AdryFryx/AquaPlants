from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView)
from api.views import (DispositivoViewSet,MedicionViewSet,actualizar_configuracion,gestionar_alertas,registrar_usuario)
from api.views import login_web

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
]
