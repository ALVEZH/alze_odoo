#!/usr/bin/env python3
# scripts/inicializar_fotos.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.odoo_client import OdooClient
from src.database import get_db_connection

ODOO_URL = "http://localhost:8069"
ODOO_DB = "middleware_pruebas"
ODOO_USER = "pinzonelias501@gmail.com"
ODOO_PASS = "admin"

def main():
    print("🚀 Inicializando flags de foto para empleados existentes...")
    odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    if not odoo.connect():
        print("❌ No se pudo conectar a Odoo")
        return

    # Obtener todos los empleados de Odoo con sus fotos
    employees = odoo.search_employees([], fields=['id', 'image_1920'])
    print(f"📋 Empleados en Odoo: {len(employees)}")

    conn = get_db_connection()
    cursor = conn.cursor()

    actualizados = 0
    for emp in employees:
        if emp['image_1920']:  # Si tiene foto (no vacío)
            cursor.execute("UPDATE empleados SET foto_enviada = 1 WHERE id_odoo = ?", (emp['id'],))
            if cursor.rowcount > 0:
                actualizados += 1
                print(f"   ✅ Empleado ID {emp['id']} marcado con foto_enviada=1")
    conn.commit()
    conn.close()

    print(f"\n✅ Proceso completado. {actualizados} empleados actualizados.")

if __name__ == "__main__":
    main()