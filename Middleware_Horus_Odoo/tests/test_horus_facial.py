# tests/test_horus_facial.py (versión corregida)
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.horus_client import HorusTL1Client

# ===== CONFIGURACIÓN =====
IP_HORUS = "192.168.1.105"
PORT_HORUS = 4370
PASSWORD = "0"
TEST_UID = 9999
TEST_NAME = "PRUEBA FACIAL"
# =========================

client = HorusTL1Client(IP_HORUS, port=PORT_HORUS, password=PASSWORD)

if not client.connect():
    print("❌ No se pudo conectar.")
    sys.exit(1)

try:
    # 1. Listar usuarios actuales
    print("\n📋 Listando usuarios actuales...")
    users = client.get_users()
    print(f"Total: {len(users)}")
    for u in users:
        print(f"   - {u['uid']}: {u['name']}")

    # 2. Crear usuario de prueba (si no existe)
    if not any(u['uid'] == TEST_UID for u in users):
        print(f"\n👤 Creando usuario de prueba '{TEST_NAME}' con UID {TEST_UID}...")
        client.create_user(TEST_UID, TEST_NAME)
    else:
        print(f"\n👤 El usuario {TEST_UID} ya existe, se reutilizará.")

    # 3. Activar registro facial (capturamos cualquier error)
    print("\n📸 Intentando activar registro facial...")
    client.enroll_face(TEST_UID)
    
    # 4. Esperar unos segundos para que el usuario pueda reaccionar
    print("⏳ Esperando 15 segundos para posible captura manual...")
    time.sleep(15)

    # 5. Verificar asistencias (opcional)
    print("\n📊 Obteniendo asistencias recientes...")
    attends = client.get_attendance()
    print(f"Asistencias totales en dispositivo: {len(attends)}")
    # Mostrar últimas 5
    for att in attends[-5:]:
        print(f"   - {att['user_id']} : {att['timestamp']}")

finally:
    # Opcional: eliminar usuario de prueba (descomentar si se desea)
    # print("\n🗑️ Eliminando usuario de prueba...")
    # client.delete_user(TEST_UID)
    
    client.disconnect()