import requests
import random
import time

URL = "https://aquaplants.onrender.com/datos-esp32/"  # Cambia a tu URL local si estás en pruebas

# Puedes cambiar esta MAC por la de cualquier cliente registrado en el sistema
MAC_ADDRESS = "00:1B:44:11:3A:B7" 

headers = {
    "Content-Type": "application/json",
    "X-API-KEY": "AQUAPLANTS_IOT_SECRET_2026" # La llave de seguridad estática
}

print(f"Iniciando simulador para torre con MAC: {MAC_ADDRESS}")

while True:
    payload = {
        "mac_address": MAC_ADDRESS,
        "temperatura": round(random.uniform(18.0, 30.0), 1),
        "ph": round(random.uniform(5.5, 7.5), 1),
        "nivel_agua": round(random.uniform(20.0, 100.0), 1),
        "nutriente_a": round(random.uniform(1.0, 5.0), 1),
        "nutriente_b": round(random.uniform(1.0, 5.0), 1)
    }

    try:
        response = requests.post(URL, json=payload, headers=headers)
        if response.status_code == 201:
            print(f"[OK] Datos enviados: Temp {payload['temperatura']}°C, pH {payload['ph']}")
        else:
            print(f"[ERROR] {response.status_code}: {response.json()}")
    except Exception as e:
        print(f"[ERROR DE CONEXIÓN] {e}")

    # Esperar 5 minutos (300 segundos) para el siguiente envío
    time.sleep(300)