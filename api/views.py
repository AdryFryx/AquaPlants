
import math
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Dispositivo,
    Medicion,
    ReglaUmbral,
    AlertaGenerada
)
from .serializers import DispositivoSerializer, MedicionSerializer


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
            queryset = Medicion.objects.filter(
                dispositivo__usuario_encargado=usuario
            )

        dias = self.request.query_params.get('dias')

        if dias:
            try:
                fecha_inicio = timezone.now() - timedelta(days=int(dias))
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


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def actualizar_configuracion(request):
    try:
        dispositivo = request.user.dispositivos.first()

        if dispositivo is None:
            return Response(
                {'error': 'No tienes un dispositivo asociado.'},
                status=400
            )

        cultivo = getattr(dispositivo, 'cultivo_activo', None)

        if cultivo is None:
            return Response(
                {'error': 'El dispositivo no tiene un cultivo activo.'},
                status=400
            )

        # CONSULTAR CONFIGURACIÓN
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
                    status=400
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

            if campo_min not in request.data and campo_max not in request.data:
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
                    status=400
                )

            try:
                minimo = float(minimo)
                maximo = float(maximo)
            except (ValueError, TypeError):
                return Response(
                    {'error': f'Los valores de {variable} deben ser numéricos.'},
                    status=400
                )

            if not math.isfinite(minimo) or not math.isfinite(maximo):
                return Response(
                    {'error': f'Los valores de {variable} no son válidos.'},
                    status=400
                )

            if minimo >= maximo:
                return Response(
                    {'error': f'El mínimo de {variable} debe ser menor que el máximo.'},
                    status=400
                )

            reglas[variable] = {
                'rango_minimo': minimo,
                'rango_maximo': maximo
            }

        # GUARDAR CONFIGURACIÓN
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
        }, status=200)

    except Exception as e:
        print(f'Error en configuración: {e}')
        return Response(
            {'error': 'No se pudo procesar la configuración.'},
            status=400
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gestionar_alertas(request):
    dispositivo = request.user.dispositivos.first()

    if dispositivo is None:
        if request.method == 'GET':
            return Response([])

        return Response(
            {'error': 'No tienes un dispositivo asociado.'},
            status=400
        )

    if request.method == 'GET':
        alertas = AlertaGenerada.objects.filter(
            medicion__dispositivo=dispositivo
        ).order_by('-id')[:15]

        data = [
            {'id': alerta.id, 'mensaje': alerta.mensaje}
            for alerta in alertas
        ]

        return Response(data)

    alerta_id = request.data.get('id')

    if alerta_id is None:
        return Response(
            {'error': 'Debes proporcionar el ID de la alerta.'},
            status=400
        )

    eliminadas, _ = AlertaGenerada.objects.filter(
        id=alerta_id,
        medicion__dispositivo=dispositivo
    ).delete()

    if eliminadas == 0:
        return Response(
            {'error': 'No se encontró la alerta.'},
            status=404
        )

    return Response({
        'mensaje': 'Alerta resuelta exitosamente'
    })
