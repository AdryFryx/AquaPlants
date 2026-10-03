from  rest_framework import serializers
from .models import Dispositivo, Medicion

class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = '__all__'

class MedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicion
        fields = '__all__'