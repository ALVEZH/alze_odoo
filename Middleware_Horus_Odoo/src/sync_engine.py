# src/sync_engine.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import traceback
from src.horus_client import HorusTL1Client
from src.database import guardar_asistencia, registrar_log, obtener_empleado_por_pin

class AttendancePoller:
    def __init__(self, horus_ip, horus_port=4370, horus_password='0', interval=10, debug=False):
        self.horus_ip = horus_ip
        self.horus_port = horus_port
        self.horus_password = horus_password
        self.interval = interval
        self.debug = debug
        self.client = HorusTL1Client(horus_ip, port=horus_port, password=horus_password)
        self.ultima_marcacion_id = 0  # opcional

    def poll_once(self):
        if not self.client.connect():
            registrar_log('ERROR', 'AttendancePoller', f"No se pudo conectar a {self.horus_ip}")
            return

        try:
            attends = self.client.get_attendance()
            if self.debug:
                print(f"📊 Asistencias crudas: {len(attends)}")
            
            if attends:
                registrar_log('INFO', 'AttendancePoller', f"Se obtuvieron {len(attends)} registros")
            
            for att in attends:
                pin = str(att['user_id'])
                timestamp = att['timestamp']
                
                empleado = obtener_empleado_por_pin(pin)
                if not empleado:
                    if self.debug:
                        print(f"⚠️ PIN {pin} no existe en BD")
                    continue
                if not empleado['activo']:
                    if self.debug:
                        print(f"⚠️ PIN {pin} está inactivo")
                    continue

                success, msg = guardar_asistencia(pin, timestamp)
                if success:
                    registrar_log('INFO', 'AttendancePoller', msg)
                    if self.debug:
                        print(f"✅ {msg}")
                else:
                    registrar_log('WARNING', 'AttendancePoller', msg)
                    if self.debug:
                        print(f"❌ {msg}")
        except Exception as e:
            registrar_log('ERROR', 'AttendancePoller', f"Error en polling: {e}")
            if self.debug:
                print(f"❌ Error: {e}")
        finally:
            self.client.disconnect(silent=not self.debug)
    def start(self):
        registrar_log('INFO', 'AttendancePoller', f"Iniciando polling cada {self.interval} segundos")
        print(f"🔄 Iniciando polling de asistencias cada {self.interval} segundos...")
        while True:
            self.poll_once()
            time.sleep(self.interval)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Middleware de captura de asistencias Horus TL1')
    parser.add_argument('--ip', default='192.168.1.105', help='IP del dispositivo Horus')
    parser.add_argument('--port', type=int, default=4370, help='Puerto (default: 4370)')
    parser.add_argument('--password', default='0', help='Contraseña del dispositivo')
    parser.add_argument('--interval', type=int, default=30, help='Intervalo de polling en segundos')
    parser.add_argument('--debug', action='store_true', help='Modo debug con más prints')
    args = parser.parse_args()

    from src.database import init_db
    init_db()
    
    poller = AttendancePoller(
        horus_ip=args.ip,
        horus_port=args.port,
        horus_password=args.password,
        interval=args.interval,
        debug=args.debug
    )
    
    try:
        poller.start()
    except KeyboardInterrupt:
        from src.database import registrar_log
        registrar_log('INFO', 'AttendancePoller', "Polling detenido por el usuario")
        print("\n⏹️  Polling detenido.")