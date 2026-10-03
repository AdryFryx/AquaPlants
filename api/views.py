from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Dispositivo, Medicion
from .serializers import DispositivoSerializer, MedicionSerializer

class DispositivoViewSet(viewsets.ModelViewSet):
    queryset = Dispositivo.objects.all()
    serializer_class = DispositivoSerializer
    permission_classes = [IsAuthenticated] # Solo usuarios logueados con JWT pueden ver esto

class MedicionViewSet(viewsets.ModelViewSet):
    queryset = Medicion.objects.all()
    serializer_class = MedicionSerializer
    # Aquí el ESP32 enviará los datos (POST) y Flutter los leerá (GET)