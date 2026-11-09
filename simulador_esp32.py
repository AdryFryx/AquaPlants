import time
import random
import requests

# 1. ACTUALIZADO: URL de tu API en la nube (Render)
API_URL = "https://aquaplants.onrender.com/api/mediciones/"

# El ID de tu dispositivo en la base de datos (verifica que sea el 1)
DISPOSITIVO_ID = 1

print("Iniciando simulación del ESP32 para AquaPlants...")
print("Presiona Ctrl+C para detener el envío de datos.\n")

while True:
    # Generamos datos aleatorios realistas para hidroponía
    temperatura = round(random.uniform(20.0, 26.0), 1)  # 20°C a 26°C
    ph = round(random.uniform(5.5, 6.5), 1)             # pH ideal para lechugas
    nivel_agua = round(random.uniform(70.0, 100.0), 1)  # Porcentaje de estanque

    # Armamos el paquete de datos en formato JSON
    payload = {
        "dispositivo": DISPOSITIVO_ID,
        "temperatura": temperatura,
        "ph": ph,
        "nivel_agua": nivel_agua
    }

    try:
        # Enviamos los datos a Django (Método POST)
        respuesta = requests.post(API_URL, json=payload)
        
        if respuesta.status_code == 201:
            print(f"✅ Enviado -> Temp: {temperatura}°C | pH: {ph} | Agua: {nivel_agua}%")
        else:
            # 2. ACTUALIZADO: Se arregló el error de salto de línea en el print
            print(f"⚠️ Error al enviar: {respuesta.status_code} - {respuesta.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: Revisa si el servidor en Render está funcionando.")

    # El ESP32 "duerme" 5 segundos antes de enviar el siguiente dato
    time.sleep(5)