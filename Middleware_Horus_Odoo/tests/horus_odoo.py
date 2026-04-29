# scripts/forzar_creacion_odoo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.horus_client import HorusTL1Client
from src.odoo_client import OdooClient
from src.database import init_db, guardar_empleado, guardar_mapeo

# ===== CONFIGURACIÓN =====
HORUS_IP = "192.168.1.105"
HORUS_PORT = 4370
HORUS_PASSWORD = "0"
ODOO_URL = "http://devo.uaalze.com"
ODOO_DB = "bd_odoo1"
ODOO_USER = "admin"
ODOO_PASS = "admin"
# =========================

def main():
    print("🚀 Forzando creación de usuarios Horus en Odoo...")
    init_db()
    
    # Conectar a Horus
    horus = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
    if not horus.connect():
        print("❌ No se pudo conectar a Horus")
        return
    print("✅ Conectado a Horus")
    
    device_users = horus.get_users()
    print(f"📋 Usuarios en dispositivo: {len(device_users)}")
    
    # Conectar a Odoo
    odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    if not odoo.connect():
        print("❌ No se pudo conectar a Odoo")
        horus.disconnect()
        return
    print("✅ Conectado a Odoo")
    
    # Obtener empleados existentes en Odoo para búsqueda por nombre
    odoo_employees = odoo.search_employees([], fields=['id', 'name'])
    odoo_by_name = {emp['name'].strip().lower(): emp['id'] for emp in odoo_employees}
    
    creados = 0
    actualizados = 0
    errores = 0
    
    for u in device_users:
        user_id = u['user_id']   # PIN visible (puede ser alfanumérico)
        uid = u['uid']            # UID interno de Horus
        nombre = u['name']
        
        print(f"\n--- Procesando {nombre} (PIN: {user_id}, UID: {uid}) ---")
        
        # Buscar en Odoo por nombre (ignorando mayúsculas)
        nombre_lower = nombre.strip().lower()
        if nombre_lower in odoo_by_name:
            id_odoo = odoo_by_name[nombre_lower]
            print(f"   🔍 Empleado encontrado en Odoo por nombre: ID {id_odoo}")
        else:
            # Crear nuevo empleado en Odoo
            try:
                id_odoo = odoo.create_employee({'name': nombre})
                print(f"   ➕ Empleado creado en Odoo con ID {id_odoo}")
                odoo_by_name[nombre_lower] = id_odoo
                creados += 1
            except Exception as e:
                print(f"   ❌ Error creando empleado: {e}")
                errores += 1
                continue
        
        # Guardar en BD local y mapeo
        guardar_empleado(id_odoo, user_id, nombre, uid_horus=uid)
        guardar_mapeo(id_odoo, user_id, uid)
        print(f"   ✅ Mapeo guardado: Odoo ID {id_odoo} <-> PIN {user_id}")
        actualizados += 1
    
    print("\n" + "="*50)
    print(f"✅ Proceso completado:")
    print(f"   - Nuevos empleados en Odoo: {creados}")
    print(f"   - Mapeos actualizados: {actualizados}")
    print(f"   - Errores: {errores}")
    
    horus.disconnect()

if __name__ == '__main__':
    main()