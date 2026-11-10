import math
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
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
            return Response({'tipo_planta': cultivo.tipo_planta, 'reglas': reglas})

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
        
        contexto = {
            'rol': 'Administrador',
            'clientes': clientes,
            'dispositivos': dispositivos,
            'supervisores': supervisores,
        }
        
    elif es_supervisor(usuario_actual):
        contexto = {
            'rol': 'Supervisor',
            'informes_pendientes': InformeFalla.objects.filter(supervisor_asignado=usuario_actual, estado='PENDIENTE'),
        }

    return render(request, 'api/dashboard_admin.html', contexto)


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
    if not es_administrador(request.user): 
        return redirect('dashboard_admin')
    
    try:
        with transaction.atomic():
            user = User.objects.create(
                username=request.POST.get('username'),
                email=request.POST.get('email'),
                first_name=request.POST.get('nombre'),
                last_name=request.POST.get('apellido'),
                password=make_password(request.POST.get('password'))
            )
            
            grupo, _ = Group.objects.get_or_create(name='CLIENTE')
            user.groups.add(grupo)
            
            PerfilUsuario.objects.create(usuario=user, telefono=request.POST.get('telefono'))
            
            mac = request.POST.get('mac_address')
            instalacion = request.POST.get('nombre_instalacion')
            
            if mac and instalacion:
                dispositivo = Dispositivo.objects.create(
                    mac_address=mac,
                    usuario_encargado=user,
                    nombre_instalacion=instalacion
                )
                Cultivo.objects.create(dispositivo=dispositivo, tipo_planta="Por definir")

        messages.success(request, 'Cliente y dispositivo registrados exitosamente.')
    except Exception as e:
        messages.error(request, 'Error al registrar: Puede que el usuario o la MAC ya existan.')
        
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def editar_cliente_web(request):
    if not es_administrador(request.user): 
        return redirect('dashboard_admin')
    
    try:
        cliente = User.objects.get(id=request.POST.get('cliente_id'), groups__name='CLIENTE')
        cliente.first_name = request.POST.get('nombre')
        cliente.last_name = request.POST.get('apellido')
        cliente.email = request.POST.get('email')
        cliente.save()
        
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=cliente)
        perfil.telefono = request.POST.get('telefono')
        perfil.save()
        
        messages.success(request, 'Datos del cliente actualizados.')
    except Exception as e:
        messages.error(request, 'Error al actualizar el cliente.')
        
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def eliminar_cliente_web(request):
    if not es_administrador(request.user): 
        return redirect('dashboard_admin')
    
    try:
        cliente = User.objects.get(id=request.POST.get('cliente_id'), groups__name='CLIENTE')
        cliente.delete()
        messages.success(request, 'Cliente eliminado completamente del sistema.')
    except Exception as e:
        messages.error(request, 'Error al intentar eliminar al cliente.')
        
    return redirect('dashboard_admin')


@login_required(login_url='login_web')
@require_POST
def resolver_informe(request):
    if not es_supervisor(request.user):
        return redirect('dashboard_admin')
        
    informe_id = request.POST.get('informe_id')
    try:
        informe = InformeFalla.objects.get(id=informe_id, supervisor_asignado=request.user)
        informe.estado = 'RESUELTO'
        informe.save()
        messages.success(request, '¡Problema marcado como resuelto!')
    except InformeFalla.DoesNotExist:
        messages.error(request, 'No se pudo actualizar el informe.')
        
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