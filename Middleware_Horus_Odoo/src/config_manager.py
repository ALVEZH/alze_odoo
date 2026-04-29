# config_manager.py
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

DEFAULT_CONFIG = {
    "odoo": {
        "url": "http://devo.uaalze.com",
        "db": "bd_odoo1",
        "username": "admin",
        "password": "admin"
    },
    "horus": {
        "ip": "192.168.1.105",
        "port": 4370,
        "password": "0"
    },
    "sync": {
        "horus_to_bd_interval": 10,
        "odoo_to_horus_interval": 10,
        "attendance_sync_interval": 10,
        "horus_to_odoo_interval": 60
    }
}

def load_config():
    """Carga la configuración desde config.json. Si no existe, crea una con valores por defecto."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Guarda la configuración en config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def update_odoo_config(url, db, username, password):
    """Actualiza solo la parte de Odoo de la configuración."""
    config = load_config()
    config['odoo'] = {
        'url': url,
        'db': db,
        'username': username,
        'password': password
    }
    save_config(config)

def get_odoo_config():
    """Devuelve la configuración de Odoo."""
    return load_config().get('odoo', DEFAULT_CONFIG['odoo'])

def update_horus_config(ip, port, password):
    """Actualiza solo la parte de Horus de la configuración."""
    config = load_config()
    config['horus'] = {
        'ip': ip,
        'port': port,
        'password': password
    }
    save_config(config)

def get_horus_config():
    """Devuelve la configuración de Horus."""
    return load_config().get('horus', DEFAULT_CONFIG['horus'])

def get_sync_intervals():
    """Devuelve los intervalos de sincronización."""
    return load_config().get('sync', DEFAULT_CONFIG['sync'])