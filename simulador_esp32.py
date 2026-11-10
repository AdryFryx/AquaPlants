import time
import random
import requests

BASE_URL = "https://aquaplants.onrender.com/api"
API_URL = f"{BASE_URL}/mediciones/"
TOKEN_URL = f"{BASE_URL}/token/"

DISPOSITIVO_ID = 1

# 1. Pon las credenciales de tu usuario de prueba
USUARIO = "gabriel" # O el correo exacto que usaste
CONTRASENA = "HolaBuenas890." # Reemplaza con la contraseña real

print("Iniciando simulación del ESP32 para AquaPlants...")
print("Obteniendo token de acceso...")

# 2. Hacemos login para obtener el JWT Token
try:
    login_response = requests.post(TOKEN_URL, json={"username": USUARIO, "password": CONTRASENA})
    if login_response.status_code == 200:
        access_token = login_response.json().get('access')
        print("✅ Token obtenido exitosamente.\n")
    else:
        print(f"❌ Error al iniciar sesión: {login_response.text}")
        exit() # Detiene el script si las credenciales están mal
except requests.exceptions.ConnectionError:
    print("❌ Error de conexión con Render.")
    exit()

# 3. Guardamos el token en los headers para los envíos
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

print("Presiona Ctrl+C para detener el envío de datos.\n")

while True:
    temperatura = round(random.uniform(20.0, 26.0), 1)
    ph = round(random.uniform(5.5, 6.5), 1)
    nivel_agua = round(random.uniform(70.0, 100.0), 1)

    payload = {
        "dispositivo": DISPOSITIVO_ID,
        "temperatura": temperatura,
        "ph": ph,
        "nivel_agua": nivel_agua
    }

    try:
        # Agregamos timeout=10 (espera máximo 10 segundos antes de rendirse y seguir)
        respuesta = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        
        if respuesta.status_code == 201:
            print(f"✅ Enviado -> Temp: {temperatura}°C | pH: {ph} | Agua: {nivel_agua}%")
        elif respuesta.status_code == 401:
            print("⚠️ El token expiró por seguridad. Cancela el script (Ctrl+C) y vuélvelo a ejecutar.")
            break
        else:
            print(f"⚠️ Error al enviar: {respuesta.status_code} - {respuesta.text}")
            
    except requests.exceptions.Timeout:
        print("⏳ Render tardó demasiado en responder. Saltando al siguiente intento...")
    except requests.exceptions.ConnectionError:
        print("❌ Error de red transitorio.")

    time.sleep(9)