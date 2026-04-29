@echo off
title Instalador Middleware Horus-Odoo
echo ========================================
echo  Instalador del Middleware Horus-Odoo
echo ========================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado. Por favor, instala Python 3.12 desde python.org
    echo y asegúrate de marcarlo en PATH.
    pause
    exit /b 1
) else (
    echo [OK] Python encontrado.
)

:: 2. Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

:: 3. Activar entorno virtual e instalar dependencias
echo Instalando dependencias...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Falló la instalación de dependencias.
    pause
    exit /b 1
)

:: 4. Crear archivo de configuración inicial (si no existe)
if not exist config.json (
    echo Creando config.json con valores por defecto...
    python -c "from src.config_manager import save_config, DEFAULT_CONFIG; save_config(DEFAULT_CONFIG)"
)

:: 5. Preguntar si se desea crear tareas programadas
echo.
set /p crear_tareas="¿Deseas crear las tareas programadas para inicio automático? (s/n): "
if /i "%crear_tareas%"=="s" (
    echo Creando tareas programadas...
    schtasks /create /tn "Middleware Horus-Odoo" /tr "C:\Middleware_Horus_Odoo\run_middleware.bat" /sc onstart /ru SYSTEM /f
    schtasks /create /tn "Configurador Horus-Odoo" /tr "C:\Middleware_Horus_Odoo\run_config.bat" /sc onstart /ru SYSTEM /f
    echo [OK] Tareas creadas.
)

echo.
echo ========================================
echo  Instalación completada.
echo  Puedes iniciar el middleware manualmente ejecutando:
echo    - run_middleware.bat  (servidor principal)
echo    - run_config.bat      (panel de configuración)
echo.
echo  O reinicia el equipo para que arranquen automáticamente.
echo ========================================
pause