from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Dispositivo, Medicion, ReglaUmbral, Cultivo, AlertaGenerada
from .serializers import DispositivoSerializer, MedicionSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

class DispositivoViewSet(viewsets.ModelViewSet):
    serializer_class = DispositivoSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        usuario = self.request.user
        
        # 1. Administrador (Superusuario en Django): Ve todo el sistema
        if usuario.is_superuser:
            return Dispositivo.objects.all()
            
        # 2. Supervisor (Staff en Django): Ve todo para soporte técnico
        elif usuario.is_staff:
            return Dispositivo.objects.all()
            
        # 3. Cliente/Encargado normal: Ve estrictamente su propia torre
        return Dispositivo.objects.filter(usuario_encargado=usuario)

from datetime import timedelta
from django.utils import timezone

class MedicionViewSet(viewsets.ModelViewSet):
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        
        # Filtramos correctamente usando el nombre de tu modelo (usuario_encargado)
        if usuario.is_superuser or usuario.is_staff:
            queryset = Medicion.objects.all()
        else:
            queryset = Medicion.objects.filter(dispositivo__usuario_encargado=usuario)
        
        dias = self.request.query_params.get('dias')
        if dias:
            try:
                fecha_inicio = timezone.now() - timedelta(days=int(dias))
                queryset = queryset.filter(timestamp__gte=fecha_inicio)
            except ValueError:
                pass
                
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        medicion = serializer.save()
        try:
            cultivo = medicion.dispositivo.cultivo_activo
            regla_temp = cultivo.reglas.filter(variable='TEMP').first()
            if regla_temp and medicion.temperatura:
                if medicion.temperatura > regla_temp.rango_maximo:
                    AlertaGenerada.objects.create(
                        medicion=medicion,
                        mensaje=f"CRÍTICO: Temperatura de {medicion.temperatura}°C supera el límite de {regla_temp.rango_maximo}°C"
                    )
        except Exception as e:
            print(f"Error en el motor de alertas: {e}")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_configuracion(request):
    try:
        dispositivo = request.user.dispositivos.first()
        cultivo = dispositivo.cultivo_activo

        cultivo.tipo_planta = request.data.get('tipo_planta', cultivo.tipo_planta)
        cultivo.save()

        ReglaUmbral.objects.update_or_create(
            cultivo=cultivo,
            variable='TEMP',
            defaults={
                'rango_minimo': 10.0,
                'rango_maximo': float(request.data.get('temp_max', 25.0))
            }
        )
        return Response({'mensaje':'Configuración guardada exitosamente'})
    except Exception as e:
        return Response({'error':str(e)}, status=400)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gestionar_alertas(request):
    if request.method == 'GET':
        dispositivo = request.user.dispositivos.first()
        alertas = AlertaGenerada.objects.filter(medicion__dispositivo=dispositivo).order_by('-id')[:15]

        data = [{'id': a.id, 'mensaje': a.mensaje} for a in alertas]
        return Response(data)

    elif request.method == 'POST':
        alerta_id = request.data.get('id')
        AlertaGenerada.objects.filter(id=alerta_id).delete()
        return Response({'mensaje': 'Alerta resuelta exitosamente'})