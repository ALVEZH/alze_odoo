@echo off
title Configurador Middleware Horus-Odoo
cd /d C:\Middleware_Horus_Odoo
:inicio
echo [%date% %time%] Iniciando panel configurador...
call venv\Scripts\activate.bat
python config_server.py
echo [%date% %time%] El panel se detuvo. Reiniciando panel en 5 ...
timeout /t 5
goto inicio