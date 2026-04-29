# src/odoo_client.py
import xmlrpc.client
from datetime import datetime

class OdooClient:
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None

    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                raise Exception("Credenciales inválidas")
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"✅ Conectado a Odoo - UID: {self.uid}")
            return True
        except Exception as e:
            print(f"❌ Error conectando a Odoo: {e}")
            return False

    def search_employees(self, domain=None, fields=None):
        if domain is None:
            domain = []
        if fields is None:
            fields = ['id', 'name']
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            'hr.employee', 'search_read',
            [domain], {'fields': fields}
        )

    def create_employee(self, values):
        emp_id = self.models.execute_kw(
            self.db, self.uid, self.password,
            'hr.employee', 'create', [values]
        )
        return emp_id

    def write_employee(self, emp_id, values):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            'hr.employee', 'write', [[emp_id], values]
        )

    def unlink_employee(self, emp_id):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            'hr.employee', 'unlink', [[emp_id]]
        )

    def toggle_active(self, emp_id, active=True):
        return self.write_employee(emp_id, {'active': active})

    # --------------------------------------------------------------
    # Asistencias (hr.attendance)
    # --------------------------------------------------------------
    def create_attendance(self, employee_id, timestamp_str):
        """
        Registra una marcación en Odoo.
        - Si el empleado tiene una entrada abierta (sin check_out), la cierra con esta nueva marcación.
        - Si no, crea una nueva entrada.
        - En caso de que la nueva marcación sea anterior a la entrada abierta (error de fechas),
          se fuerza una nueva entrada.
        """
        # Buscar la última asistencia del empleado
        domain = [('employee_id', '=', employee_id)]
        last_attendance = self.models.execute_kw(
            self.db, self.uid, self.password,
            'hr.attendance', 'search_read',
            [domain], {'limit': 1, 'order': 'check_in desc', 'fields': ['id', 'check_in', 'check_out']}
        )

        # Si hay una entrada abierta
        if last_attendance and last_attendance[0]['check_out'] is False:
            last = last_attendance[0]
            try:
                # Intentar cerrar la entrada con la nueva marcación
                self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'hr.attendance', 'write',
                    [[last['id']], {'check_out': timestamp_str}]
                )
                print(f"   Asistencia {last['id']} cerrada con salida {timestamp_str}")
                return last['id']
            except Exception as e:
                # Si falla (por ejemplo, porque la nueva hora es anterior), creamos una nueva entrada
                print(f"   No se pudo cerrar la asistencia anterior: {e}. Creando nueva entrada.")
                vals = {'employee_id': employee_id, 'check_in': timestamp_str}
                new_id = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'hr.attendance', 'create', [vals]
                )
                return new_id
        else:
            # No hay entrada abierta, crear nueva
            vals = {'employee_id': employee_id, 'check_in': timestamp_str}
            new_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'hr.attendance', 'create', [vals]
            )
            print(f"   Nueva asistencia creada (entrada) con ID {new_id}")
            return new_id