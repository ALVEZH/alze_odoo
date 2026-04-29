# config_server.py
from flask import Flask, render_template_string, request, redirect, url_for, flash, get_flashed_messages
from src import config_manager
import requests
import os
import subprocess

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Token secreto (debe coincidir con el definido en adms_server.py)
SHUTDOWN_TOKEN = "deactivate"

# Rutas absolutas (ajusta si es necesario)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_MIDDLEWARE_BAT = os.path.join(BASE_DIR, "run_middleware.bat")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Configuración del Middleware Horus-Odoo</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 700px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        label { display: block; margin-top: 15px; font-weight: bold; }
        input[type=text], input[type=password], input[type=number] { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }
        button { margin-top: 20px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        button:hover { background: #45a049; }
        .btn-stop { background: #dc3545; }
        .btn-stop:hover { background: #c82333; }
        .btn-start { background: #007bff; }
        .btn-start:hover { background: #0069d9; }
        .message { padding: 10px; margin-top: 20px; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .status { margin: 20px 0; font-size: 1.1em; }
        .config-section { background: #f9f9fc; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Configuración del Middleware</h1>
        {% for category, message in messages %}
        <div class="message {{ category }}">{{ message }}</div>
        {% endfor %}

        <div class="status">
            <strong>Estado del middleware:</strong> 
            {% if middleware_running %}
                <span style="color:green;">EJECUTÁNDOSE</span>
            {% else %}
                <span style="color:red;">DETENIDO</span>
            {% endif %}
        </div>

        <div style="text-align: center; margin: 20px 0;">
            <form action="/start" method="post" style="display: inline;">
                <button type="submit" class="btn-start">Encender middleware</button>
            </form>
            <form action="/restart" method="post" style="display: inline;">
                <button type="submit" style="background-color: #ffc107; color: black;">Reiniciar middleware</button>
            </form>
            <!-- <form action="/stop" method="post" style="display: inline;">
                <button type="submit" class="btn-stop">Apagar middleware</button>
            </form> -->
        </div>

        <!-- Configuración de Odoo -->
        <div class="config-section">
            <h2>⚙️ Configuración de conexión a Odoo</h2>
            <form method="post">
                <input type="hidden" name="form_type" value="odoo">
                <label>URL de Odoo (con puerto, ej. http://localhost:8069):</label>
                <input type="text" name="url" value="{{ odoo_config.url }}" required>
                <label>Base de datos:</label>
                <input type="text" name="db" value="{{ odoo_config.db }}" required>
                <label>Usuario:</label>
                <input type="text" name="username" value="{{ odoo_config.username }}" required>
                <label>Contraseña:</label>
                <input type="password" name="password" value="{{ odoo_config.password }}" required>
                <button type="submit">Guardar configuración Odoo</button>
            </form>
        </div>

        <!-- Configuración de Horus -->
        <div class="config-section">
            <h2>📡 Configuración de conexión a Horus TL1</h2>
            <form method="post">
                <input type="hidden" name="form_type" value="horus">
                <label>IP del dispositivo:</label>
                <input type="text" name="ip" value="{{ horus_config.ip }}" required>
                <label>Puerto (por defecto 4370):</label>
                <input type="number" name="port" value="{{ horus_config.port }}" required>
                <label>Contraseña (si tiene, por defecto "0"):</label>
                <input type="password" name="password" value="{{ horus_config.password }}">
                <button type="submit">Guardar configuración Horus</button>
            </form>
        </div>

    </div>
</body>
</html>
"""

def check_middleware():
    """Verifica si el proceso de adms_server está corriendo."""
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('adms_server.py' in arg for arg in cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            continue
    return False

@app.route('/', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'odoo':
            url = request.form['url']
            db = request.form['db']
            username = request.form['username']
            password = request.form['password']
            config_manager.update_odoo_config(url, db, username, password)
            flash('Configuración de Odoo guardada correctamente.', 'success')
        elif form_type == 'horus':
            ip = request.form['ip']
            try:
                port = int(request.form['port'])
            except:
                port = 4370
            password = request.form['password']
            config_manager.update_horus_config(ip, port, password)
            flash('Configuración de Horus guardada correctamente.', 'success')
        return redirect(url_for('config'))

    odoo_config = config_manager.get_odoo_config()
    horus_config = config_manager.get_horus_config()
    middleware_running = check_middleware()
    messages = get_flashed_messages(with_categories=True)
    return render_template_string(HTML_TEMPLATE,
                                  odoo_config=odoo_config,
                                  horus_config=horus_config,
                                  middleware_running=middleware_running,
                                  messages=messages)

@app.route('/restart', methods=['POST'])
def restart():
    """Envía una solicitud de apagado al middleware principal."""
    try:
        url = f"http://localhost:8000/shutdown?token={SHUTDOWN_TOKEN}"
        resp = requests.post(url, timeout=5)
        if resp.status_code == 200:
            flash('Reinicio solicitado correctamente. El middleware se reiniciará en unos segundos.', 'success')
        else:
            flash(f'Error al solicitar reinicio: {resp.text}', 'error')
    except requests.exceptions.ConnectionError:
        flash('No se pudo conectar al middleware. ¿Está ejecutándose?', 'error')
    except Exception as e:
        flash(f'Error inesperado: {e}', 'error')
    return redirect(url_for('config'))

@app.route('/stop', methods=['POST'])
def stop():
    """Envía solicitud de apagado sin esperar reinicio."""
    try:
        url = f"http://localhost:8000/shutdown?token={SHUTDOWN_TOKEN}"
        resp = requests.post(url, timeout=5)
        if resp.status_code == 200:
            flash('Apagado solicitado correctamente.', 'success')
        else:
            flash(f'Error al apagar: {resp.text}', 'error')
    except requests.exceptions.ConnectionError:
        flash('No se pudo conectar al middleware. ¿Está ejecutándose?', 'error')
    except Exception as e:
        flash(f'Error inesperado: {e}', 'error')
    return redirect(url_for('config'))

@app.route('/start', methods=['POST'])
def start():
    """Inicia el middleware ejecutando run_middleware.bat en una nueva ventana."""
    if check_middleware():
        flash('El middleware ya está en ejecución.', 'info')
    else:
        try:
            # Abre una nueva ventana de CMD con el script run_middleware.bat
            subprocess.Popen(['start', RUN_MIDDLEWARE_BAT], shell=True)
            flash('Middleware iniciado. Se abrirá una nueva ventana.', 'success')
        except Exception as e:
            flash(f'Error al iniciar el middleware: {e}', 'error')
    return redirect(url_for('config'))

if __name__ == '__main__':
    # Verificar dependencias
    try:
        import psutil
    except ImportError:
        print("⚠️ psutil no instalado. La verificación de estado no funcionará. Instala con: pip install psutil")
    app.run(host='0.0.0.0', port=8001, debug=False)