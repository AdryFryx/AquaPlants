from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api import views

# =====================================================
# ENRUTADOR DE LA API (DRF)
# =====================================================
router = DefaultRouter()
router.register(r'dispositivos', views.DispositivoViewSet, basename='dispositivo')
router.register(r'mediciones', views.MedicionViewSet, basename='medicion')

urlpatterns = [
    path('admin/', admin.site.urls),

    # =================================================
    # API MÓVIL (FLUTTER)
    # =================================================
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/registro/', views.registrar_usuario, name='registro'),
    path('api/configuracion/', views.actualizar_configuracion, name='actualizar_configuracion'),
    path('api/alertas/', views.gestionar_alertas, name='gestionar_alertas'),
    path('api/reportar-falla/', views.reportar_falla_cliente, name='reportar_falla_cliente'),
    path('api/', include(router.urls)),

    # =================================================
    # API IOT (ESP32 / SIMULADOR)
    # =================================================
    path('datos-esp32/', views.recibir_datos_esp32, name='recibir_datos_esp32'),

    # =================================================
    # PANEL WEB - AUTENTICACIÓN Y DASHBOARD
    # =================================================
    path('login-admin/', views.login_web, name='login_web'),
    path('logout-admin/', views.logout_web, name='logout_web'),
    path('dashboard-admin/', views.dashboard_admin, name='dashboard_admin'),

    # =================================================
    # PANEL WEB - DISPOSITIVOS Y TIEMPO REAL
    # =================================================
    path('dispositivo/<int:dispositivo_id>/', views.detalle_dispositivo_web, name='detalle_dispositivo_web'),
    path('dispositivo/<int:dispositivo_id>/realtime/', views.datos_dispositivo_realtime, name='datos_dispositivo_realtime'),
    path('cambiar-estado-dispositivo/', views.cambiar_estado_dispositivo, name='cambiar_estado_dispositivo'),
    path('config-torre/', views.configurar_torre_web, name='configurar_torre_web'),
    path('eliminar-dispositivo/', views.eliminar_dispositivo_web, name='eliminar_dispositivo_web'),
    path('api/mis-cultivos/', views.mis_cultivos, name='mis_cultivos'),
    path('agregar-cultivo/', views.agregar_cultivo_web, name='agregar_cultivo_web'),
    path('eliminar-cultivo/', views.eliminar_cultivo_web, name='eliminar_cultivo_web'),
    
    # =================================================
    # PANEL WEB - USUARIOS
    # =================================================
    path('crear-cliente-web/', views.crear_cliente_web, name='crear_cliente_web'),
    path('crear-empleado/', views.crear_empleado_web, name='crear_empleado_web'),
    path('editar-usuario/', views.editar_usuario_web, name='editar_usuario_web'),
    path('eliminar-usuario/', views.eliminar_usuario_web, name='eliminar_usuario_web'),

    # =================================================
    # PANEL WEB - INFORMES DE FALLA (TRIAGE Y RESOLUCIÓN)
    # =================================================
    path('crear-informe/', views.crear_informe_falla, name='crear_informe'),
    path('asignar-reporte/', views.asignar_reporte_cliente, name='asignar_reporte_cliente'),
    path('resolver-informe/', views.resolver_informe, name='resolver_informe'),
]
