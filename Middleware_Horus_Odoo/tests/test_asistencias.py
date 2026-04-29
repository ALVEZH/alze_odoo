# tests/test_asistencias.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.horus_client import HorusTL1Client
from src.database import init_db, guardar_empleado, obtener_asistencias_pendientes, registrar_log

# Configuración
IP_HORUS = "192.168.1.105"
PORT = 4370
PASS = "0"

def main():
    init_db()
    # Asegurar que existe un empleado de prueba en BD
    guardar_empleado(9999, "9999", "EMPLEADO PRUEBA")
    
    client = HorusTL1Client(IP_HORUS, port=PORT, password=PASS)
    if not client.connect():
        print("❌ No se pudo conectar")
        return

    print("📊 Obteniendo asistencias del dispositivo...")
    attends = client.get_attendance()
    print(f"Total asistencias: {len(attends)}")
    
    # Mostrar las últimas 5
    for att in attends[-5:]:
        print(f"   - {att['user_id']} : {att['timestamp']}")
    
    client.disconnect()
    
    # Consultar asistencias pendientes en BD
    pendientes = obtener_asistencias_pendientes()
    print(f"\n📦 Asistencias pendientes en BD: {len(pendientes)}")
    for p in pendientes[:5]:
        print(f"   - {p['pin_horus']} : {p['fecha_hora']}")
    
    registrar_log('INFO', 'test_asistencias', "Prueba de asistencias completada")
    print("✅ Prueba finalizada. Revisa logs en BD.")

if __name__ == '__main__':
    main()