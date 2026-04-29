# src/adms_server.py
import sys
import os
import csv
import time
import threading
from datetime import datetime
from io import StringIO
from flask import Flask, request, Response, jsonify, current_app
import pytz
import hashlib
import base64


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import (
    init_db, optimizar_indices, registrar_log,
    obtener_empleado_por_pin, guardar_asistencia,
    guardar_empleado, eliminar_empleado, get_db_connection,
    guardar_mapeo, obtener_pin_por_id_odoo, obtener_id_odoo_por_pin,
    obtener_empleado_por_id_odoo, marcar_asistencia_enviada,
    obtener_asistencias_pendientes
)
from src.horus_client import HorusTL1Client
from src.odoo_client import OdooClient
from src import config_manager

app = Flask(__name__)

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------
# Cargar configuración
config = config_manager.load_config()
horus_cfg = config['horus']
odoo_cfg = config['odoo']
sync_cfg = config['sync']

# Asignar a variables globales
HORUS_IP = horus_cfg['ip']
HORUS_PORT = horus_cfg['port']
HORUS_PASSWORD = horus_cfg['password']
ODOO_URL = odoo_cfg['url']
ODOO_DB = odoo_cfg['db']
ODOO_USER = odoo_cfg['username']
ODOO_PASS = odoo_cfg['password']
SYNC_INTERVAL = sync_cfg.get('horus_to_bd_interval', 10)
HORUS_TO_ODOO_INTERVAL = sync_cfg.get('horus_to_odoo_interval', 60)
ODOO_TO_HORUS_INTERVAL = sync_cfg.get('odoo_to_horus_interval', 10)
ODOO_SYNC_INTERVAL = sync_cfg.get('attendance_sync_interval', 10)

# Zona horaria del dispositivo (ajústala según tu ubicación)
LOCAL_TIMEZONE = pytz.timezone('America/Mexico_City')

# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES PARA FOTOS
# ----------------------------------------------------------------------
def hash_base64_image(b64_str):
    """Calcula el hash SHA256 de una imagen codificada en base64."""
    if not b64_str:
        return None
    try:
        img_data = base64.b64decode(b64_str)
        return hashlib.sha256(img_data).hexdigest()
    except:
        return None

# ----------------------------------------------------------------------
# HILO 1: Sincronización Horus → BD (usuarios desde dispositivo)
# ----------------------------------------------------------------------
# Este hilo se encarga de sincronizar los usuarios activos en el dispositivo Horus hacia la base de datos local,
# creando o actualizando registros de empleados según corresponda, y marcando como inactivos aquellos que ya no están en el dispositivo.
class UserSyncThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.name = "UserSync"

    def run(self):
        with app.app_context():
            registrar_log('INFO', self.name, "Hilo de sincronización Horus→BD iniciado")
            print("🔄 Hilo de sincronización de usuarios (Horus→BD) iniciado")
            while self.running:
                try:
                    self.sync_users()
                except Exception as e:
                    registrar_log('ERROR', self.name, f"Error en sincronización: {e}")
                time.sleep(SYNC_INTERVAL)

    def sync_users(self):
        print("\n📋 Sincronizando usuarios desde dispositivo...")
        client = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
        if not client.connect():
            registrar_log('WARNING', self.name, "No se pudo conectar al dispositivo")
            return

        try:
            device_users = client.get_users()
            print(f"   🔍 Usuarios en dispositivo: {len(device_users)}")

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT pin_horus FROM empleados WHERE activo = 1")
            db_active_pins = {row[0] for row in cursor.fetchall()}
            conn.close()

            device_pins = set()
            for u in device_users:
                user_id = u['user_id']
                uid = u['uid']
                nombre = u['name']

                # Obtener id_odoo actual si existe
                empleado_existente = obtener_empleado_por_pin(user_id)
                if empleado_existente:
                    id_odoo = empleado_existente['id_odoo']
                    print(f"   🔍 Usuario {user_id} ya tenía id_odoo={id_odoo}, se mantiene")
                    # Conservar foto_enviada y hash existentes
                    guardar_empleado(id_odoo, user_id, nombre, uid_horus=uid)
                else:
                    id_odoo = uid  # temporal
                    print(f"   🔍 Usuario {user_id} nuevo, id_odoo temporal={uid}")
                    guardar_empleado(id_odoo, user_id, nombre, uid_horus=uid)

                guardar_mapeo(id_odoo, user_id, uid)
                device_pins.add(user_id)

            # Usuarios que ya no están en dispositivo
            inactive_pins = db_active_pins - device_pins
            for pin in inactive_pins:
                eliminar_empleado(pin)
                print(f"   🗑️ Usuario {pin} marcado como inactivo (ya no está en dispositivo)")

            registrar_log('INFO', self.name, f"Sincronización completada. Activos: {len(device_pins)}, Inactivados: {len(inactive_pins)}")
            print(f"   ✅ Sincronización completada. Activos: {len(device_pins)}, Inactivados: {len(inactive_pins)}")
        except Exception as e:
            registrar_log('ERROR', self.name, f"Error durante sincronización: {e}")
            print(f"   ❌ Error: {e}")
        finally:
            client.disconnect(silent=True)

# ----------------------------------------------------------------------
# HILO 2: Crear en Odoo usuarios de Horus que no tienen mapeo
# ----------------------------------------------------------------------
# Este hilo se encarga de revisar periódicamente los usuarios activos en Horus que no tienen un mapeo con Odoo,
# y crear los empleados correspondientes en Odoo, actualizando el mapeo y la BD local.
class HorusToOdooSyncThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.name = "HorusToOdoo"
    
    def run(self):
        with app.app_context():
            registrar_log('INFO', self.name, "Hilo de creación en Odoo (Horus→Odoo) iniciado")
            print("🔄 Hilo de creación de empleados en Odoo (Horus→Odoo) iniciado")
            while self.running:
                try:
                    self.sync_horus_to_odoo()
                except Exception as e:
                    registrar_log('ERROR', self.name, f"Error en sync Horus→Odoo: {e}")
                time.sleep(HORUS_TO_ODOO_INTERVAL)

    def sync_horus_to_odoo(self):
        print("\n📋 Creando en Odoo usuarios de Horus sin mapeo...")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id_odoo, e.pin_horus, e.nombre
            FROM empleados e
            LEFT JOIN mapeo_pins m ON e.pin_horus = m.pin_horus
            WHERE e.activo = 1 AND m.id_odoo IS NULL
        """)
        sin_mapeo = cursor.fetchall()
        conn.close()

        if not sin_mapeo:
            return

        odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
        if not odoo.connect():
            registrar_log('WARNING', self.name, "No se pudo conectar a Odoo")
            return

        creados = 0
        for (id_odoo, pin_horus, nombre) in sin_mapeo:
            try:
                new_id = odoo.create_employee({'name': nombre})
                print(f"   ➕ Empleado {nombre} creado en Odoo con ID {new_id} (PIN {pin_horus})")
                guardar_mapeo(new_id, pin_horus, id_odoo)
                guardar_empleado(new_id, pin_horus, nombre, uid_horus=id_odoo)
                creados += 1
            except Exception as e:
                registrar_log('ERROR', self.name, f"Error creando empleado {nombre}: {e}")

        registrar_log('INFO', self.name, f"Usuarios creados en Odoo: {creados}")
        print(f"   ✅ {creados} usuarios creados en Odoo")

# ----------------------------------------------------------------------
# HILO 3: Sincronización Odoo → Horus (empleados y verificación de fotos)
# ----------------------------------------------------------------------
# Este hilo se encarga de sincronizar los empleados activos de Odoo hacia Horus,
# creando o actualizando usuarios en el dispositivo según corresponda, y eliminando
# aquellos que ya no están activos en Odoo. Además, verifica cambios en las fotos de Odoo
# para actualizar la foto en el dispositivo si es necesario.
class OdooToHorusSyncThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.name = "OdooToHorus"

    def run(self):
        with app.app_context():
            registrar_log('INFO', self.name, "Hilo de sincronización Odoo→Horus iniciado")
            print("🔄 Hilo de sincronización de empleados (Odoo→Horus) iniciado")
            while self.running:
                try:
                    self.sync_odoo_to_horus()
                except Exception as e:
                    registrar_log('ERROR', self.name, f"Error en sincronización Odoo→Horus: {e}")
                time.sleep(ODOO_TO_HORUS_INTERVAL)

    def sync_odoo_to_horus(self):
        print("\n📋 Sincronizando empleados desde Odoo...")
        odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
        if not odoo.connect():
            registrar_log('WARNING', self.name, "No se pudo conectar a Odoo")
            return

        try:
            # Obtener empleados activos de Odoo con sus fotos
            odoo_employees = odoo.search_employees([('active', '=', True)], fields=['id', 'name', 'image_1920'])
            print(f"   🔍 Empleados activos en Odoo: {len(odoo_employees)}")
            odoo_ids = {emp['id'] for emp in odoo_employees}

            # Conectar a Horus
            horus = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
            if not horus.connect():
                registrar_log('WARNING', self.name, "No se pudo conectar a Horus")
                return

            device_users = horus.get_users()
            existing_uids = {u['uid'] for u in device_users}
            existing_user_ids = {u['user_id'] for u in device_users}

            # Crear/actualizar empleados desde Odoo
            creados = 0
            actualizados = 0
            for emp in odoo_employees:
                odoo_id = emp['id']
                nombre = emp['name']
                b64_image = emp.get('image_1920')
                pin_mapeado = obtener_pin_por_id_odoo(odoo_id)

                if pin_mapeado:
                    if pin_mapeado in existing_user_ids:
                        for u in device_users:
                            if u['user_id'] == pin_mapeado:
                                if u['name'] != nombre:
                                    success, msg = horus.update_user(u['uid'], new_name=nombre)
                                    if success:
                                        actualizados += 1
                                        print(f"   ✏️ Usuario {pin_mapeado} actualizado en dispositivo")
                                        guardar_empleado(odoo_id, pin_mapeado, nombre, uid_horus=u['uid'])
                                break
                    else:
                        uid = horus.get_next_available_uid()
                        success, msg = horus.create_user(uid, nombre, user_id=pin_mapeado)
                        if success:
                            creados += 1
                            print(f"   ➕ Usuario {pin_mapeado} creado en dispositivo (UID {uid})")
                            guardar_empleado(odoo_id, pin_mapeado, nombre, uid_horus=uid)
                else:
                    if str(odoo_id).isdigit() and str(odoo_id) not in existing_user_ids:
                        uid = odoo_id if odoo_id not in existing_uids else horus.get_next_available_uid(start_from=odoo_id+1)
                        success, msg = horus.create_user(uid, nombre, user_id=str(odoo_id))
                        if success:
                            creados += 1
                            print(f"   ➕ Usuario {odoo_id} creado en dispositivo con UID {uid}")
                            guardar_empleado(odoo_id, str(odoo_id), nombre, uid_horus=uid)
                            guardar_mapeo(odoo_id, str(odoo_id), uid)
                    else:
                        nuevo_pin = None
                        for candidate in range(1000, 10000):
                            if str(candidate) not in existing_user_ids and candidate not in existing_uids:
                                nuevo_pin = str(candidate)
                                break
                        if nuevo_pin:
                            uid = horus.get_next_available_uid(start_from=int(nuevo_pin))
                            success, msg = horus.create_user(uid, nombre, user_id=nuevo_pin)
                            if success:
                                creados += 1
                                print(f"   ➕ Usuario creado con PIN {nuevo_pin} (UID {uid}) para Odoo ID {odoo_id}")
                                guardar_empleado(odoo_id, nuevo_pin, nombre, uid_horus=uid)
                                guardar_mapeo(odoo_id, nuevo_pin, uid)
                        else:
                            print(f"   ❌ No se pudo encontrar un PIN libre para Odoo ID {odoo_id}")

            # Eliminar usuarios que ya no están en Odoo
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id_odoo, pin_horus, uid_horus FROM empleados WHERE activo = 1")
            local_empleados = cursor.fetchall()
            conn.close()

            eliminados = 0
            for (local_id, local_pin, local_uid) in local_empleados:
                if local_id not in odoo_ids:
                    if local_uid:
                        success, msg = horus.delete_user(local_uid)
                        if success:
                            eliminados += 1
                            eliminar_empleado(local_pin)
                            print(f"   🗑️ Usuario {local_pin} (ID Odoo {local_id}) eliminado del dispositivo")
                        else:
                            print(f"   ⚠️ No se pudo eliminar usuario {local_pin}: {msg}")
                    else:
                        eliminar_empleado(local_pin)
                        print(f"   ⚠️ Usuario {local_pin} marcado inactivo en BD (sin uid_horus)")

            registrar_log('INFO', self.name, f"Sincronización Odoo→Horus: {creados} creados, {actualizados} actualizados, {eliminados} eliminados")
            print(f"   ✅ Sincronización Odoo→Horus completada: {creados} creados, {actualizados} actualizados, {eliminados} eliminados")

            # --- Verificación de cambios en fotos de Odoo ---
            print("   📸 Verificando cambios en fotos de Odoo...")
            for emp in odoo_employees:
                odoo_id = emp['id']
                b64_image = emp.get('image_1920')
                empleado_local = obtener_empleado_por_id_odoo(odoo_id)
                if not empleado_local:
                    continue
                pin = empleado_local['pin_horus']
                foto_enviada = empleado_local.get('foto_enviada', 0)
                if foto_enviada == 1:
                    hash_local = empleado_local.get('ultima_foto_hash')
                    if b64_image:
                        hash_actual = hash_base64_image(b64_image)
                        if hash_actual and hash_actual != hash_local:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE empleados SET foto_enviada = 0, ultima_foto_hash = ? WHERE pin_horus = ?", (hash_actual, pin))
                            conn.commit()
                            conn.close()
                            print(f"   📸 Foto de empleado {odoo_id} cambió. Flag foto_enviada reseteado.")
                    else:
                        # Foto eliminada en Odoo
                        if hash_local is not None:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE empleados SET foto_enviada = 0, ultima_foto_hash = NULL WHERE pin_horus = ?", (pin,))
                            conn.commit()
                            conn.close()
                            print(f"   📸 Foto de empleado {odoo_id} eliminada. Flag foto_enviada reseteado.")

        except Exception as e:
            registrar_log('ERROR', self.name, f"Error durante sincronización Odoo→Horus: {e}")
            print(f"   ❌ Error: {e}")
        finally:
            horus.disconnect(silent=True)

# ----------------------------------------------------------------------
# HILO 4: Envío de asistencias a Odoo
# ----------------------------------------------------------------------
# Este hilo se encarga de enviar las asistencias pendientes a Odoo,
# creando registros de asistencia vinculados al empleado correcto.
class OdooSyncThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.name = "OdooSync"

    def run(self):
        with app.app_context():
            registrar_log('INFO', self.name, "Hilo de envío de asistencias a Odoo iniciado")
            print("🔄 Hilo de envío de asistencias a Odoo iniciado")
            while self.running:
                try:
                    self.sync_attendances()
                except Exception as e:
                    registrar_log('ERROR', self.name, f"Error en sync Odoo: {e}")
                time.sleep(ODOO_SYNC_INTERVAL)

    def sync_attendances(self):
        pendientes = obtener_asistencias_pendientes(limite=100)
        if not pendientes:
            return

        print(f"📤 Enviando {len(pendientes)} asistencias a Odoo...")
        odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
        if not odoo.connect():
            registrar_log('ERROR', self.name, "No se pudo conectar a Odoo")
            return

        enviadas = 0
        for att in pendientes:
            print(f"\n   Procesando asistencia ID {att['id']} - PIN {att['pin_horus']} - Fecha {att['fecha_hora']}")
            try:
                # Convertir la fecha de string a datetime
                if isinstance(att['fecha_hora'], str):
                    local_dt = datetime.strptime(att['fecha_hora'], '%Y-%m-%d %H:%M:%S')
                else:
                    local_dt = att['fecha_hora']

                # Obtener ID de Odoo del empleado
                id_odoo = obtener_id_odoo_por_pin(att['pin_horus'])
                if not id_odoo:
                    empleado = obtener_empleado_por_pin(att['pin_horus'])
                    if empleado:
                        try:
                            new_id = odoo.create_employee({'name': empleado['nombre']})
                            guardar_mapeo(new_id, att['pin_horus'], empleado['uid_horus'])
                            guardar_empleado(new_id, att['pin_horus'], empleado['nombre'], uid_horus=empleado['uid_horus'])
                            id_odoo = new_id
                            print(f"   ➕ Empleado creado en Odoo con ID {id_odoo}")
                        except Exception as e2:
                            registrar_log('ERROR', self.name, f"Error creando empleado: {e2}")
                            continue
                    else:
                        registrar_log('WARNING', self.name, f"No se encontró empleado para PIN {att['pin_horus']}")
                        continue

                # Convertir hora local a UTC
                if local_dt.tzinfo is None:
                    local_dt = LOCAL_TIMEZONE.localize(local_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                fecha_hora_utc = utc_dt.replace(tzinfo=None)
                fecha_hora_str = fecha_hora_utc.strftime('%Y-%m-%d %H:%M:%S')
                print(f"      Fecha UTC enviada: {fecha_hora_str}")

                odoo_att_id = odoo.create_attendance(id_odoo, fecha_hora_str)
                marcar_asistencia_enviada(att['id'], odoo_att_id)
                enviadas += 1
                print(f"      ✅ Asistencia {att['id']} enviada - ID Odoo: {odoo_att_id}")
            except Exception as e:
                registrar_log('ERROR', self.name, f"Error: {e}")
                print(f"      ❌ Error: {e}")
                import traceback
                traceback.print_exc()

        registrar_log('INFO', self.name, f"Asistencias enviadas a Odoo: {enviadas}/{len(pendientes)}")
        print(f"\n   ✅ {enviadas}/{len(pendientes)} asistencias enviadas")

# ----------------------------------------------------------------------
# HILO 5: Sincronización horaria del dispositivo (cada hora)
# ----------------------------------------------------------------------
class TimeSyncThread(threading.Thread):
    def __init__(self, interval=3600):
        super().__init__()
        self.daemon = True
        self.running = True
        self.interval = interval
        self.name = "TimeSync"

    def run(self):
        with app.app_context():
            registrar_log('INFO', self.name, "Hilo de sincronización horaria iniciado")
            print("🔄 Hilo de sincronización horaria iniciado (cada 1 hora)")
            while self.running:
                try:
                    self.sync_device_time()
                except Exception as e:
                    registrar_log('ERROR', self.name, f"Error en sync horaria: {e}")
                time.sleep(self.interval)

    def sync_device_time(self):
        from src.horus_client import HorusTL1Client
        client = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
        if not client.connect():
            registrar_log('WARNING', self.name, "No se pudo conectar a Horus para sincronizar hora")
            return
        try:
            now = datetime.now()
            client.sync_time(now)
        finally:
            client.disconnect(silent=True)

# ----------------------------------------------------------------------
# ENDPOINTS ADMS DE HORUS TL1
# ----------------------------------------------------------------------
# Endpoint para recibir datos de asistencias (ATTLOG)
@app.route('/iclock/cdata', methods=['GET', 'POST'])
def iclock_cdata():
    sn = request.args.get('SN', '')
    table = request.args.get('table', '')

    if request.method == 'GET':
        print(f"📡 Handshake desde {sn}")
        return Response("OK", mimetype='text/plain')

    if request.method == 'POST':
        data_str = request.get_data(as_text=True)

        if table.upper() == 'ATTLOG':
            print(f"\n📨 Recibidas asistencias de {sn}")
            try:
                csv_data = StringIO(data_str)
                reader = csv.reader(csv_data, delimiter='\t')
                guardadas = 0
                for row in reader:
                    if len(row) >= 2:
                        pin = row[0].strip()
                        timestamp_str = row[1].strip()
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
                            except ValueError:
                                print(f"   ⚠️ Fecha inválida: {timestamp_str}")
                                continue
                        success, _ = guardar_asistencia(pin, timestamp)
                        if success:
                            guardadas += 1
                print(f"   ✅ {guardadas} asistencias guardadas en este lote")
                return Response(f"OK:{guardadas}", mimetype='text/plain')
            except Exception as e:
                print(f"❌ Error procesando ATTLOG: {e}")
                return Response("ERROR", mimetype='text/plain')

        return Response("OK", mimetype='text/plain')

# Endpoint para recibir fotos de empleados
@app.route('/iclock/fdata', methods=['POST'])
def iclock_fdata():
    print("\n📸 POST /iclock/fdata recibido")
    sn = request.args.get('SN', 'desconocido')
    print(f"   SN: {sn}")
    print(f"   Headers: {dict(request.headers)}")
    data = request.get_data()
    print(f"   Tamaño total: {len(data)} bytes")
    print(f"   Primeros 200 bytes: {data[:200]!r}")

    try:
        # Extraer cabecera y datos de imagen
        jpeg_start = data.find(b'\xff\xd8')
        if jpeg_start == -1:
            registrar_log('WARNING', 'ADMS', "No se encontró marca JPEG en /iclock/fdata")
            return Response("OK", mimetype='text/plain')

        header_bytes = data[:jpeg_start]
        image_data = data[jpeg_start:]

        try:
            header = header_bytes.decode('utf-8', errors='ignore')
        except:
            header = header_bytes.decode('latin-1', errors='ignore')

        print(f"   Cabecera extraída:\n{header}")

        # Parsear cabecera para obtener el PIN
        lines = header.split('\n')
        pin = None
        for line in lines:
            if line.startswith('PIN='):
                filename = line[4:].strip()
                if '-' in filename:
                    pin = filename.split('-')[-1].replace('.jpg', '').replace('.jpeg', '')
                else:
                    pin = filename.replace('.jpg', '').replace('.jpeg', '')
                print(f"   PIN extraído: {pin}")
                break

        if not pin:
            registrar_log('WARNING', 'ADMS', "No se pudo extraer PIN de la cabecera")
            return Response("OK", mimetype='text/plain')

        # Verificar que el empleado existe en BD local
        empleado = obtener_empleado_por_pin(pin)
        if not empleado:
            registrar_log('WARNING', 'ADMS', f"Foto recibida para PIN {pin} que no existe en BD")
            return Response("OK", mimetype='text/plain')

        print(f"   Empleado encontrado: ID Odoo {empleado['id_odoo']}, nombre {empleado['nombre']}")

        # Consultar flag foto_enviada
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT foto_enviada FROM empleados WHERE pin_horus = ?", (pin,))
        row = cursor.fetchone()
        foto_enviada = row[0] if row else 0
        conn.close()
        print(f"   Flag foto_enviada actual: {foto_enviada}")

        if foto_enviada:
            print(f"   ℹ️  PIN {pin} ya tiene foto enviada. Se descarta esta nueva imagen.")
            registrar_log('INFO', 'ADMS', f"Foto descartada para PIN {pin} (ya existente)")
            return Response("OK", mimetype='text/plain')

        # Procesar imagen (redimensionar si está PIL disponible)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            image_data = output.getvalue()
            print(f"   Imagen redimensionada a {img.size}")
        except ImportError:
            print("   PIL no instalado, se envía imagen original")
        except Exception as e:
            print(f"   Error al redimensionar: {e}, se envía original")

        # Codificar a base64 para Odoo
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Enviar a Odoo en un hilo separado y marcar como enviada
        def enviar_y_marcar():
            try:
                odoo = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
                if odoo.connect():
                    print(f"   📤 Enviando foto a Odoo para empleado {empleado['id_odoo']}")
                    success = odoo.write_employee(empleado['id_odoo'], {'image_1920': image_base64})
                    print(f"   Resultado write_employee: {success}")
                    if success:
                        # Calcular hash de la imagen enviada
                        hash_obj = hashlib.sha256(image_data)
                        hash_str = hash_obj.hexdigest()

                        conn2 = get_db_connection()
                        cursor2 = conn2.cursor()
                        cursor2.execute("UPDATE empleados SET foto_enviada = 1, ultima_foto_hash = ? WHERE pin_horus = ?", (hash_str, pin))
                        conn2.commit()
                        rows_affected = cursor2.rowcount
                        cursor2.execute("SELECT foto_enviada FROM empleados WHERE pin_horus = ?", (pin,))
                        nuevo_valor = cursor2.fetchone()[0]
                        conn2.close()
                        print(f"   Filas actualizadas: {rows_affected}, nuevo valor foto_enviada: {nuevo_valor}")
                        if rows_affected > 0 and nuevo_valor == 1:
                            registrar_log('INFO', 'ADMS', f"Foto enviada a Odoo para PIN {pin}")
                            print(f"   ✅ Foto enviada y marcada correctamente")
                        else:
                            registrar_log('ERROR', 'ADMS', f"No se pudo actualizar flag para PIN {pin}")
                    else:
                        registrar_log('ERROR', 'ADMS', f"Error al enviar foto a Odoo para PIN {pin}")
                else:
                    registrar_log('ERROR', 'ADMS', "No se pudo conectar a Odoo para enviar foto")
            except Exception as e:
                registrar_log('ERROR', 'ADMS', f"Excepción enviando foto: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=enviar_y_marcar).start()
        return Response("OK", mimetype='text/plain')

    except Exception as e:
        registrar_log('ERROR', 'ADMS', f"Error general en /iclock/fdata: {e}")
        import traceback
        traceback.print_exc()
        return Response("OK", mimetype='text/plain')

# Endpoint para handshake (puede ser usado por el dispositivo para verificar conexión)
@app.route('/iclock/getrequest', methods=['GET'])
def iclock_getrequest():
    """
    Responde a las peticiones de comandos del dispositivo.
    Si el dispositivo solicita información, se le puede enviar la hora actual para sincronizarla.
    """
    # Obtener la hora actual del servidor (debe estar sincronizada)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    response = f"SET TIME {now}\r\n"
    
    print(f"📡 Enviando comando de hora al dispositivo: {response.strip()}")
    return Response(response, mimetype='text/plain')
# ----------------------------------------------------------------------
# API REST
# ----------------------------------------------------------------------
# Función auxiliar para conectar a Horus
def conectar_horus():
    client = HorusTL1Client(HORUS_IP, port=HORUS_PORT, password=HORUS_PASSWORD)
    if client.connect():
        return client
    return None

# Endpoint para crear empleado
@app.route('/api/empleados', methods=['POST'])
def crear_empleado():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON requerido"}), 400
    uid = data.get('uid')
    nombre = data.get('nombre')
    departamento = data.get('departamento', '')
    if not uid or not nombre:
        return jsonify({"error": "uid y nombre son obligatorios"}), 400

    client = conectar_horus()
    if not client:
        return jsonify({"error": "No se pudo conectar al dispositivo"}), 500

    if client.user_exists_by_user_id(str(uid)) or client.user_exists_by_uid(uid):
        return jsonify({"error": f"El ID {uid} ya está ocupado en el dispositivo"}), 409

    if obtener_pin_por_id_odoo(uid):
        return jsonify({"error": f"Ya existe un mapeo para el ID {uid}"}), 409

    if client.user_exists_by_uid(uid):
        nuevo_uid = client.get_next_available_uid(start_from=uid+1)
        success, msg = client.create_user(nuevo_uid, nombre, user_id=str(uid))
        if success:
            guardar_empleado(uid, str(uid), nombre, departamento, uid_horus=nuevo_uid)
            guardar_mapeo(uid, str(uid), nuevo_uid)
            client.disconnect(silent=True)
            registrar_log('INFO', 'API', f"Empleado {uid} creado vía API con UID {nuevo_uid}")
            return jsonify({"success": True, "uid": uid, "nombre": nombre, "pin_asignado": str(uid), "uid_horus": nuevo_uid}), 201
    else:
        success, msg = client.create_user(uid, nombre, user_id=str(uid))
        if success:
            guardar_empleado(uid, str(uid), nombre, departamento, uid_horus=uid)
            guardar_mapeo(uid, str(uid), uid)
            client.disconnect(silent=True)
            registrar_log('INFO', 'API', f"Empleado {uid} creado vía API")
            return jsonify({"success": True, "uid": uid, "nombre": nombre}), 201

    client.disconnect(silent=True)
    return jsonify({"error": msg}), 500

# Endpoint para actualizar empleado
@app.route('/api/empleados/<int:uid>', methods=['PUT'])
def actualizar_empleado(uid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON requerido"}), 400
    nombre = data.get('nombre')
    departamento = data.get('departamento')

    client = conectar_horus()
    if not client:
        return jsonify({"error": "No se pudo conectar al dispositivo"}), 500

    empleado = obtener_empleado_por_id_odoo(uid)
    if not empleado:
        return jsonify({"error": f"No existe empleado con ID {uid} en BD local"}), 404

    uid_horus = empleado['uid_horus']
    if uid_horus is None:
        return jsonify({"error": "El empleado no tiene uid_horus asociado"}), 500

    success, msg = client.update_user(uid_horus, new_name=nombre)
    client.disconnect(silent=True)
    if not success:
        return jsonify({"error": msg}), 500

    if nombre or departamento:
        guardar_empleado(uid, empleado['pin_horus'], nombre, departamento or '', uid_horus=uid_horus)
    registrar_log('INFO', 'API', f"Empleado {uid} actualizado vía API")
    return jsonify({"success": True, "uid": uid})

# Endpoint para eliminar empleado
@app.route('/api/empleados/<int:uid>', methods=['DELETE'])
def eliminar_empleado_api(uid):
    client = conectar_horus()
    if not client:
        return jsonify({"error": "No se pudo conectar al dispositivo"}), 500

    empleado = obtener_empleado_por_id_odoo(uid)
    if not empleado:
        return jsonify({"error": f"No existe empleado con ID {uid} en BD local"}), 404

    uid_horus = empleado['uid_horus']
    if uid_horus is None:
        return jsonify({"error": "El empleado no tiene uid_horus asociado"}), 500

    success, msg = client.delete_user(uid_horus)
    client.disconnect(silent=True)
    if not success:
        return jsonify({"error": msg}), 500

    eliminar_empleado(empleado['pin_horus'])
    registrar_log('INFO', 'API', f"Empleado {uid} eliminado vía API")
    return jsonify({"success": True, "uid": uid})

# Endpoint para resetear el flag de foto enviada
@app.route('/api/empleados/<int:uid>/reset_foto', methods=['POST'])
def reset_foto_empleado(uid):
    empleado = obtener_empleado_por_id_odoo(uid)
    if not empleado:
        return jsonify({"error": "Empleado no encontrado"}), 404

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE empleados SET foto_enviada = 0 WHERE id_odoo = ?", (uid,))
    conn.commit()
    conn.close()
    registrar_log('INFO', 'API', f"Flag foto reseteado para empleado {uid}")
    return jsonify({"success": True, "message": "Flag de foto reseteado. La próxima foto será enviada a Odoo."})

# Endpoint para listar empleados activos
@app.route('/api/empleados', methods=['GET'])
def listar_empleados():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_odoo, pin_horus, nombre, departamento, activo, uid_horus, foto_enviada FROM empleados WHERE activo = 1")
    rows = cursor.fetchall()
    conn.close()
    empleados = [{
        "uid": r[0],
        "pin": r[1],
        "nombre": r[2],
        "departamento": r[3],
        "activo": bool(r[4]),
        "uid_horus": r[5],
        "foto_enviada": r[6]
    } for r in rows]
    return jsonify(empleados)

@app.route('/')
def index():
    return 'Middleware Horus TL1 + Odoo - Sincronización bidireccional automática'

# Endpoint para reinicio controlado
SHUTDOWN_TOKEN = "deactivate"  # Debe coincidir con el de config_server.py

@app.route('/shutdown', methods=['POST'])
def shutdown():
    token = request.args.get('token')
    if token != SHUTDOWN_TOKEN:
        registrar_log('WARNING', 'ADMS', f"Intento de apagado con token inválido: {token}")
        return jsonify({"error": "Token inválido"}), 403

    registrar_log('INFO', 'ADMS', "Recibida solicitud de apagado. Deteniendo servidor...")
    print("🔴 Apagando servidor por solicitud...")

    # Enviar respuesta inmediatamente
    response = jsonify({"success": True, "message": "Servidor apagado correctamente"})
    
    # En un hilo separado, esperar un segundo y forzar la salida del proceso
    def shutdown_after_delay():
        time.sleep(1)  # Dar tiempo a que la respuesta se envíe
        registrar_log('INFO', 'ADMS', "Saliendo del proceso...")
        os._exit(0)  # Termina el proceso inmediatamente

    threading.Thread(target=shutdown_after_delay, daemon=True).start()
    return response
# ----------------------------------------------------------------------
# INICIO DEL SERVIDOR
# ----------------------------------------------------------------------
if __name__ == '__main__':
    print("🚀 Iniciando middleware completo...")
    if not init_db():
        print("❌ No se pudo inicializar la base de datos. Saliendo.")
        sys.exit(1)
    optimizar_indices()
    print("✅ Base de datos OK")

    # Hilo 1: Horus → BD
    user_sync_thread = UserSyncThread()
    user_sync_thread.start()

    # Hilo 2: Horus → Odoo (crear empleados en Odoo)
    horus_to_odoo_thread = HorusToOdooSyncThread()
    horus_to_odoo_thread.start()

    # Hilo 3: Odoo → Horus (incluye verificación de fotos)
    odoo_to_horus_thread = OdooToHorusSyncThread()
    odoo_to_horus_thread.start()

    # Hilo 4: Asistencias → Odoo
    odoo_sync_thread = OdooSyncThread()
    odoo_sync_thread.start()

    # Hilo 5: Sincronización horaria
    time_sync_thread = TimeSyncThread(interval=3600)  # cada hora
    time_sync_thread.start()

    print("🌍 Servidor ADMS corriendo en http://0.0.0.0:8000")
    print(f"   ⏱️  Sincronización Horus→BD: cada {SYNC_INTERVAL} seg")
    print(f"   ⏱️  Creación en Odoo (Horus→Odoo): cada {HORUS_TO_ODOO_INTERVAL} seg")
    print(f"   ⏱️  Sincronización Odoo→Horus: cada {ODOO_TO_HORUS_INTERVAL} seg")
    print(f"   ⏱️  Envío a Odoo: cada {ODOO_SYNC_INTERVAL} seg")

    try:
        app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
    except KeyboardInterrupt:
        registrar_log('INFO', 'ADMS', 'Servidor detenido por usuario')
        print("\n⏹️ Servidor ADMS detenido.")