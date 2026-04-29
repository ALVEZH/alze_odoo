# tests/test_odoo_local.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.odoo_client import OdooClient
import datetime

# Configuración para Odoo local
ODOO_URL = "http://localhost:8069"
ODOO_DB = "middleware_pruebas"
ODOO_USER = "admin"
ODOO_PASS = "admin"

client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)

if client.connect():
    # Listar empleados
    emps = client.search_employees([('active', '=', True)], fields=['id', 'name'])
    print(f"\n📋 Empleados activos en Odoo: {len(emps)}")
    for emp in emps[:5]:
        print(f"   - ID: {emp['id']} | {emp['name']}")

    # Crear empleado de prueba
    new_id = client.create_employee({'name': 'Middleware Test'})
    print(f"\n✅ Empleado creado con ID: {new_id}")

    # Actualizar
    client.write_employee(new_id, {'name': 'Middleware Test Actualizado'})
    print(f"✅ Empleado {new_id} actualizado")

    # Registrar asistencia
    now = datetime.datetime.now()
    att_id = client.create_attendance(new_id, now)
    print(f"✅ Asistencia registrada con ID: {att_id}")
else:
    print("❌ No se pudo conectar a Odoo")