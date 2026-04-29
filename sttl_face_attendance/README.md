# Módulo de Reconocimiento Facial para Asistencia

Módulo para Odoo 17 Community que añade reconocimiento facial al kiosko de asistencia. Permite a los empleados registrar entrada/salida mediante su rostro, con soporte para cámara frontal/trasera, modo continuo para puntos de acceso, y configuración de intentos.

## Características principales

- **Captura de imagen de empleado** desde el formulario (botón "Crear Foto").
- **Dos modos de cámara**: frontal y trasera, seleccionables mediante iconos.
- **Multiples Registros**: la cámara permanece abierta y registra múltiples empleados sin cerrarse, mostrando un indicador verde de registro realizado con hora y tipo de registro (entrada/salida).
- **Configuración de intentos**: número máximo de intentos y segundos entre detecciones, ajustable desde la interfaz.
- **Botón de identificación manual**: un panel para el registro manual del empleado.
- **Botón para agregar empleado**: se requiere iniciar sesión con una cuenta registrada con permisos para crear a un empleado nuevo y registrarlo, importante al teminar el registro, se debe cerrar sesión.
- **Diseño responsivo** adaptado a móviles, tablets y escritorio.
- **Overlay de cámara** con botones para reiniciar y cerrar, y temporizador visual de intentos.

## Requisitos

- Odoo 17 Community Edition
- Módulos base: `hr`, `hr_attendance`
- Navegador moderno con soporte para `getUserMedia` y WebGL (Chrome, Firefox, Edge) con permisos de uso en la cámara y ubicación.

## Instalación

1. En Odoo, en el icono de un cuadrado en la parte superior izquierda hay un cuadrado, al seleccionar hay una lista de aplicaciones instaladas de Odoo, selecciona una llamada "Aplicaciones". Al entrar, se muestran todas las aplicaciones posibles a activar, busca "Empleados" y presiona el botón de "Activar", después busca "Asistencias" y presiona el botón activar.
2. Activa el modo desarrollador desde "Ajustes", hasta abajo hay una sección llamada "Herramientas de desarrollador" y una opción llamada "Activar modo de desarrollador", clic en el y se reinicia la página automáticamente.
3. Copia la carpeta `sttl_face_attendance` (asegurate que tenga ese nombre al descargar) en el directorio de addons de Odoo (Odoo 17 → server → odoo → adoons) desde el explorador de archivos, la carpeta dependerá la ubicación donde fue instalada.
4. Reinicia el servicio de Odoo, busca servicios del sistema, al entrar debes buscar algo similar a `odoo-server-17.0`, lo seleccionas, presionas clic derecho y haces clic en "Reiniciar", solo esperas a que se reinicie.
5. En Odoo, actualiza la página con F5 o Ctr + R
6. Regresa al apartado de Aplicaciones y en el baner superior hay una sección llamada "Actualizar lista de aplicaciones", al activarla, saldrá un mensaje de confirmación, se confirma y actualiza la página.
7. En ese mismo panel de aplicaciones hay un buscador, borra lo que tenga y escribe "face" y aparece el módulo de reconocimiento facial, solo presiona activar y automáticamente se aplicarán los cambios.

## Validación de Instalación

- Entra al módulo de empleados.
- Entra a un empleado para inspeccionar su información o en el botón de crear nuevo empleado.
- En la foto de perfil hay un botón "Crear Foto", confirmando la instalación.

- Entra al módulo de asistencias.
- En el baner superior hay una opción llamada "Modo Quiosco".
- Se debe ver el panel con el título de "CONTROL DE ASISTENCIAS".

## Configuración

No requiere configuración adicional. Los ajustes de intentos y segundos se guardan automáticamente en el navegador (localStorage).

## Uso

### En el módulo Empleados
- Ve a un empleado (nuevo o existente) y haz clic en **Crear Foto** para capturar su foto (necesaria para el reconocimiento).

### En el módulo Asistencia
- Aparecerán los iconos de cámara frontal y trasera.
- Ajusta los intentos y segundos con los botones +/–.
- Activa el botón **Multiples registros** si deseas que la cámara permanezca abierta.
- Haz clic en un icono de cámara para iniciar el reconocimiento.
- Al detectar un rostro coincidente, se registrará la asistencia y se mostrará un indicador (en modo continuo) o se cerrará la cámara y mostrará saludo o despedida (modo normal).
- Usa **Buscar Empleado** para selección manual de un empleado.
- **Agregar Empleado** abre la vista de empleados (requiere autenticación de administrador).
- **Salir** regresa al panel de inicio de sesión.

## Estructura del módulo

<img width="405" height="677" alt="image" src="https://github.com/user-attachments/assets/33a16bce-81cc-4de8-ba51-8a341fcb4018" />

## Carpeta face-api

Carpeta para uso de reconocimiento facial descargada desde https://justadudewhohacks.github.io/face-api.js/docs/index.html

## Licencia para el módulo en Odoo

LGPL-3
