# src/database.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'middleware.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def _add_column_if_not_exists(table, column, coldef):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column not in existing:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")
            print(f"✅ Columna '{column}' agregada a tabla '{table}'")
        except Exception as e:
            print(f"⚠️ No se pudo agregar columna '{column}' a '{table}': {e}")
    conn.commit()
    conn.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id_odoo INTEGER PRIMARY KEY,
            pin_horus TEXT UNIQUE,
            nombre TEXT,
            departamento TEXT,
            activo BOOLEAN DEFAULT 1,
            ultima_sincronizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    _add_column_if_not_exists('empleados', 'uid_horus', 'uid_horus INTEGER')
    _add_column_if_not_exists('empleados', 'foto_enviada', 'foto_enviada INTEGER DEFAULT 0')
    _add_column_if_not_exists('empleados', 'ultima_foto_hash', 'ultima_foto_hash TEXT')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin_horus TEXT,
            fecha_hora TIMESTAMP,
            tipo TEXT DEFAULT 'facial',
            enviado_odoo BOOLEAN DEFAULT 0,
            FOREIGN KEY(pin_horus) REFERENCES empleados(pin_horus)
        )
    ''')
    conn.commit()
    conn.close()
    _add_column_if_not_exists('asistencias', 'odoo_attendance_id', 'odoo_attendance_id INTEGER')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nivel TEXT,
            modulo TEXT,
            mensaje TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mapeo_pins (
            id_odoo INTEGER PRIMARY KEY,
            pin_horus TEXT UNIQUE,
            uid_horus INTEGER,
            FOREIGN KEY (id_odoo) REFERENCES empleados(id_odoo),
            FOREIGN KEY (pin_horus) REFERENCES empleados(pin_horus)
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada/migrada en", DB_PATH)
    return True

def optimizar_indices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_empleados_pin ON empleados(pin_horus)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_empleados_activo ON empleados(activo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asistencias_pin_fecha ON asistencias(pin_horus, fecha_hora)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asistencias_enviado ON asistencias(enviado_odoo)")
    cursor.execute("PRAGMA table_info(asistencias)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'odoo_attendance_id' in cols:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asistencias_odoo_id ON asistencias(odoo_attendance_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asistencias_unica ON asistencias(pin_horus, fecha_hora)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_odoo ON mapeo_pins(id_odoo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_pin ON mapeo_pins(pin_horus)")
    conn.commit()
    conn.close()
    print("✅ Índices optimizados")

# ----------------------------------------------------------------------
# FUNCIONES PARA EMPLEADOS
# ----------------------------------------------------------------------
def guardar_empleado(id_odoo, pin_horus, nombre, departamento='', uid_horus=None, foto_enviada=0, ultimo_hash=None):
    """
    Inserta o actualiza un empleado en la BD local.
    - Si ya existe: actualiza nombre, departamento, uid_horus y activo=1.
      Conserva id_odoo y foto_enviada a menos que se especifique un nuevo hash.
    - Si no existe: inserta nuevo con los valores dados.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_odoo, foto_enviada, ultima_foto_hash FROM empleados WHERE pin_horus = ?", (pin_horus,))
        row = cursor.fetchone()
        if row:
            # Actualizar campos básicos
            cursor.execute('''
                UPDATE empleados
                SET nombre = ?, departamento = ?, uid_horus = ?, activo = 1, ultima_sincronizacion = CURRENT_TIMESTAMP
                WHERE pin_horus = ?
            ''', (nombre, departamento, uid_horus, pin_horus))
            # Actualizar hash si se proporciona
            if ultimo_hash is not None:
                cursor.execute("UPDATE empleados SET ultima_foto_hash = ? WHERE pin_horus = ?", (ultimo_hash, pin_horus))
            print(f"✅ Empleado {nombre} actualizado en BD (PIN {pin_horus})")
        else:
            # Nuevo empleado
            cursor.execute('''
                INSERT INTO empleados (id_odoo, pin_horus, uid_horus, nombre, departamento, activo, foto_enviada, ultima_foto_hash, ultima_sincronizacion)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
            ''', (id_odoo, pin_horus, uid_horus, nombre, departamento, foto_enviada, ultimo_hash))
            print(f"✅ Empleado {nombre} guardado en BD (PIN {pin_horus})")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error guardando empleado {pin_horus}: {e}")
        return False

def eliminar_empleado(pin_horus):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE empleados SET activo = 0 WHERE pin_horus = ?', (pin_horus,))
        conn.commit()
        conn.close()
        print(f"✅ Empleado PIN {pin_horus} desactivado")
        return True
    except Exception as e:
        print(f"❌ Error eliminando empleado {pin_horus}: {e}")
        return False

def obtener_empleado_por_pin(pin_horus):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_odoo, nombre, activo, uid_horus, foto_enviada, ultima_foto_hash FROM empleados WHERE pin_horus = ?', (pin_horus,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id_odoo': row[0], 'nombre': row[1], 'activo': row[2], 'uid_horus': row[3], 'foto_enviada': row[4], 'ultima_foto_hash': row[5]}
        return None
    except Exception as e:
        print(f"❌ Error consultando empleado {pin_horus}: {e}")
        return None

def obtener_empleado_por_id_odoo(id_odoo):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT pin_horus, nombre, activo, uid_horus, foto_enviada, ultima_foto_hash FROM empleados WHERE id_odoo = ?', (id_odoo,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'pin_horus': row[0], 'nombre': row[1], 'activo': row[2], 'uid_horus': row[3], 'foto_enviada': row[4], 'ultima_foto_hash': row[5]}
        return None
    except Exception as e:
        print(f"❌ Error consultando empleado por ID {id_odoo}: {e}")
        return None

# ----------------------------------------------------------------------
# FUNCIONES PARA MAPEO DE PINS
# ----------------------------------------------------------------------
def guardar_mapeo(id_odoo, pin_horus, uid_horus=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO mapeo_pins (id_odoo, pin_horus, uid_horus)
            VALUES (?, ?, ?)
        ''', (id_odoo, pin_horus, uid_horus))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error guardando mapeo {id_odoo}->{pin_horus}: {e}")
        return False

def obtener_pin_por_id_odoo(id_odoo):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT pin_horus FROM mapeo_pins WHERE id_odoo = ?', (id_odoo,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        print(f"❌ Error obteniendo mapeo para {id_odoo}: {e}")
        return None

def obtener_id_odoo_por_pin(pin_horus):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_odoo FROM mapeo_pins WHERE pin_horus = ?', (pin_horus,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        print(f"❌ Error obteniendo mapeo para PIN {pin_horus}: {e}")
        return None

# ----------------------------------------------------------------------
# FUNCIONES PARA ASISTENCIAS
# ----------------------------------------------------------------------
def guardar_asistencia(pin_horus, fecha_hora, tipo='facial'):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        empleado = obtener_empleado_por_pin(pin_horus)
        if not empleado:
            conn.close()
            print(f"⚠️ PIN {pin_horus} no existe en BD, no se guarda asistencia")
            return False, "Empleado no encontrado"
        if not empleado['activo']:
            conn.close()
            print(f"⚠️ PIN {pin_horus} inactivo, no se guarda asistencia")
            return False, "Empleado inactivo"

        cursor.execute('''
            INSERT OR IGNORE INTO asistencias (pin_horus, fecha_hora, tipo, enviado_odoo)
            VALUES (?, ?, ?, 0)
        ''', (pin_horus, fecha_hora, tipo))
        inserted = cursor.rowcount
        conn.commit()
        conn.close()
        if inserted > 0:
            print(f"✅ Asistencia guardada: {pin_horus} - {fecha_hora}")
            return True, "Asistencia guardada"
        else:
            print(f"ℹ️ Asistencia duplicada omitida: {pin_horus} - {fecha_hora}")
            return False, "Duplicado"
    except Exception as e:
        print(f"❌ Error guardando asistencia {pin_horus} {fecha_hora}: {e}")
        return False, str(e)

def marcar_asistencia_enviada(asistencia_id, odoo_attendance_id=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if odoo_attendance_id:
            cursor.execute('UPDATE asistencias SET enviado_odoo = 1, odoo_attendance_id = ? WHERE id = ?',
                           (odoo_attendance_id, asistencia_id))
        else:
            cursor.execute('UPDATE asistencias SET enviado_odoo = 1 WHERE id = ?', (asistencia_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error marcando asistencia {asistencia_id}: {e}")
        return False

def obtener_asistencias_pendientes(limite=1000):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, pin_horus, fecha_hora, tipo
            FROM asistencias
            WHERE enviado_odoo = 0
            ORDER BY fecha_hora ASC
            LIMIT ?
        ''', (limite,))
        rows = cursor.fetchall()
        conn.close()
        return [{'id': r[0], 'pin_horus': r[1], 'fecha_hora': r[2], 'tipo': r[3]} for r in rows]
    except Exception as e:
        print(f"❌ Error obteniendo asistencias pendientes: {e}")
        return []

# ----------------------------------------------------------------------
# FUNCIONES PARA LOGS
# ----------------------------------------------------------------------
def registrar_log(nivel, modulo, mensaje):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (nivel, modulo, mensaje)
            VALUES (?, ?, ?)
        ''', (nivel, modulo, mensaje))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[{nivel}] {modulo}: {mensaje} (ERROR LOG: {e})")

if __name__ == '__main__':
    init_db()
    optimizar_indices()
    print("✅ Base de datos lista para usar.")