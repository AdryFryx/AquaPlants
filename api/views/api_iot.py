from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Dispositivo, Medicion, AlertaGenerada


@api_view(['POST'])
@permission_classes([AllowAny])
def recibir_datos_esp32(request):
    api_key = request.headers.get('X-API-KEY')
    if api_key != "AQUAPLANTS_IOT_SECRET_2026":
        return Response({'error': 'No autorizado. API Key incorrecta.'}, status=status.HTTP_401_UNAUTHORIZED)

    mac = request.data.get('mac_address')
    if not mac:
        return Response({'error': 'Falta la mac_address en los datos.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dispositivo = Dispositivo.objects.get(mac_address=mac)
    except Dispositivo.DoesNotExist:
        return Response({'error': f'Dispositivo con MAC {mac} no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    medicion = Medicion.objects.create(
        dispositivo=dispositivo,
        temperatura=request.data.get('temperatura'),
        ph=request.data.get('ph'),
        nivel_agua=request.data.get('nivel_agua'),
        nutriente_a=request.data.get('nutriente_a'),
        nutriente_b=request.data.get('nutriente_b')
    )

    try:
        cultivos = dispositivo.cultivos.filter(activo=True).prefetch_related('reglas')
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
        print(f'Error en motor de alertas IoT: {e}')

    return Response({'mensaje': 'Datos guardados correctamente'}, status=status.HTTP_201_CREATED)