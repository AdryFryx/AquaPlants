import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count, Avg
from django.utils import timezone

from ..models import Dispositivo, Medicion, InformeFalla, Cultivo, AlertaGenerada
from ..permissions import es_administrador, es_supervisor
from .web_supervisor import render_dashboard_supervisor
from .presets import PLANTACIONES_PRESETS, aplicar_preset_a_cultivo


@login_required(login_url='login_web')
def dashboard_admin(request):
    usuario_actual = request.user

    if not (es_administrador(usuario_actual) or es_supervisor(usuario_actual)):
        return redirect('login_web')

    if es_administrador(usuario_actual):
        clientes = User.objects.filter(groups__name='CLIENTE').select_related('perfil')
        dispositivos = Dispositivo.objects.all().select_related('usuario_encargado')
        supervisores = User.objects.filter(groups__name='SUPERVISOR')
        administradores = User.objects.filter(is_superuser=True)
        reportes_por_asignar = InformeFalla.objects.filter(
            estado='POR_ASIGNAR'
        ).select_related('dispositivo', 'dispositivo__usuario_encargado').order_by('-fecha_creacion')

        contexto = {
            'rol': 'Administrador',
            'dispositivos': dispositivos,
            'clientes': clientes,
            'supervisores': supervisores,
            'administradores': administradores,
            'reportes_por_asignar': reportes_por_asignar,
            'plantas_disponibles': list(PLANTACIONES_PRESETS.keys()),
        }
        return render(request, 'api/dashboard_admin.html', contexto)

    elif es_supervisor(usuario_actual):
        return render_dashboard_supervisor(request)

    return redirect('login_web')


@login_required(login_url='login_web')
def detalle_dispositivo_web(request, dispositivo_id):
    """Página dedicada con las 5 gráficas en tiempo real separadas por plantación."""
    if not (es_administrador(request.user) or es_supervisor(request.user)):
        return redirect('dashboard_admin')

    dispositivo = get_object_or_404(
        Dispositivo.objects.select_related('usuario_encargado', 'usuario_encargado__perfil')
        .prefetch_related('cultivos__reglas'),
        id=dispositivo_id
    )
    es_admin = es_administrador(request.user)
    supervisores = User.objects.filter(groups__name='SUPERVISOR') if es_admin else []

    cultivos_data = []
    for c in dispositivo.cultivos.filter(activo=True):
        reglas = {
            r.variable: {'min': r.rango_minimo, 'max': r.rango_maximo}
            for r in c.reglas.all()
        }
        cultivos_data.append({
            'id': c.id,
            'tipo_planta': c.tipo_planta,
            'semanas_ciclo': c.semanas_ciclo,
            'reglas': reglas,
        })

    return render(request, 'api/detalle_dispositivo.html', {
        'rol': 'Administrador' if es_admin else 'Supervisor',
        'es_admin': es_admin,
        'disp': dispositivo,
        'supervisores': supervisores,
        'plantas_disponibles': list(PLANTACIONES_PRESETS.keys()),
        'cultivos_json': json.dumps(cultivos_data),
    })


@login_required(login_url='login_web')
def datos_dispositivo_realtime(request, dispositivo_id):
    """Endpoint JSON que consulta el JS cada 10 segundos."""
    if not (es_administrador(request.user) or es_supervisor(request.user)):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    dispositivo = get_object_or_404(Dispositivo, id=dispositivo_id)
    mediciones = list(Medicion.objects.filter(dispositivo=dispositivo).order_by('-timestamp')[:15])
    mediciones.reverse()

    return JsonResponse({
        'estado_conexion': dispositivo.estado_conexion,
        'etiquetas': [m.timestamp.strftime('%H:%M:%S') for m in mediciones],
        'temperatura': [m.temperatura if m.temperatura is not None else 0 for m in mediciones],
        'agua': [m.nivel_agua if m.nivel_agua is not None else 0 for m in mediciones],
        'ph': [m.ph if m.ph is not None else 0 for m in mediciones],
        'nutriente_a': [m.nutriente_a if m.nutriente_a is not None else 0 for m in mediciones],
        'nutriente_b': [m.nutriente_b if m.nutriente_b is not None else 0 for m in mediciones],
    })


@login_required(login_url='login_web')
@require_POST
def asignar_reporte_cliente(request):
    """NUEVO: El Admin detalla el reporte del cliente y lo deriva a un Supervisor."""
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    informe_id = request.POST.get('informe_id')
    supervisor_id = request.POST.get('supervisor_id')
    descripcion_admin = request.POST.get('descripcion', '').strip()

    try:
        informe = InformeFalla.objects.get(id=informe_id, estado='POR_ASIGNAR')
        supervisor = User.objects.get(id=supervisor_id, groups__name='SUPERVISOR')

        informe.administrador_creador = request.user
        informe.supervisor_asignado = supervisor
        informe.descripcion = f"[Reporte Cliente: {informe.reporte_cliente}] — Detalle Admin: {descripcion_admin}"
        informe.estado = 'PENDIENTE'
        informe.save()

        messages.success(request, f"Reporte derivado a {supervisor.first_name} correctamente.")
    except (InformeFalla.DoesNotExist, User.DoesNotExist):
        messages.error(request, "Error al asignar el reporte.")

    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def crear_informe_falla(request):
    if not es_administrador(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('dashboard_admin')

    dispositivo_id = request.POST.get('dispositivo_id')
    supervisor_id = request.POST.get('supervisor_id')
    descripcion = request.POST.get('descripcion')

    try:
        dispositivo = Dispositivo.objects.get(id=dispositivo_id)
        supervisor = User.objects.get(id=supervisor_id, groups__name='SUPERVISOR')

        InformeFalla.objects.create(
            dispositivo=dispositivo,
            administrador_creador=request.user,
            supervisor_asignado=supervisor,
            descripcion=descripcion,
            estado='PENDIENTE'
        )
        messages.success(request, f'Informe de falla enviado a {supervisor.first_name} exitosamente.')
    except (Dispositivo.DoesNotExist, User.DoesNotExist):
        messages.error(request, 'Error al crear el informe. Datos inválidos.')

    return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))


@login_required(login_url='login_web')
@require_POST
def crear_cliente_web(request):
    username = request.POST.get('username')
    nombre = request.POST.get('nombre')
    apellido = request.POST.get('apellido')
    email = request.POST.get('email')
    password = request.POST.get('password')
    mac_address = request.POST.get('mac_address')
    nombre_instalacion = request.POST.get('nombre_instalacion')

    if User.objects.filter(username=username).exists():
        messages.error(request, "Ese usuario ya está registrado.")
        return redirect('dashboard_admin')

    if Dispositivo.objects.filter(mac_address=mac_address).exists():
        messages.error(request, "Esa MAC Address ya está en uso.")
        return redirect('dashboard_admin')

    nuevo_user = User.objects.create_user(
        username=username, email=email, password=password,
        first_name=nombre, last_name=apellido
    )
    grupo_cliente, _ = Group.objects.get_or_create(name='CLIENTE')
    nuevo_user.groups.add(grupo_cliente)

    nuevo_disp = Dispositivo.objects.create(
        mac_address=mac_address,
        usuario_encargado=nuevo_user,
        nombre_instalacion=nombre_instalacion
    )
    cultivo_inicial = Cultivo.objects.create(dispositivo=nuevo_disp, tipo_planta='Lechuga', semanas_ciclo=5)
    aplicar_preset_a_cultivo(cultivo_inicial)

    messages.success(request, f"¡Cliente {nombre} y su dispositivo {mac_address} creados con éxito!")
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def crear_empleado_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    username = request.POST.get('username')
    nombre = request.POST.get('nombre')
    apellido = request.POST.get('apellido')
    email = request.POST.get('email')
    password = request.POST.get('password')
    rol = request.POST.get('rol')

    if User.objects.filter(username=username).exists():
        messages.error(request, "Ese usuario ya existe.")
        return redirect('dashboard_admin')

    nuevo_user = User.objects.create_user(
        username=username, email=email, password=password,
        first_name=nombre, last_name=apellido
    )

    if rol == 'ADMIN':
        nuevo_user.is_superuser = True
        nuevo_user.is_staff = True
        nuevo_user.save()
    elif rol == 'SUPERVISOR':
        grupo, _ = Group.objects.get_or_create(name='SUPERVISOR')
        nuevo_user.groups.add(grupo)

    messages.success(request, f"¡Empleado {nombre} registrado como {rol} exitosamente!")
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def editar_usuario_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    user_id = request.POST.get('usuario_id')
    user = User.objects.get(id=user_id)
    user.first_name = request.POST.get('nombre')
    user.last_name = request.POST.get('apellido')
    user.email = request.POST.get('email')
    user.save()
    messages.success(request, f"Datos de @{user.username} actualizados.")
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def eliminar_usuario_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    user_id = request.POST.get('usuario_id')
    user = User.objects.get(id=user_id)
    nombre = user.username
    user.delete()
    messages.success(request, f"El usuario @{nombre} fue eliminado del sistema.")
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def cambiar_estado_dispositivo(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    dispositivo_id = request.POST.get('dispositivo_id')
    try:
        dispositivo = Dispositivo.objects.get(id=dispositivo_id)
        dispositivo.estado_conexion = not dispositivo.estado_conexion
        dispositivo.save()
        estado_texto = "En línea" if dispositivo.estado_conexion else "Desconectado"
        messages.success(request, f'Dispositivo {dispositivo.mac_address} cambiado a: {estado_texto}')
    except Dispositivo.DoesNotExist:
        messages.error(request, 'Error al cambiar el estado: Dispositivo no encontrado.')

    return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))


@login_required(login_url='login_web')
@require_POST
def configurar_torre_web(request):
    dispositivo_id = request.POST.get('dispositivo_id')
    latitud = request.POST.get('latitud')
    longitud = request.POST.get('longitud')
    tipo_planta = request.POST.get('tipo_planta')
    semanas_ciclo = request.POST.get('semanas_ciclo')

    dispositivo = Dispositivo.objects.get(id=dispositivo_id)
    dispositivo.latitud = float(latitud) if latitud else None
    dispositivo.longitud = float(longitud) if longitud else None
    dispositivo.save()

    if hasattr(dispositivo, 'cultivo_activo'):
        cultivo = dispositivo.cultivo_activo
        cultivo.tipo_planta = tipo_planta
        cultivo.semanas_ciclo = int(semanas_ciclo)
        cultivo.save()

    messages.success(request, f"Configuración de {dispositivo.nombre_instalacion} actualizada exitosamente.")
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def eliminar_dispositivo_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    dispositivo_id = request.POST.get('dispositivo_id')
    try:
        dispositivo = Dispositivo.objects.get(id=dispositivo_id)
        mac = dispositivo.mac_address
        dispositivo.delete()
        messages.success(request, f"La torre con MAC {mac} y todo su historial fueron eliminados correctamente.")
    except Dispositivo.DoesNotExist:
        messages.error(request, "Error: El dispositivo no existe.")

    return redirect('dashboard_admin')

@login_required(login_url='login_web')
@require_POST
def agregar_cultivo_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    dispositivo_id = request.POST.get('dispositivo_id')
    tipo_planta = (request.POST.get('tipo_planta') or '').strip()

    especie_base = tipo_planta
    if tipo_planta.startswith('Lechuga'):
        especie_base = 'Lechuga'
    elif tipo_planta.startswith('Acelga'):
        especie_base = 'Acelga'

    if especie_base not in PLANTACIONES_PRESETS:
        messages.error(request, "Tipo de plantación no válido.")
        return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))

    dispositivo = get_object_or_404(Dispositivo, id=dispositivo_id)

    if dispositivo.cultivos.filter(tipo_planta=tipo_planta, activo=True).exists():
        messages.warning(request, f"{dispositivo.nombre_instalacion} ya tiene {tipo_planta} asignada.")
        return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))

    cultivo = Cultivo.objects.create(dispositivo=dispositivo, tipo_planta=tipo_planta)
    aplicar_preset_a_cultivo(cultivo)

    messages.success(request, f"Plantación de {tipo_planta} asignada a {dispositivo.nombre_instalacion} con sus umbrales automáticos.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))


@login_required(login_url='login_web')
@require_POST
def eliminar_cultivo_web(request):
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    cultivo_id = request.POST.get('cultivo_id')
    cultivo = get_object_or_404(Cultivo, id=cultivo_id)
    nombre = cultivo.tipo_planta
    cultivo.delete()

    messages.success(request, f"Plantación de {nombre} eliminada.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_admin'))

@login_required(login_url='login_web')
def informe_gestion_web(request):
    """Genera el Informe de Gestión ejecutivo del sistema."""
    if not es_administrador(request.user):
        return redirect('dashboard_admin')

    # KPIs de infraestructura y usuarios
    total_clientes = User.objects.filter(groups__name='CLIENTE').count()
    total_dispositivos = Dispositivo.objects.count()
    dispositivos_online = Dispositivo.objects.filter(estado_conexion=True).count()
    dispositivos_offline = total_dispositivos - dispositivos_online

    # Distribución de plantaciones activas
    cultivos_por_tipo = (
        Cultivo.objects.filter(activo=True)
        .values('tipo_planta')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    total_cultivos = Cultivo.objects.filter(activo=True).count()

    # Promedios globales de sensores y alertas
    total_mediciones = Medicion.objects.count()
    promedios = Medicion.objects.aggregate(
        temp=Avg('temperatura'),
        agua=Avg('nivel_agua'),
        ph=Avg('ph'),
        nut_a=Avg('nutriente_a'),
        nut_b=Avg('nutriente_b'),
    )
    total_alertas = AlertaGenerada.objects.count()

    # Gestión de incidencias / fallas
    total_fallas = InformeFalla.objects.count()
    fallas_por_asignar = InformeFalla.objects.filter(estado='POR_ASIGNAR').count()
    fallas_pendientes = InformeFalla.objects.filter(estado='PENDIENTE').count()
    fallas_resueltas = InformeFalla.objects.filter(estado='RESUELTO').count()
    tasa_resolucion = round((fallas_resueltas / total_fallas) * 100, 1) if total_fallas > 0 else 100.0

    # Detalle por torre
    dispositivos_detalle = (
        Dispositivo.objects.select_related('usuario_encargado')
        .prefetch_related('cultivos')
        .annotate(num_mediciones=Count('mediciones', distinct=True))
    )

    contexto = {
        'fecha_generacion': timezone.now(),
        'generado_por': request.user,
        'total_clientes': total_clientes,
        'total_dispositivos': total_dispositivos,
        'dispositivos_online': dispositivos_online,
        'dispositivos_offline': dispositivos_offline,
        'total_cultivos': total_cultivos,
        'cultivos_por_tipo': cultivos_por_tipo,
        'total_mediciones': total_mediciones,
        'promedios': promedios,
        'total_alertas': total_alertas,
        'total_fallas': total_fallas,
        'fallas_por_asignar': fallas_por_asignar,
        'fallas_pendientes': fallas_pendientes,
        'fallas_resueltas': fallas_resueltas,
        'tasa_resolucion': tasa_resolucion,
        'dispositivos_detalle': dispositivos_detalle,
    }
    return render(request, 'api/informe_gestion.html', contexto)

@login_required(login_url='login_web')
def informe_dispositivo_web(request, dispositivo_id):
    """Genera un Informe de Gestión individual para una torre y su cliente."""
    if not (es_administrador(request.user) or es_supervisor(request.user)):
        return redirect('dashboard_admin')

    dispositivo = get_object_or_404(
        Dispositivo.objects.select_related('usuario_encargado')
        .prefetch_related('cultivos__reglas'),
        id=dispositivo_id
    )

    mediciones_qs = Medicion.objects.filter(dispositivo=dispositivo)
    total_mediciones = mediciones_qs.count()
    promedios = mediciones_qs.aggregate(
        temp=Avg('temperatura'),
        agua=Avg('nivel_agua'),
        ph=Avg('ph'),
        nut_a=Avg('nutriente_a'),
        nut_b=Avg('nutriente_b'),
    )
    ultima_medicion = mediciones_qs.order_by('-timestamp').first()

    alertas = AlertaGenerada.objects.filter(
        medicion__dispositivo=dispositivo
    ).select_related('medicion').order_by('-id')[:10]
    total_alertas = AlertaGenerada.objects.filter(medicion__dispositivo=dispositivo).count()

    fallas = InformeFalla.objects.filter(dispositivo=dispositivo).order_by('-fecha_creacion')
    total_fallas = fallas.count()
    fallas_resueltas = fallas.filter(estado='RESUELTO').count()

    contexto = {
        'fecha_generacion': timezone.now(),
        'generado_por': request.user,
        'disp': dispositivo,
        'cliente': dispositivo.usuario_encargado,
        'cultivos': dispositivo.cultivos.filter(activo=True),
        'total_mediciones': total_mediciones,
        'promedios': promedios,
        'ultima_medicion': ultima_medicion,
        'alertas': alertas,
        'total_alertas': total_alertas,
        'fallas': fallas,
        'total_fallas': total_fallas,
        'fallas_resueltas': fallas_resueltas,
    }
    return render(request, 'api/informe_dispositivo.html', contexto)