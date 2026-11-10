from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from .permissions import es_administrador, es_supervisor
import math
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Dispositivo,
    Medicion,
    ReglaUmbral,
    AlertaGenerada
)

from .serializers import (
    DispositivoSerializer,
    MedicionSerializer,
    RegistroSerializer
)


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

        return Dispositivo.objects.filter(
            usuario_encargado=usuario
        )


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
            queryset = Medicion.objects.filter(
                dispositivo__usuario_encargado=usuario
            )

        dias = self.request.query_params.get('dias')

        if dias:
            try:
                cantidad_dias = int(dias)

                if cantidad_dias < 0:
                    return queryset.none()

                fecha_inicio = timezone.now() - timedelta(
                    days=cantidad_dias
                )

                queryset = queryset.filter(
                    timestamp__gte=fecha_inicio
                )

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

                regla = cultivo.reglas.filter(
                    variable=variable
                ).first()

                if regla and (
                    valor < regla.rango_minimo
                    or valor > regla.rango_maximo
                ):
                    AlertaGenerada.objects.create(
                        medicion=medicion,
                        mensaje=(
                            f'ALERTA: {nombre} fuera del rango permitido. '
                            f'Valor: {valor}{unidad}. '
                            f'Rango: {regla.rango_minimo}-'
                            f'{regla.rango_maximo}{unidad}.'
                        )
                    )

        except Exception as e:
            print(f'Error en el motor de alertas: {e}')


# =====================================================
# REGISTRO PUBLICO DE CLIENTES
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

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# =====================================================
# CONFIGURACION DEL CULTIVO
# =====================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def actualizar_configuracion(request):
    try:
        dispositivo = request.user.dispositivos.first()

        if dispositivo is None:
            return Response(
                {'error': 'No tienes un dispositivo asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cultivo = getattr(dispositivo, 'cultivo_activo', None)

        if cultivo is None:
            return Response(
                {'error': 'El dispositivo no tiene un cultivo activo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # CONSULTAR CONFIGURACION
        if request.method == 'GET':
            reglas = {
                regla.variable: {
                    'minimo': regla.rango_minimo,
                    'maximo': regla.rango_maximo
                }
                for regla in cultivo.reglas.all()
            }

            return Response({
                'tipo_planta': cultivo.tipo_planta,
                'reglas': reglas
            })

        # ACTUALIZAR TIPO DE PLANTA
        tipo_planta = request.data.get('tipo_planta')

        if tipo_planta is not None:
            tipo_planta = str(tipo_planta).strip()

            if not tipo_planta or len(tipo_planta) > 100:
                return Response(
                    {'error': 'El nombre de la planta no es válido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cultivo.tipo_planta = tipo_planta

        # VARIABLES Y CAMPOS RECIBIDOS
        variables = {
            'TEMP': ('temp_min', 'temp_max'),
            'PH': ('ph_min', 'ph_max'),
            'AGUA': ('agua_min', 'agua_max'),
        }

        reglas = {}

        for variable, campos in variables.items():
            campo_min, campo_max = campos

            if (
                campo_min not in request.data
                and campo_max not in request.data
            ):
                continue

            regla_actual = cultivo.reglas.filter(
                variable=variable
            ).first()

            minimo = request.data.get(
                campo_min,
                regla_actual.rango_minimo if regla_actual else None
            )

            maximo = request.data.get(
                campo_max,
                regla_actual.rango_maximo if regla_actual else None
            )

            if minimo is None or maximo is None:
                return Response(
                    {'error': f'Faltan valores para {variable}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                minimo = float(minimo)
                maximo = float(maximo)

            except (ValueError, TypeError):
                return Response(
                    {
                        'error':
                        f'Los valores de {variable} deben ser numéricos.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not math.isfinite(minimo) or not math.isfinite(maximo):
                return Response(
                    {'error': f'Los valores de {variable} no son válidos.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if minimo >= maximo:
                return Response(
                    {
                        'error':
                        f'El mínimo de {variable} debe ser menor que el máximo.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            reglas[variable] = {
                'rango_minimo': minimo,
                'rango_maximo': maximo
            }

        # GUARDAR CONFIGURACION
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

        return Response(
            {'error': 'No se pudo procesar la configuración.'},
            status=status.HTTP_400_BAD_REQUEST
        )


# =====================================================
# GESTION DE ALERTAS
# =====================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gestionar_alertas(request):
    usuario = request.user

    if usuario.is_superuser or usuario.is_staff:
        alertas_queryset = AlertaGenerada.objects.all()
    else:
        alertas_queryset = AlertaGenerada.objects.filter(
            medicion__dispositivo__usuario_encargado=usuario
        )

    if request.method == 'GET':
        alertas = alertas_queryset.select_related(
            'medicion',
            'medicion__dispositivo'
        ).order_by('-id')[:15]

        data = [
            {
                'id': alerta.id,
                'mensaje': alerta.mensaje
            }
            for alerta in alertas
        ]

        return Response(data)

    alerta_id = request.data.get('id')

    if alerta_id is None:
        return Response(
            {'error': 'Debes proporcionar el ID de la alerta.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    eliminadas, _ = alertas_queryset.filter(
        id=alerta_id
    ).delete()

    if eliminadas == 0:
        return Response(
            {'error': 'No se encontró la alerta.'},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        'mensaje': 'Alerta resuelta exitosamente.'
    })

def login_web(request):
    # 1. Si ya tiene la sesión iniciada, lo mandamos directo al dashboard
    if request.user.is_authenticated:
        return redirect('dashboard_admin') # Esta ruta la crearemos en el siguiente paso

    # 2. Si el usuario presiona el botón "Iniciar Sesión" (Método POST)
    if request.method == 'POST':
        usuario = request.POST.get('username')
        contrasena = request.POST.get('password')
        
        # Django verifica si el usuario y clave existen en la base de datos
        user = authenticate(request, username=usuario, password=contrasena)
        
        if user is not None:
            # Verificamos si tiene el rol correcto usando las funciones de tu permissions.py
            if es_administrador(user) or es_supervisor(user):
                auth_login(request, user) # Creamos la cookie de sesión
                return redirect('dashboard_admin')
            else:
                messages.error(request, 'No tienes permisos de Administrador o Supervisor para entrar aquí.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            
    # 3. Si solo está cargando la página (Método GET), mostramos el HTML en blanco
    return render(request, 'api/login_web.html')