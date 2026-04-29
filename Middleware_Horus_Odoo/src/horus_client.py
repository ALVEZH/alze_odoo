# src/horus_client.py
import base64
from datetime import datetime
from zk import ZK, const

class HorusTL1Client:
    def __init__(self, ip, port=4370, password=''):
        self.ip = ip
        self.port = port
        self.password = password if password is not None else ''
        self.zk = ZK(ip, port=port, timeout=30, password=self.password, force_udp=False)
        self.conn = None


    def sync_time(self, dt=None):
        """
        Sincroniza la hora del dispositivo con la hora del servidor.
        Si dt es None, usa datetime.now().
        Retorna True si tuvo éxito.
        """
        if not self.conn:
            raise Exception("No hay conexión activa.")
        if dt is None:
            dt = datetime.now()
        try:
            # El método de pyzk para ajustar la hora se llama set_time
            self.conn.set_time(dt)
            print(f"✅ Hora sincronizada en el dispositivo: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        except Exception as e:
            print(f"❌ Error sincronizando hora: {e}")
            return False

    # ------------------------------------------------------------------
    # Gestión de conexión
    # ------------------------------------------------------------------
    def connect(self):
        try:
            self.conn = self.zk.connect()
            print(f"✅ Conectado a Horus TL1 en {self.ip}")
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False

    def disconnect(self, silent=False):
        if self.conn:
            self.conn.disconnect()
            if not silent:
                print("🔌 Desconectado")
            self.conn = None

    # ------------------------------------------------------------------
    # Gestión de usuarios (incluye user_id)
    # ------------------------------------------------------------------
    def get_users(self):
        if not self.conn:
            raise Exception("No hay conexión activa.")
        self.conn.disable_device()
        raw_users = self.conn.get_users()
        self.conn.enable_device()

        users = []
        for user in raw_users:
            privilege = 'Admin' if user.privilege == const.USER_ADMIN else 'User'
            # Decodificar nombre (puede venir en base64)
            if isinstance(user.name, bytes):
                try:
                    name = base64.b64decode(user.name).decode('utf-8', errors='replace')
                except:
                    name = user.name.decode('utf-8', errors='replace')
            else:
                name = user.name
            users.append({
                'uid': user.uid,
                'user_id': user.user_id,   # Identificador visible en el dispositivo
                'name': name,
                'privilege': privilege,
                'password': user.password,
                'group_id': user.group_id,
            })
        return users

    def user_exists_by_uid(self, uid):
        """Verifica si existe un usuario con ese UID."""
        users = self.get_users()
        return any(u['uid'] == uid for u in users)

    def user_exists_by_user_id(self, user_id):
        """Verifica si existe un usuario con ese user_id (el visible)."""
        users = self.get_users()
        return any(u['user_id'] == str(user_id) for u in users)

    def get_next_available_uid(self, start_from=1):
        """Busca el siguiente UID libre (empezando desde start_from)."""
        users = self.get_users()
        existing_uids = {u['uid'] for u in users}
        uid = start_from
        while uid in existing_uids:
            uid += 1
        return uid

    def create_user(self, uid, name, password='', group_id='', user_id=None):
        """
        Crea un usuario en el dispositivo.
        Si user_id no se proporciona, se usa el mismo uid.
        Verifica que ni uid ni user_id estén ocupados.
        Retorna (success, mensaje).
        """
        if not self.conn:
            raise Exception("No hay conexión activa.")
        if user_id is None:
            user_id = str(uid)
        else:
            user_id = str(user_id)

        # Verificar si el uid ya existe
        if self.user_exists_by_uid(uid):
            return False, f"⚠️ El UID {uid} ya existe en el dispositivo."

        # Verificar si el user_id ya existe
        if self.user_exists_by_user_id(user_id):
            return False, f"⚠️ El user_id {user_id} ya existe en el dispositivo."

        self.conn.disable_device()
        try:
            self.conn.set_user(
                uid=uid,
                name=name,
                privilege=const.USER_DEFAULT,
                password=password,
                group_id=group_id,
                user_id=user_id
            )
            self.conn.test_voice()
            return True, f"✅ Usuario '{name}' creado con UID {uid} y user_id {user_id}"
        except Exception as e:
            return False, f"❌ Error al crear usuario: {e}"
        finally:
            self.conn.enable_device()

    def update_user(self, uid, new_name=None, new_password=None, new_group_id=None, new_user_id=None):
        """
        Actualiza un usuario existente.
        Solo modifica los campos proporcionados.
        Si se cambia el user_id, verifica que no esté ocupado.
        """
        if not self.conn:
            raise Exception("No hay conexión activa.")
        if not self.user_exists_by_uid(uid):
            return False, f"⚠️ El usuario con UID {uid} no existe."

        users = self.get_users()
        current = next((u for u in users if u['uid'] == uid), None)
        if not current:
            return False, f"⚠️ No se pudo recuperar información del usuario {uid}."

        name = new_name if new_name is not None else current['name']
        password = new_password if new_password is not None else current['password']
        group_id = new_group_id if new_group_id is not None else current['group_id']
        user_id = new_user_id if new_user_id is not None else current['user_id']

        # Si se cambia el user_id, verificar que no esté ocupado por otro usuario
        if new_user_id is not None and new_user_id != current['user_id']:
            if self.user_exists_by_user_id(new_user_id):
                return False, f"⚠️ El user_id {new_user_id} ya está ocupado por otro usuario."

        self.conn.disable_device()
        try:
            self.conn.set_user(
                uid=uid,
                name=name,
                privilege=const.USER_DEFAULT,
                password=password,
                group_id=group_id,
                user_id=user_id
            )
            self.conn.test_voice()
            return True, f"✅ Usuario UID {uid} actualizado correctamente."
        except Exception as e:
            return False, f"❌ Error al actualizar usuario: {e}"
        finally:
            self.conn.enable_device()

    def delete_user(self, uid):
        """
        Elimina un usuario por su UID.
        Retorna (success, mensaje). Si falla, success=False.
        """
        if not self.conn:
            return False, "No hay conexión activa"
        if not self.user_exists_by_uid(uid):
            return False, f"⚠️ El usuario con UID {uid} no existe"

        self.conn.disable_device()
        try:
            self.conn.delete_user(uid)  # Nota: delete_user usa user_id, no uid
            self.conn.test_voice()
            print(f"   ✅ Usuario UID {uid} eliminado físicamente del dispositivo")
            return True, f"Usuario {uid} eliminado"
        except Exception as e:
            print(f"   ❌ Error al eliminar usuario {uid}: {e}")
            return False, f"Error: {e}"
        finally:
            self.conn.enable_device()

    # ------------------------------------------------------------------
    # Asistencias y facial
    # ------------------------------------------------------------------
    def get_attendance(self):
        """Obtiene registros de asistencia, omitiendo fechas inválidas."""
        if not self.conn:
            raise Exception("No hay conexión activa.")
        self.conn.disable_device()
        try:
            raw = self.conn.get_attendance()
        except ValueError:
            # Dispositivo con primer registro corrupto
            raw = []
        except Exception as e:
            print(f"⚠️ Error al obtener asistencias: {e}")
            raw = []
        finally:
            self.conn.enable_device()

        attendance = []
        for att in raw:
            try:
                ts = att.timestamp
                if ts.year < 2000 or ts.year > 2100:
                    continue
                attendance.append({
                    'user_id': att.user_id,   # Nota: esto es el user_id del dispositivo
                    'timestamp': ts,
                    'status': att.status
                })
            except (ValueError, AttributeError):
                continue
        return attendance

    def enroll_face(self, uid):
        """Activa modo registro facial (timeout manejado)."""
        if not self.conn:
            raise Exception("No hay conexión activa.")
        if not self.user_exists_by_uid(uid):
            return False, f"⚠️ El usuario UID {uid} no existe."

        self.conn.disable_device()
        try:
            self.conn.enroll_user(uid=uid, temp_id=111)
            print("📸 Comando de registro facial enviado.")
            return True, "Modo registro facial activado."
        except TimeoutError:
            return False, "⏱️ Timeout: registro no completado automáticamente (manual requerido)."
        except Exception as e:
            return False, f"❌ Error en registro facial: {e}"
        finally:
            self.conn.enable_device()
            self.conn.test_voice()