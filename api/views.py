import math
import json
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# Las importaciones de modelos y serializers se unificaron para evitar duplicados
from .models import (
    Dispositivo, 
    Medicion, 
    ReglaUmbral, 
    AlertaGenerada, 
    PerfilUsuario, 
    InformeFalla,
    Cultivo
)
from .serializers import DispositivoSerializer, MedicionSerializer, RegistroSerializer
from .permissions import es_administrador, es_supervisor

# =====================================================
# GESTION DE DISPOSITIVOS
# =====================================================

class DispositivoViewSet(viewsets.ModelViewSet):
    serializer_class = DispositivoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_staff:
            return Dispositivo.objects.all()
        return Dispositivo.objects.filter(usuario_encargado=usuario)

# =====================================================
# GESTION DE MEDICIONES Y GENERACION DE ALERTAS
# =====================================================

class MedicionViewSet(viewsets.ModelViewSet):
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if usuario.is_superuser or usuario.is_staff:
            queryset = Medicion.objects.all()
        else:
            queryset = Medicion.objects.filter(dispositivo__usuario_encargado=usuario)

        dias = self.request.query_params.get('dias')

        if dias:
            try:
                cantidad_dias = int(dias)
                if cantidad_dias < 0:
                    return queryset.none()
                fecha_inicio = timezone.now() - timedelta(days=cantidad_dias)
                queryset = queryset.filter(timestamp__gte=fecha_inicio)
            except (ValueError, TypeError):
                pass

        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        medicion = serializer.save()

        try:
            cultivo = medicion.dispositivo.cultivo_activo
            variables = {
                'TEMP': ('temperatura', 'Temperatura', '°C'),
                'PH': ('ph', 'pH', ''),
                'AGUA': ('nivel_agua', 'Nivel de agua', ''),
            }

            for variable, datos in variables.items():
                campo, nombre, unidad = datos
                valor = getattr(medicion, campo)

                if valor is None:
                    continue

                regla = cultivo.reglas.filter(variable=variable).first()

                if regla and (valor < regla.rango_minimo or valor > regla.rango_maximo):
                    AlertaGenerada.objects.create(
                        medicion=medicion,
                        mensaje=f'ALERTA: {nombre} fuera del rango permitido. Valor: {valor}{unidad}. Rango: {regla.rango_minimo}-{regla.rango_maximo}{unidad}.'
                    )

        except Exception as e:
            print(f'Error en el motor de alertas: {e}')

# =====================================================
# REGISTRO PUBLICO DE CLIENTES (API)
# =====================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_usuario(request):
    serializer = RegistroSerializer(data=request.data)

    if serializer.is_valid():
        usuario = serializer.save()
        return Response({
            'mensaje': 'Cuenta creada exitosamente.',
            'usuario': {
                'id': usuario.id,
                'username': usuario.username,
                'nombre': usuario.first_name,
                'apellido': usuario.last_name,
                'email': usuario.email,
                'rol': 'CLIENTE'
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =====================================================
# CONFIGURACION DEL CULTIVO (API)
# =====================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def actualizar_configuracion(request):
    try:
        dispositivo = request.user.dispositivos.first()
        if dispositivo is None:
            return Response({'error': 'No tienes un dispositivo asociado.'}, status=status.HTTP_400_BAD_REQUEST)

        cultivo = getattr(dispositivo, 'cultivo_activo', None)
        if cultivo is None:
            return Response({'error': 'El dispositivo no tiene un cultivo activo.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            reglas = {
                regla.variable: {'minimo': regla.rango_minimo, 'maximo': regla.rango_maximo}
                for regla in cultivo.reglas.all()
            }
            return Response({
                'usuario_nombre': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'torre_nombre': dispositivo.nombre_instalacion,
                'tipo_planta': cultivo.tipo_planta,
                'reglas': reglas
            })

        tipo_planta = request.data.get('tipo_planta')
        if tipo_planta is not None:
            tipo_planta = str(tipo_planta).strip()
            if not tipo_planta or len(tipo_planta) > 100:
                return Response({'error': 'El nombre de la planta no es válido.'}, status=status.HTTP_400_BAD_REQUEST)
            cultivo.tipo_planta = tipo_planta

        variables = {
            'TEMP': ('temp_min', 'temp_max'),
            'PH': ('ph_min', 'ph_max'),
            'AGUA': ('agua_min', 'agua_max'),
        }

        reglas = {}
        for variable, campos in variables.items():
            campo_min, campo_max = campos

            if campo_min not in request.data and campo_max not in request.data:
                continue

            regla_actual = cultivo.reglas.filter(variable=variable).first()
            minimo = request.data.get(campo_min, regla_actual.rango_minimo if regla_actual else None)
            maximo = request.data.get(campo_max, regla_actual.rango_maximo if regla_actual else None)

            if minimo is None or maximo is None:
                return Response({'error': f'Faltan valores para {variable}.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                minimo = float(minimo)
                maximo = float(maximo)
            except (ValueError, TypeError):
                return Response({'error': f'Los valores de {variable} deben ser numéricos.'}, status=status.HTTP_400_BAD_REQUEST)

            if not math.isfinite(minimo) or not math.isfinite(maximo):
                return Response({'error': f'Los valores de {variable} no son válidos.'}, status=status.HTTP_400_BAD_REQUEST)

            if minimo >= maximo:
                return Response({'error': f'El mínimo de {variable} debe ser menor que el máximo.'}, status=status.HTTP_400_BAD_REQUEST)

            reglas[variable] = {
                'rango_minimo': minimo,
                'rango_maximo': maximo
            }

        with transaction.atomic():
            cultivo.save()
            for variable, valores in reglas.items():
                ReglaUmbral.objects.update_or_create(
                    cultivo=cultivo,
                    variable=variable,
                    defaults=valores
                )

        return Response({
            'mensaje': 'Configuración guardada exitosamente.',
            'tipo_planta': cultivo.tipo_planta,
            'reglas_actualizadas': list(reglas.keys())
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f'Error en configuración: {e}')
        return Response({'error': 'No se pudo procesar la configuración.'}, status=status.HTTP_400_BAD_REQUEST)

# =====================================================
# GESTION DE ALERTAS (API)
# =====================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gestionar_alertas(request):
    usuario = request.user

    if usuario.is_superuser or usuario.is_staff:
        alertas_queryset = AlertaGenerada.objects.all()
    else:
        alertas_queryset = AlertaGenerada.objects.filter(medicion__dispositivo__usuario_encargado=usuario)

    if request.method == 'GET':
        alertas = alertas_queryset.select_related('medicion', 'medicion__dispositivo').order_by('-id')[:15]
        data = [{'id': alerta.id, 'mensaje': alerta.mensaje} for alerta in alertas]
        return Response(data)

    alerta_id = request.data.get('id')
    if alerta_id is None:
        return Response({'error': 'Debes proporcionar el ID de la alerta.'}, status=status.HTTP_400_BAD_REQUEST)

    eliminadas, _ = alertas_queryset.filter(id=alerta_id).delete()
    if eliminadas == 0:
        return Response({'error': 'No se encontró la alerta.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'mensaje': 'Alerta resuelta exitosamente.'})

# =====================================================
# VISTAS WEB (DASHBOARDS)
# =====================================================

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

@login_required(login_url='login_web')
def dashboard_admin(request):
    usuario_actual = request.user
    
    if not (es_administrador(usuario_actual) or es_supervisor(usuario_actual)):
        return redirect('login_web')
    
    contexto = {}

    if es_administrador(usuario_actual):
        clientes = User.objects.filter(groups__name='CLIENTE').select_related('perfil')
        dispositivos = Dispositivo.objects.all().select_related('usuario_encargado')
        supervisores = User.objects.filter(groups__name='SUPERVISOR')
        administradores = User.objects.filter(is_superuser=True)
        
        contexto = {
            'rol': 'Administrador',
            'dispositivos': dispositivos,
            'clientes': clientes,
            'supervisores': supervisores,
            'administradores': administradores,

        }
        return render(request, 'api/dashboard_admin.html', contexto)
        
    elif es_supervisor(usuario_actual):
        informes = InformeFalla.objects.filter(supervisor_asignado=usuario_actual, estado='PENDIENTE').select_related('dispositivo', 'dispositivo__usuario_encargado')
        informes_resueltos = InformeFalla.objects.filter(supervisor_asignado=usuario_actual, estado='RESUELTO').order_by('-fecha_resolucion')[:15]
        # Preparamos un diccionario con los datos históricos para los gráficos
        datos_graficos = {}
        for informe in informes:
            mediciones = list(Medicion.objects.filter(dispositivo=informe.dispositivo).order_by('-timestamp')[:15])
            mediciones.reverse()
            
            datos_graficos[informe.id] = {
                'etiquetas': [m.timestamp.strftime('%H:%M') for m in mediciones],
                'temperatura': [m.temperatura if m.temperatura else 0 for m in mediciones],
                'ph': [m.ph if m.ph else 0 for m in mediciones],
                'agua': [m.nivel_agua if m.nivel_agua else 0 for m in mediciones],
                # NUEVOS DATOS: Nutrientes Hidropónicos
                'nutriente_a': [m.nutriente_a if m.nutriente_a else 0 for m in mediciones],
                'nutriente_b': [m.nutriente_b if m.nutriente_b else 0 for m in mediciones]
            }

        contexto = {
            'rol': 'Supervisor',
            'informes_pendientes': informes,
            'informes_resueltos': informes_resueltos,
            'datos_graficos_json': json.dumps(datos_graficos) 
        }
        return render(request, 'api/dashboard_supervisor.html', contexto)
    else:
        return redirect('login_web')

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

    return redirect('dashboard_admin')

@login_required(login_url='login_web')
@require_POST
def crear_cliente_web(request):
    if request.method == 'POST':
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

        # 1. Creamos al Usuario Cliente
        nuevo_user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password, 
            first_name=nombre, 
            last_name=apellido
        )
        
        # 2. IMPORTANTE: Le asignamos el grupo CLIENTE para que aparezca en la tabla
        grupo_cliente, _ = Group.objects.get_or_create(name='CLIENTE')
        nuevo_user.groups.add(grupo_cliente)
        
        # 3. Le creamos y asignamos su Dispositivo ESP32
        nuevo_disp = Dispositivo.objects.create(
            mac_address=mac_address, 
            usuario_encargado=nuevo_user, 
            nombre_instalacion=nombre_instalacion
        )
        
        # 4. Le creamos su Cultivo inicial
        Cultivo.objects.create(
            dispositivo=nuevo_disp, 
            tipo_planta='Lechuga',
            semanas_ciclo=4
        )
        
        messages.success(request, f"¡Cliente {nombre} y su dispositivo {mac_address} creados con éxito!")
        return redirect('dashboard_admin')
        
    return redirect('dashboard_admin')


# =====================================================
# NUEVO CRUD GENÉRICO PARA TODOS LOS USUARIOS
# =====================================================

@login_required(login_url='login_web')
@require_POST
def crear_empleado_web(request):
    if not es_administrador(request.user): 
        return redirect('dashboard_admin')

    if request.method == 'POST':
        username = request.POST.get('username')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        password = request.POST.get('password')
        rol = request.POST.get('rol') # 'SUPERVISOR' o 'ADMIN'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ese usuario ya existe.")
            return redirect('dashboard_admin')
            
        nuevo_user = User.objects.create_user(username=username, email=email, password=password, first_name=nombre, last_name=apellido)
        
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

    if request.method == 'POST':
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

    if request.method == 'POST':
        user_id = request.POST.get('usuario_id')
        user = User.objects.get(id=user_id)
        nombre = user.username
        user.delete() # Esto borra al usuario y sus dispositivos asociados automáticamente
        messages.success(request, f"El usuario @{nombre} fue eliminado del sistema.")
    return redirect('dashboard_admin')

@login_required(login_url='login_web')
@require_POST
def resolver_informe(request):
    if request.method == 'POST':
        informe_id = request.POST.get('informe_id')
        comentario = request.POST.get('comentario', 'Resuelto sin comentarios adicionales.')
        
        informe = InformeFalla.objects.get(id=informe_id)
        informe.estado = 'RESUELTO'
        informe.comentario_resolucion = comentario
        informe.fecha_resolucion = timezone.now() # Guarda la fecha y hora actual
        informe.save()
        
        messages.success(request, f"¡Ticket cerrado exitosamente con tu feedback guardado!")
        
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
        
    return redirect('dashboard_admin')

def logout_web(request):
    auth_logout(request) # Esto destruye la sesión y la cookie
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login_web')

def configurar_torre_web(request):
    if request.method == 'POST':
        dispositivo_id = request.POST.get('dispositivo_id')
        latitud = request.POST.get('latitud')
        longitud = request.POST.get('longitud')
        tipo_planta = request.POST.get('tipo_planta')
        semanas_ciclo = request.POST.get('semanas_ciclo')

        # Buscar el dispositivo
        dispositivo = Dispositivo.objects.get(id=dispositivo_id)
        
        # Guardar GPS (si el usuario dejó el campo vacío, lo guardamos como None)
        dispositivo.latitud = float(latitud) if latitud else None
        dispositivo.longitud = float(longitud) if longitud else None
        dispositivo.save()

        # Buscar el cultivo asociado y actualizar sus parámetros hidropónicos
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

    if request.method == 'POST':
        dispositivo_id = request.POST.get('dispositivo_id')
        try:
            dispositivo = Dispositivo.objects.get(id=dispositivo_id)
            mac = dispositivo.mac_address
            # Django borrará automáticamente en cascada el Cultivo y las Mediciones de este dispositivo
            dispositivo.delete()
            messages.success(request, f"La torre con MAC {mac} y todo su historial fueron eliminados correctamente.")
        except Dispositivo.DoesNotExist:
            messages.error(request, "Error: El dispositivo no existe.")
            
    return redirect('dashboard_admin')

@api_view(['POST'])
@permission_classes([AllowAny]) # Permite acceso sin cuenta de usuario
def recibir_datos_esp32(request):
    # 1. Validación de seguridad básica (API Key)
    api_key = request.headers.get('X-API-KEY')
    if api_key != "AQUAPLANTS_IOT_SECRET_2026":
        return Response({'error': 'No autorizado. API Key incorrecta.'}, status=status.HTTP_401_UNAUTHORIZED)
        
    # 2. Identificar el dispositivo automáticamente por su MAC
    mac = request.data.get('mac_address')
    if not mac:
        return Response({'error': 'Falta la mac_address en los datos.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        dispositivo = Dispositivo.objects.get(mac_address=mac)
    except Dispositivo.DoesNotExist:
        return Response({'error': f'Dispositivo con MAC {mac} no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
    # 3. Guardar la medición asociándola al dispositivo detectado
    medicion = Medicion.objects.create(
        dispositivo=dispositivo,
        temperatura=request.data.get('temperatura'),
        ph=request.data.get('ph'),
        nivel_agua=request.data.get('nivel_agua'),
        nutriente_a=request.data.get('nutriente_a'),
        nutriente_b=request.data.get('nutriente_b')
    )
    
    # 4. Motor de alertas automáticas
    try:
        cultivo = getattr(dispositivo, 'cultivo_activo', None)
        if cultivo:
            variables = {
                'TEMP': ('temperatura', 'Temperatura', '°C'),
                'PH': ('ph', 'pH', ''),
                'AGUA': ('nivel_agua', 'Nivel de agua', ''),
            }
            for variable, datos in variables.items():
                campo, nombre, unidad = datos
                valor = getattr(medicion, campo)
                if valor is None: continue
                
                regla = cultivo.reglas.filter(variable=variable).first()
                if regla and (valor < regla.rango_minimo or valor > regla.rango_maximo):
                    AlertaGenerada.objects.create(
                        medicion=medicion,
                        mensaje=f'ALERTA: {nombre} fuera del rango permitido. Valor: {valor}{unidad}.'
                    )
    except Exception as e:
        print(f'Error en motor de alertas IoT: {e}')
        
    return Response({'mensaje': 'Datos guardados correctamente'}, status=status.HTTP_201_CREATED)