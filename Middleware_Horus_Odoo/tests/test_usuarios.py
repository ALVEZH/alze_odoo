# tests/test_usuarios.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.horus_client import HorusTL1Client

IP = "192.168.1.105"
PORT = 4370
PASS = "0"

client = HorusTL1Client(IP, port=PORT, password=PASS)
if not client.connect():
    sys.exit(1)

# 1. Intentar crear usuario que NO existe
uid = 9999
success, msg = client.create_user(uid, "PRUEBA UPDATE")
print(msg)

# 2. Intentar crear el MISMO usuario otra vez (debe fallar)
success, msg = client.create_user(uid, "INTENTO DUPLICADO")
print(msg)

# 3. Actualizar el usuario (cambiar nombre)
success, msg = client.update_user(uid, new_name="NOMBRE ACTUALIZADO")
print(msg)

# 4. Verificar que el nombre cambió
users = client.get_users()
for u in users:
    if u['uid'] == uid:
        print(f"Nombre en dispositivo: {u['name']}")

# 5. Eliminar usuario (opcional, comentado para no perderlo)
#success, msg = client.delete_user(uid)
#print(msg)

client.disconnect()