#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para forzar el envío de fotos de todos los empleados desde Horus TL1 al middleware.
Ejecutar UNA SOLA VEZ después de que el middleware esté corriendo.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.horus_client import HorusTL1Client
from src.database import obtener_empleado_por_pin

# Configuración del dispositivo
HORUS_IP = "192.168.1.105"
HORUS_PORT = 4370
HORUS_PASSWORD = "0"
DELAY_ENTRE_USUARIOS = 3  # segundos, para no saturar el dispositivo

def main():
    print("🚀 Iniciando proceso de actualización masiva de perfiles...")
    client = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
    if not client.connect():
        print("❌ No se pudo conectar al dispositivo.")
        return

    try:
        usuarios = client.get_users()
        print(f"📋 Usuarios encontrados: {len(usuarios)}")

        for u in usuarios:
            uid = u['uid']
            nombre = u['name']
            user_id = u['user_id']
            print(f"\n--- Procesando UID {uid} (PIN {user_id}) - {nombre} ---")

            # Obtener datos actuales del usuario (ya los tenemos en 'u')
            # Realizamos una actualización con los mismos datos (para forzar envío de foto)
            success, msg = client.update_user(uid, new_name=nombre)
            if success:
                print(f"   ✅ Perfil actualizado (sin cambios reales). Esperando envío de foto...")
                # El middleware recibirá la foto en breve
                time.sleep(DELAY_ENTRE_USUARIOS)
            else:
                print(f"   ⚠️ Error al actualizar: {msg}")

        print("\n✅ Proceso completado. Las fotos deberían comenzar a llegar al middleware.")
        print("   Revisa los logs del middleware para confirmar la recepción de imágenes.")

    finally:
        client.disconnect()

if __name__ == "__main__":
    main()