import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.horus_client import HorusTL1Client

IP = "192.168.1.105"
PORT = 4370
PASS = "0"

client = HorusTL1Client(IP, port=PORT, password=PASS)
if client.connect():
    print("✅ Conectado")
    
    # 1. Obtener TODOS los registros de asistencia sin filtrar
    try:
        raw = client.conn.get_attendance()
        print(f"📊 raw_attendance: {len(raw)} registros")
        for i, att in enumerate(raw[:10]):  # primeros 10
            try:
                print(f"   {i}: user_id={att.user_id}, timestamp={att.timestamp}, status={att.status}")
            except Exception as e:
                print(f"   {i}: ERROR al acceder al registro: {e}")
    except Exception as e:
        print(f"❌ Error en get_attendance(): {e}")
    
    # 2. Listar usuarios (para confirmar que el 9999 existe)
    users = client.get_users()
    print(f"👥 Usuarios: {len(users)}")
    for u in users:
        if u['uid'] == 9999:
            print(f"   ✅ Usuario 9999 encontrado: {u['name']}")
    
    client.disconnect()
else:
    print("❌ No se pudo conectar")