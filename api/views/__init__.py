from .api_iot import recibir_datos_esp32
from .api_mobile import (
    DispositivoViewSet,
    MedicionViewSet,
    registrar_usuario,
    actualizar_configuracion,
    gestionar_alertas,
    reportar_falla_cliente,
    mis_cultivos,
)
from .web_auth import login_web, logout_web
from .web_supervisor import resolver_informe
from .web_admin import (
    dashboard_admin,
    detalle_dispositivo_web,
    datos_dispositivo_realtime,
    asignar_reporte_cliente,
    crear_informe_falla,
    crear_cliente_web,
    crear_empleado_web,
    editar_usuario_web,
    eliminar_usuario_web,
    cambiar_estado_dispositivo,
    configurar_torre_web,
    eliminar_dispositivo_web,
    agregar_cultivo_web,
    eliminar_cultivo_web,
)