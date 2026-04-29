@echo off
title Middleware Horus-Odoo
cd /d C:\Middleware_Horus_Odoo
:inicio
echo [%date% %time%] Iniciando Middleware...
call venv\Scripts\activate.bat
python src/adms_server.py
echo [%date% %time%] El middleware se detuvo. Reiniciando Middleware en 5 ...
timeout /t 5
goto inicio