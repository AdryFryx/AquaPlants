import time
import random
import requests

# Usa esta URL https://aquaplants.onrender.com/datos-esp32/ para producción en Render (o cambia a http://127.0.0.1:8000/datos-esp32/ para pruebas locales)
API_URL = "http://127.0.0.1:8000/datos-esp32/"

# Solo cambias esta MAC por la de cualquier torre registrada en tu panel Admin
MAC_ADDRESS = "00:11:22:33:44:55"

headers = {
    "Content-Type": "application/json",
    "X-API-KEY": "AQUAPLANTS_IOT_SECRET_2026"
}

print(f"Iniciando simulación del ESP32 para MAC: {MAC_ADDRESS}")
print("Presiona Ctrl+C para detener el envío de datos.\n")

while True:
    temperatura = round(random.uniform(20.0, 26.0), 1)
    ph = round(random.uniform(5.5, 6.5), 1)
    nivel_agua = round(random.uniform(70.0, 100.0), 1)
    nutriente_a = round(random.uniform(1.0, 5.0), 1)
    nutriente_b = round(random.uniform(1.0, 5.0), 1)

    payload = {
        "mac_address": MAC_ADDRESS,
        "temperatura": temperatura,
        "ph": ph,
        "nivel_agua": nivel_agua,
        "nutriente_a": nutriente_a,
        "nutriente_b": nutriente_b
    }

    try:
        respuesta = requests.post(API_URL, json=payload, headers=headers, timeout=10)

        if respuesta.status_code == 201:
            print(
                f"✅ Enviado -> Temp: {temperatura}°C | pH: {ph} | "
                f"Agua: {nivel_agua}% | Nut A: {nutriente_a} | Nut B: {nutriente_b}"
            )
        else:
            print(f"⚠️ Error al enviar: {respuesta.status_code} - {respuesta.text}")

    except requests.exceptions.Timeout:
        print("⏳ El servidor tardó demasiado en responder. Saltando al siguiente intento...")
    except requests.exceptions.ConnectionError:
        print("❌ Error de red transitorio.")

    time.sleep(10)