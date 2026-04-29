#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_foto.py - Prueba para obtener la foto de perfil de un empleado desde Horus TL1.

Objetivo:
    Explorar si el dispositivo expone las fotografías de los usuarios a través de
    comandos de pyzk o mediante peticiones HTTP. Guarda la imagen localmente si se encuentra.

Uso:
    python tests/test_foto.py --ip <IP_HORUS> --pin <PIN> [--output <carpeta>]
"""

import sys
import os
import argparse
import requests
import base64
from pathlib import Path

# Ajustar path para importar módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.horus_client import HorusTL1Client
from src.database import obtener_empleado_por_pin, init_db

# ----------------------------------------------------------------------
# Configuración por defecto (puedes cambiarlas aquí)
# ----------------------------------------------------------------------
DEFAULT_IP = "192.168.1.105"
DEFAULT_PORT = 4370
DEFAULT_PASSWORD = "0"
DEFAULT_OUTPUT = "fotos_prueba"

# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------
def save_image(data, filename, output_dir):
    """Guarda datos binarios en un archivo dentro del directorio de salida."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(data)
    print(f"✅ Imagen guardada: {filepath}")
    return filepath

def try_http_endpoints(ip, pin, output_dir):
    """
    Intenta obtener la foto mediante peticiones HTTP a posibles endpoints.
    Retorna True si se encontró y guardó alguna imagen.
    """
    endpoints = [
        f"/photo?pin={pin}",
        f"/image?user={pin}",
        f"/cgi-bin/photo.cgi?user={pin}",
        f"/cgi-bin/image.cgi?id={pin}",
        f"/iclock/photo.aspx?pin={pin}",
        f"/iclock/image.aspx?pin={pin}",
        f"/upload/photo/{pin}.jpg",
        f"/picture/{pin}.jpg",
    ]
    base_url = f"http://{ip}"
    
    for endpoint in endpoints:
        url = base_url + endpoint
        print(f"   Probando URL: {url}")
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                # Verificar si el contenido parece una imagen (JPEG o PNG)
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type or response.content[:2] in (b'\xff\xd8', b'\x89PNG'):
                    filename = f"foto_pin_{pin}_http.jpg"
                    save_image(response.content, filename, output_dir)
                    print(f"   ✅ Imagen obtenida desde {url}")
                    return True
                else:
                    print(f"   ⚠️  Respuesta 200 pero no es imagen (Content-Type: {content_type})")
            else:
                print(f"   ❌ Código {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ No se pudo conectar a {url}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    return False

def try_pyzk_commands(horus_client, uid, pin, output_dir):
    """
    Intenta usar comandos de pyzk no documentados o experimentales.
    """
    # pyzk no tiene métodos documentados para fotos, pero podemos intentar
    # acceder a atributos internos o comandos raw.
    if not horus_client.conn:
        print("   ⚠️  No hay conexión activa")
        return False

    # Intentar obtener por algún método de la conexión
    # (esto es especulativo, basado en la estructura de pyzk)
    try:
        # Algunos dispositivos tienen un método 'get_user_photo' no estándar
        if hasattr(horus_client.conn, 'get_user_photo'):
            photo_data = horus_client.conn.get_user_photo(uid)
            if photo_data:
                filename = f"foto_uid_{uid}_pyzk.jpg"
                save_image(photo_data, filename, output_dir)
                print(f"   ✅ Imagen obtenida vía get_user_photo")
                return True
    except Exception as e:
        print(f"   ⚠️  get_user_photo falló: {e}")

    # Intentar enviar un comando en crudo (poco probable que funcione)
    try:
        # Comando hipotético para obtener foto (basado en SDK de ZKTeco)
        # Esto es un intento, no esperes que funcione.
        cmd = f"GET PHOTO {uid}\r\n"
        horus_client.conn.send_command(cmd)
        response = horus_client.conn.receive_data()
        if response:
            filename = f"foto_uid_{uid}_raw.bin"
            save_image(response, filename, output_dir)
            print(f"   ✅ Datos recibidos por comando raw (puede no ser imagen)")
            return True
    except Exception as e:
        print(f"   ⚠️  Comando raw falló: {e}")

    return False

# ----------------------------------------------------------------------
# Función principal
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Obtener foto de perfil desde Horus TL1")
    parser.add_argument('--ip', default=DEFAULT_IP, help=f"IP del dispositivo (default: {DEFAULT_IP})")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f"Puerto TCP (default: {DEFAULT_PORT})")
    parser.add_argument('--password', default=DEFAULT_PASSWORD, help=f"Contraseña del dispositivo (default: {DEFAULT_PASSWORD})")
    parser.add_argument('--pin', required=True, help="PIN (user_id) del empleado en el dispositivo")
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help=f"Carpeta de salida (default: {DEFAULT_OUTPUT})")
    parser.add_argument('--http-only', action='store_true', help="Solo probar métodos HTTP (no pyzk)")
    parser.add_argument('--pyzk-only', action='store_true', help="Solo probar métodos pyzk")
    args = parser.parse_args()

    output_dir = args.output
    pin = args.pin

    print(f"\n📸 Iniciando prueba para obtener foto del PIN {pin} en {args.ip}\n")

    # Inicializar BD local (por si se necesita mapeo)
    init_db()

    # Verificar si el PIN existe en la base de datos local (opcional, solo informativo)
    empleado = obtener_empleado_por_pin(pin)
    if empleado:
        print(f"   ℹ️  PIN {pin} encontrado en BD local: {empleado['nombre']} (ID Odoo {empleado['id_odoo']})")
        uid = empleado.get('uid_horus')
    else:
        print(f"   ℹ️  PIN {pin} NO está en BD local. Intentaremos obtener uid desde el dispositivo.")
        uid = None

    # Conectar al dispositivo para obtener información adicional
    horus = HorusTL1Client(args.ip, port=args.port, password=args.password)
    if not horus.connect():
        print("❌ No se pudo conectar al dispositivo. Abortando.")
        return

    # Obtener lista de usuarios para verificar el PIN y obtener su UID
    users = horus.get_users()
    user_info = None
    for u in users:
        if u['user_id'] == pin:
            user_info = u
            break

    if not user_info:
        print(f"❌ PIN {pin} no encontrado en el dispositivo.")
        horus.disconnect()
        return

    print(f"   ✅ Usuario encontrado en dispositivo: UID={user_info['uid']}, nombre={user_info['name']}")
    uid = user_info['uid']

    # --- Intentar obtener la foto ---
    encontrada = False

    if not args.pyzk_only:
        print("\n🌐 Probando métodos HTTP...")
        if try_http_endpoints(args.ip, pin, output_dir):
            encontrada = True

    if not args.http_only and not encontrada:
        print("\n🐍 Probando métodos pyzk (experimentales)...")
        if try_pyzk_commands(horus, uid, pin, output_dir):
            encontrada = True

    if encontrada:
        print(f"\n✅ Foto obtenida y guardada en '{output_dir}'")
    else:
        print("\n❌ No se pudo obtener la foto por ningún método.")

    horus.disconnect()

if __name__ == "__main__":
    main()