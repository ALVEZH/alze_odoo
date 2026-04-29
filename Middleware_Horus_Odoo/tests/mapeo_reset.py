# scripts/reparar_mapeos.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.horus_client import HorusTL1Client
from src.odoo_client import OdooClient
from src.database import get_db_connection

# Configuración
HORUS_IP = "192.168.1.105"
HORUS_PORT = 4370
HORUS_PASSWORD = "0"
ODOO_URL = "http://localhost:8069"
ODOO_DB = "middleware_pruebas"
ODOO_USER = "pinzonelias501@gmail.com"
ODOO_PASS = "admin"

def main():
    print("🚀 Reparando mapeos...")
    
    # Conectar a Horus
    horus = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
    if not horus.connect():
        print("❌ No se pudo conectar a Horus")
        return
    device_users = horus.get_users()
    horus.disconnect()
    print(f"✅ Usuarios en Horus: {len(device_users)}")
    
    # Conectar a Odoo
    odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    if not odoo.connect():
        print("❌ No se pudo conectar a Odoo")
        return
    
    # Obtener todos los empleados de Odoo
    odoo_emps = odoo.search_employees([], fields=['id', 'name'])
    odoo_by_name = {emp['name'].strip().lower(): emp['id'] for emp in odoo_emps}
    print(f"✅ Empleados en Odoo: {len(odoo_emps)}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Para cada usuario de Horus, actualizar con el ID correcto de Odoo
    for u in device_users:
        user_id = u['user_id']
        uid = u['uid']
        nombre = u['name']
        nombre_lower = nombre.strip().lower()
        
        if nombre_lower in odoo_by_name:
            id_odoo = odoo_by_name[nombre_lower]
            print(f"\n--- {nombre} (PIN {user_id}) -> ID Odoo {id_odoo} ---")
            
            # Actualizar empleado en BD
            cursor.execute("""
                UPDATE empleados 
                SET id_odoo = ?, nombre = ?, uid_horus = ? 
                WHERE pin_horus = ?
            """, (id_odoo, nombre, uid, user_id))
            
            # Actualizar mapeo
            cursor.execute("""
                INSERT OR REPLACE INTO mapeo_pins (id_odoo, pin_horus, uid_horus) 
                VALUES (?, ?, ?)
            """, (id_odoo, user_id, uid))
            conn.commit()
            print(f"   ✅ Actualizado")
        else:
            print(f"\n--- {nombre} (PIN {user_id}) no encontrado en Odoo ---")
    
    # Eliminar mapeos huérfanos (que no corresponden a ningún usuario actual)
    pins_horus = {u['user_id'] for u in device_users}
    cursor.execute("SELECT pin_horus FROM mapeo_pins")
    for (pin,) in cursor.fetchall():
        if pin not in pins_horus:
            cursor.execute("DELETE FROM mapeo_pins WHERE pin_horus = ?", (pin,))
            print(f"🗑️ Eliminado mapeo huérfano para PIN {pin}")
    conn.commit()
    conn.close()
    
    print("\n✅ Reparación completada. Ahora puedes reiniciar el middleware.")

if __name__ == '__main__':
    main()