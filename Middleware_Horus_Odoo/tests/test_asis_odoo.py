import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.odoo_client import OdooClient
from datetime import datetime

odoo = OdooClient("http://localhost:8069", "middleware_pruebas", "pinzonelias501@gmail.com", "admin")
if odoo.connect():
    now = datetime.now()
    try:
        att_id = odoo.create_attendance(26, now)  # Usa un ID que exista en Odoo
        print(f"✅ Asistencia creada con ID: {att_id}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ No se pudo conectar a Odoo")