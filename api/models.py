from django.db import models
from django.contrib.auth.models import User

class Dispositivo(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, help_text="MAC del ESP32")
    usuario_encargado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispositivos')
    nombre_instalacion = models.CharField(max_length=100)
    estado_conexion = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_instalacion} - {self.mac_address}"

class Cultivo(models.Model):
    dispositivo = models.OneToOneField(Dispositivo, on_delete=models.CASCADE, related_name='cultivo_activo')
    tipo_planta = models.CharField(max_length=100)
    fecha_inicio = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tipo_planta} ({self.dispositivo.nombre_instalacion})"

class ReglaUmbral(models.Model):
    VARIABLE_CHOICES = [
        ('TEMP', 'Temperatura'),
        ('PH', 'Nivel de pH'),
        ('AGUA', 'Nivel de Agua'),
    ]
    cultivo = models.ForeignKey(Cultivo, on_delete=models.CASCADE, related_name='reglas')
    variable = models.CharField(max_length=10, choices=VARIABLE_CHOICES)
    rango_minimo = models.FloatField()
    rango_maximo = models.FloatField()

    def __str__(self):
        return f"Regla {self.variable} para {self.cultivo.tipo_planta}"

class Medicion(models.Model):
    # Esta es la tabla masiva que en producción pasaremos a TimescaleDB
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='mediciones')
    temperatura = models.FloatField(null=True, blank=True)
    nivel_agua = models.FloatField(null=True, blank=True)
    ph = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Medición {self.dispositivo.mac_address} a las {self.timestamp.strftime('%H:%M:%S')}"

class AlertaGenerada(models.Model):
    medicion = models.ForeignKey(Medicion, on_delete=models.CASCADE)
    mensaje = models.CharField(max_length=255)
    resuelta = models.BooleanField(default=False)
    fecha_alerta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ALERTA: {self.mensaje}"