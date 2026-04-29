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

- Odoo 17 Community Edition instalado en una computadora.
- Módulos base: `hr` (Empleados), `hr_attendance` (Asistencias).
- Navegador moderno con soporte para `getUserMedia` y WebGL (Chrome, Brave, Edge) con permisos de uso en la cámara y ubicación.

## Instalación del Módulo de Reconocimiento Facial
Sigue estas instrucciones al pie de la letra. Si te pierdes, vuelve a leer el paso anterior.

1. Descarga la carpeta.

En el ícono verde (<> Code), debes buscar una opción "Download ZIP", haz clic en esa opción y comenzará la descarga automáticamente.

La carpeta se va a descargar como `sttl_face_attendance-main.zip`.

En la carpeta de descargas de tu computadora, buscas la carpeta descargada, en ella, haz clic derecho y busca "Extraer Todo", aceptas y ahora ya no tendrá la extención .zip, por lo que será necesario buscar la capeta con el mismo nombre y adentro, vuelve a tener esa misma carpeta (sttl_face_attendance-main), será necesario renombrarla, solo quita `-main`, quedando así `sttl_face_attendance`.

Dentro de esa carpeta renombrada, verás todos los archivos del módulo.

2. Activar los módulos básicos (Empleados y Asistencias)
Abre Odoo en tu navegador e inicia sesión con tu usuario administrador.

En la esquina superior izquierda verás un ícono con cuadrados apilados (☰). Haz clic en él.

Se desplegará un menú. Busca y haz clic en Aplicaciones (tiene un icono de rompecabezas).

Aparecerá una pantalla con muchas aplicaciones. Arriba hay una barra de búsqueda.

Borra lo que tenga escrito y escribe la palabra Empleados.

Busca en los resultados el módulo llamado Empleados (suele tener un icono de personas).

Haz clic en el botón Activar que está debajo del nombre. Espera unos segundos a que se active (verás un mensaje de confirmación).

Vuelve a hacer clic en el ícono de cuadritos (arriba a la izquierda) y selecciona Aplicaciones otra vez.

En la barra de búsqueda, borra y escribe Asistencias.

Localiza el módulo Asistencias (icono de reloj) y haz clic en Activar. Espera.

3. Activar el modo desarrollador (necesario para ver nuestro módulo)
En la misma pantalla de Aplicaciones, haz clic en el ícono de cuadritos y luego en Ajustes (suele tener un icono de engranaje).

Desplázate hasta el final de la página. Busca la sección llamada Herramientas de desarrollador.

Dentro de esa sección, verás la opción Activar el modo de desarrollador. Haz clic en ella.

La página se recargará automáticamente (no te preocupes, es normal).

4. Copiar la carpeta del módulo a la carpeta de Odoo
Abre el Explorador de archivos de Windows (la carpeta amarilla).

Ve a la carpeta donde tienes Odoo instalado. Por lo general está en:

text
C:\Program Files\Odoo 17.0.20260204\
Si no es esa, busca la carpeta que tiene el nombre "Odoo 17" en Archivos de programa.

Dentro de esa carpeta, entra en server → odoo → addons.
La ruta completa sería algo así:

text
C:\Program Files\Odoo 17.0.20260204\server\odoo\addons
Ahora, en otra ventana del explorador, ve a la carpeta Descargas (o donde hayas guardado la carpeta sttl_face_attendance).

Selecciona la carpeta sttl_face_attendance con un clic y cópiala (puedes presionar Ctrl + C).

Vuelve a la carpeta addons de Odoo y pega la carpeta allí (Ctrl + V). Si pide permisos de administrador, acepta.
Asegúrate de que la carpeta se llame exactamente sttl_face_attendance (sin espacios).

5. Reiniciar el servicio de Odoo
Abre el Administrador de tareas de Windows. Puedes hacerlo presionando Ctrl + Shift + Esc.

Ve a la pestaña Servicios (a veces hay que hacer clic en "Más detalles" para ver las pestañas).

Busca en la lista un servicio que se llame algo como odoo-server-17.0 o Odoo.

Haz clic derecho sobre ese servicio y selecciona Reiniciar.

Espera unos segundos a que el servicio se detenga y vuelva a iniciar (la lista se actualizará sola).

6. Actualizar la lista de aplicaciones en Odoo
Regresa a tu navegador (la página de Odoo donde estabas).

Recarga la página presionando la tecla F5 o Ctrl + R.

Vuelve a hacer clic en el ícono de cuadritos y selecciona Aplicaciones.

En la parte superior, a la derecha de la barra de búsqueda, verás un botón que dice Actualizar lista de aplicaciones. Haz clic en él.

Aparecerá un mensaje preguntando si estás seguro. Haz clic en OK o Confirmar.

La página se recargará de nuevo (esto puede tardar unos segundos).

7. Instalar el módulo de reconocimiento facial
En la misma pantalla de Aplicaciones, ve a la barra de búsqueda (arriba).

Borra lo que haya y escribe la palabra face.

En los resultados aparecerá un módulo llamado Reconocimiento Facial para Asistencia de RRHH.

Haz clic en el botón Activar que está debajo del nombre.

Espera unos momentos. Verás un mensaje de que el módulo se ha instalado correctamente.

¡Listo! Ya tienes el módulo funcionando.
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
