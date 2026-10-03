from django.contrib import admin
from .models import Dispositivo, Cultivo, ReglaUmbral, Medicion, AlertaGenerada
# Register your models here.
admin.site.register(Dispositivo)
admin.site.register(Cultivo)
admin.site.register(ReglaUmbral)
admin.site.register(Medicion)
admin.site.register(AlertaGenerada)