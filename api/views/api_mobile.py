import math
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from ..models import Dispositivo, Medicion, ReglaUmbral, AlertaGenerada, InformeFalla, Cultivo
from ..serializers import DispositivoSerializer, MedicionSerializer, RegistroSerializer


class DispositivoViewSet(viewsets.ModelViewSet):
    serializer_class = DispositivoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_staff:
            return Dispositivo.objects.all()
        return Dispositivo.objects.filter(usuario_encargado=usuario)


class MedicionViewSet(viewsets.ModelViewSet):
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_staff:
            queryset = Medicion.objects.all()
        else:
            queryset = Medicion.objects.filter(dispositivo__usuario_encargado=usuario)

        dispositivo_id = self.request.query_params.get('dispositivo_id')
        if dispositivo_id:
            queryset = queryset.filter(dispositivo_id=dispositivo_id)

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

        if not dias and self.action == 'list':
            return queryset.order_by('-timestamp')[:20]

        return queryset.order_by('-timestamp')
    
    def perform_create(self, serializer):
        medicion = serializer.save()
        try:
            cultivos = medicion.dispositivo.cultivos.filter(activo=True).prefetch_related('reglas')
            variables = {
                'TEMP': ('temperatura', 'Temperatura', '°C'),
                'PH': ('ph', 'pH', ''),
                'AGUA': ('nivel_agua', 'Nivel de agua', '%'),
                'NUT_A': ('nutriente_a', 'Nutriente A', ' ml/L'),
                'NUT_B': ('nutriente_b', 'Nutriente B', ' ml/L'),
            }
            for cultivo in cultivos:
                for variable, (campo, nombre, unidad) in variables.items():
                    valor = getattr(medicion, campo)
                    if valor is None:
                        continue
                    regla = cultivo.reglas.filter(variable=variable).first()
                    if regla and (valor < regla.rango_minimo or valor > regla.rango_maximo):
                        AlertaGenerada.objects.create(
                            medicion=medicion,
                            mensaje=f'ALERTA ({cultivo.tipo_planta}): {nombre} fuera de rango ({valor}{unidad}). Ideal: {regla.rango_minimo}-{regla.rango_maximo}{unidad}.'
                        )
        except Exception as e:
            print(f'Error en el motor de alertas: {e}')


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


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def actualizar_configuracion(request):
    try:
        dispositivo = request.user.dispositivos.first()
        if dispositivo is None:
            return Response({'error': 'No tienes un dispositivo asociado.'}, status=status.HTTP_400_BAD_REQUEST)

        cultivo = dispositivo.cultivos.filter(activo=True).first()
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

            reglas[variable] = {'rango_minimo': minimo, 'rango_maximo': maximo}

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reportar_falla_cliente(request):
    """NUEVO: Permite al cliente reportar una falla desde la app móvil hacia el Admin."""
    dispositivo = request.user.dispositivos.first()
    if dispositivo is None:
        return Response({'error': 'No tienes un dispositivo asociado.'}, status=status.HTTP_400_BAD_REQUEST)

    motivo = str(request.data.get('motivo', '')).strip()
    detalle = str(request.data.get('detalle', '')).strip()

    if not motivo:
        return Response({'error': 'Debes seleccionar un motivo.'}, status=status.HTTP_400_BAD_REQUEST)

    if motivo == 'Otro':
        if not detalle:
            return Response({'error': 'Debes describir el problema.'}, status=status.HTTP_400_BAD_REQUEST)
        texto_reporte = f"Otro: {detalle}"
    else:
        texto_reporte = motivo

    InformeFalla.objects.create(
        dispositivo=dispositivo,
        reporte_cliente=texto_reporte,
        descripcion='',
        estado='POR_ASIGNAR'
    )

    return Response({'mensaje': 'Reporte enviado al administrador correctamente.'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mis_cultivos(request):
    """Devuelve todas las plantaciones asignadas a los dispositivos del usuario."""
    cultivos = Cultivo.objects.filter(
        dispositivo__usuario_encargado=request.user,
        activo=True
    ).select_related('dispositivo').prefetch_related('reglas')

    data = []
    for c in cultivos:
        reglas = {
            r.variable: {'minimo': r.rango_minimo, 'maximo': r.rango_maximo}
            for r in c.reglas.all()
        }
        data.append({
            'id': c.id,
            'tipo_planta': c.tipo_planta,
            'semanas_ciclo': c.semanas_ciclo,
            'dispositivo_id': c.dispositivo.id,
            'dispositivo_nombre': c.dispositivo.nombre_instalacion,
            'reglas': reglas,
        })

    return Response(data)