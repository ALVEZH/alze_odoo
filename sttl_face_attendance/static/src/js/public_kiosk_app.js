/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import attendanceApp from "@hr_attendance/public_kiosk/public_kiosk_app";
import { useService } from "@web/core/utils/hooks";

const MODEL_URL = '/sttl_face_attendance/static/face-api/weights/';
let faceModelsLoaded = false;

patch(attendanceApp.kioskAttendanceApp.prototype, {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        
        // Cargar configuración desde localStorage
        this.maxAttempts = parseInt(localStorage.getItem('face_maxAttempts')) || 3;
        this.attemptDelay = (parseInt(localStorage.getItem('face_attemptDelaySeconds')) || 3) * 1000;
        
        this.currentCameraMode = 'user';
        this.timerInterval = null;
        this.attempts = 0;
        this.continuousMode = false;
        this.lastRegisteredId = null;
        this.lastRegisteredTime = 0;
        
        setTimeout(() => {
            this._updateDisplays();
        }, 100);
    },

    _updateDisplays() {
        const maxSpan = document.getElementById('max-attempts-display');
        if (maxSpan) maxSpan.innerText = this.maxAttempts;
        const delaySpan = document.getElementById('delay-display');
        if (delaySpan) delaySpan.innerText = this.attemptDelay / 1000;
    },

    changeMaxAttempts(delta) {
        const newValue = this.maxAttempts + delta;
        if (newValue >= 1 && newValue <= 10) {
            this.maxAttempts = newValue;
            localStorage.setItem('face_maxAttempts', newValue);
            this._updateDisplays();
        }
    },

    changeAttemptDelay(delta) {
        const newValue = (this.attemptDelay / 1000) + delta;
        if (newValue >= 1 && newValue <= 15) {
            this.attemptDelay = newValue * 1000;
            localStorage.setItem('face_attemptDelaySeconds', newValue);
            this._updateDisplays();
        }
    },

    toggleContinuousMode() {
        this.continuousMode = !this.continuousMode;
    },

    initiateFaceAttendance: async function (cameraMode) {
        this.currentCameraMode = cameraMode || 'user';
        await this.setupCamera(this.employeeId, cameraMode);
    },

    async onManualSelection(employeeId) {
        await this.setupCamera(employeeId, 'environment');
    },

    openCreateEmployee() {
        window.open('/web#cids=1&menu_id=106&action=159&model=hr.employee&view_type=form', '_blank');
    },

    goBackToMain() {
        window.location.href = '/web';
    },

    async setupCamera(employeeId = null, cameraMode = null) {
        if (cameraMode) {
            this.currentCameraMode = cameraMode;
        }
        if (!faceModelsLoaded) {
            await Promise.all([
                faceapi.nets.tinyFaceDetector.load(MODEL_URL),
                faceapi.nets.faceLandmark68Net.load(MODEL_URL),
                faceapi.nets.faceRecognitionNet.load(MODEL_URL),
            ]);
            faceModelsLoaded = true;
        }

        return new Promise(async (resolve) => {
            this.cameraResolve = resolve;
            this.employeeId = employeeId;
            this.overlay = this._createOverlay();
            try {
                await this._startCameraStream();
                this._startDetection();
                this._addControlEventListeners();
            } catch (error) {
                alert("No se pudo acceder a la cámara");
                this._handleError(null, this.overlay, resolve);
            }
        });
    },

    async _startCameraStream() {
        if (this.stream) {
            this._stopStream(this.video);
        }
        const constraints = {
            video: {
                facingMode: this.currentCameraMode
            }
        };
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        this.video = this._setupVideoElement(this.stream);
    },

    _setupVideoElement(stream) {
        let video = document.getElementById('camera-stream');
        if (!video) {
            const camDiv = document.getElementById('cam-div');
            if (!camDiv) return null;
            video = document.createElement('video');
            video.id = 'camera-stream';
            camDiv.appendChild(video);
        }
        video.srcObject = stream;
        video.play();
        return video;
    },

    _createOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'camera_overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        document.body.appendChild(overlay);

        const camDiv = document.createElement('div');
        camDiv.id = 'cam-div';
        camDiv.style.cssText = `
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            min-width: 400px;
            position: relative;
            overflow: hidden;
        `;
        overlay.appendChild(camDiv);

        // --- NUEVO: Overlay grande de éxito (cubre toda la cámara) ---
        const bigSuccessOverlay = document.createElement('div');
        bigSuccessOverlay.id = 'big-success-overlay';
        bigSuccessOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(40, 167, 69, 0.9);
            color: white;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            z-index: 30;
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            box-sizing: border-box;
            backdrop-filter: blur(2px);
        `;
        bigSuccessOverlay.innerHTML = `
            <i class="fa fa-check-circle" style="font-size: 5rem; margin-bottom: 20px;"></i>
            <div id="big-success-name" style="font-size: 2.5rem;"></div>
            <div id="big-success-time" style="font-size: 1.8rem; margin-top: 10px;"></div>
            <div id="big-success-type" style="font-size: 2rem; margin-top: 10px;"></div>
        `;
        camDiv.appendChild(bigSuccessOverlay);

        // Overlay de advertencia (amarillo)
        const warningOverlay = document.createElement('div');
        warningOverlay.id = 'warning-overlay';
        warningOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 193, 7, 0.9);
            color: white;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            z-index: 30;
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            box-sizing: border-box;
            backdrop-filter: blur(2px);
        `;
        warningOverlay.innerHTML = `
            <i class="fa fa-exclamation-triangle" style="font-size: 5rem; margin-bottom: 20px;"></i>
            <div id="warning-message" style="font-size: 2.5rem;">Ya se registró</div>
        `;
        camDiv.appendChild(warningOverlay);

        // Mantenemos el temporizador
        const timerDiv = document.createElement('div');
        timerDiv.id = 'timer-display';
        timerDiv.style.cssText = `
            font-size: 18px;
            margin-bottom: 10px;
            font-weight: bold;
            color: #333;
        `;
        camDiv.appendChild(timerDiv);

        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = `
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
            flex-wrap: wrap;
        `;
        camDiv.appendChild(buttonContainer);

        const closeButton = document.createElement('button');
        closeButton.id = 'close-button';
        closeButton.textContent = 'Cerrar Cámara';
        closeButton.className = 'btn btn-secondary';
        buttonContainer.appendChild(closeButton);

        const restartButton = document.createElement('button');
        restartButton.id = 'restart-button';
        restartButton.textContent = 'Reiniciar Cámara';
        restartButton.className = 'btn btn-warning';
        buttonContainer.appendChild(restartButton);

        return overlay;
    },

    _addControlEventListeners() {
        document.getElementById('close-button').addEventListener('click', () => {
            this._handleError(this.video, this.overlay, this.cameraResolve);
        });

        document.getElementById('restart-button').addEventListener('click', () => {
            this._restartCamera();
        });
    },

    async _restartCamera() {
        this._stopDetection();
        await this._startCameraStream();
        this._startDetection();
    },

    _startDetection() {
        this.attempts = 0;
        this._updateTimerDisplay();
        this._scheduleAttempt();
    },

    _stopDetection() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }
    },

    _updateTimerDisplay() {
        const timerDiv = document.getElementById('timer-display');
        if (!timerDiv) return;
        if (this.continuousMode) {
            // En modo continuo, no mostramos el contador de intentos fijo
            timerDiv.textContent = ''; 
        } else {
            const remaining = this.maxAttempts - this.attempts;
            timerDiv.textContent = `Intentos restantes: ${remaining} / ${this.maxAttempts}`;
        }
    },

    _scheduleAttempt() {
        if (this.attempts >= this.maxAttempts) {
            alert('No se encontró ningún empleado después de varios intentos.');
            this._handleError(this.video, this.overlay, this.cameraResolve);
            return;
        }

        let timeLeft = this.attemptDelay / 1000;
        const timerDiv = document.getElementById('timer-display');
        if (timerDiv) {
            if (this.continuousMode) {
                timerDiv.textContent = `Próximo intento en ${timeLeft}s`;
            } else {
                timerDiv.textContent = `Próximo intento en ${timeLeft}s... (Intento ${this.attempts + 1}/${this.maxAttempts})`;
            }
        }

        // Limpiar intervalos anteriores
        if (this.timerInterval) clearInterval(this.timerInterval);
        this.timerInterval = setInterval(() => {
            timeLeft -= 1;
            if (timerDiv) {
                if (this.continuousMode) {
                    timerDiv.textContent = `Próximo intento en ${timeLeft}s`;
                } else {
                    timerDiv.textContent = `Próximo intento en ${timeLeft}s... (Intento ${this.attempts + 1}/${this.maxAttempts})`;
                }
            }
            if (timeLeft <= 0) {
                clearInterval(this.timerInterval);
                this.timerInterval = null;
            }
        }, 1000);

        if (this.timeout) clearTimeout(this.timeout);
        this.timeout = setTimeout(async () => {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
            await this._performAttempt();
        }, this.attemptDelay);
    },

    async _performAttempt() {
        if (!this.video) return;

        try {
            const faceDetection = await faceapi.detectSingleFace(this.video, new faceapi.TinyFaceDetectorOptions())
                .withFaceLandmarks()
                .withFaceDescriptor();

            if (!faceDetection) {
                this.attempts++;
                this._scheduleAttempt();
                return;
            }

            const employeeDetails = await this.rpc('/employee/images', { employee_id: this.employeeId });
            const matchingEmployeeId = await this._findMatchingEmployee(faceDetection, employeeDetails);
            if (matchingEmployeeId) {
                await this._handleEmployeeDetected(matchingEmployeeId);
                return;
            }

            this.attempts++;
            this._scheduleAttempt();
        } catch (error) {
            console.error("Error en detección facial:", error);
            alert('Error en la detección facial.');
            this._handleError(this.video, this.overlay, this.cameraResolve);
        }
    },

    async _findMatchingEmployee(faceDetection, employeeDetails) {
        for (const { employee_id, image, name } of employeeDetails) {
            if (!image) continue;

            try {
                const mimeMatch = image.match(/^data:(image\/[a-zA-Z]+);base64,/);
                const mimeType = mimeMatch ? mimeMatch[1] : 'image/png';
                const blob = this._base64ToBlob(image, mimeType);
                const referenceImage = await faceapi.bufferToImage(blob);

                const referenceDescriptor = await faceapi
                    .detectSingleFace(referenceImage, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks()
                    .withFaceDescriptor();

                if (referenceDescriptor) {
                    const distance = faceapi.euclideanDistance(
                        faceDetection.descriptor,
                        referenceDescriptor.descriptor
                    );
                    if (distance < 0.45) return employee_id;
                }
            } catch (error) {
                console.warn(`Error procesando empleado ${employee_id} (${name}):`, error);
                continue;
            }
        }
        return null;
    },

    async _handleEmployeeDetected(employeeId) {
        const now = Date.now();
        if (this.continuousMode && employeeId === this.lastRegisteredId && now - this.lastRegisteredTime < 9000) {
            console.log("Registro duplicado ignorado");
            this._scheduleAttempt();
            return;
        }

        // Primero, verificar con el servidor si ya registró en los últimos 90 segundos
        const checkResult = await this.rpc('/hr_attendance/check_duplicate', {
            employee_id: employeeId,
        });    

        if (checkResult && checkResult.blocked) {
            // Mostrar overlay amarillo con el mensaje
            this._showWarningIndicator(checkResult.message || 'Ya se registró');
            this._scheduleAttempt();
            return;
        }

        const result = await this.makeRpcWithGeolocation('manual_selection', {
            token: this.props.token,
            employee_id: employeeId,
            pin_code: false,
        });


        if (result && result.attendance) {
            this.lastRegisteredId = employeeId;
            this.lastRegisteredTime = now;

            const employeeName = result.employee ? result.employee.name : 'Empleado';
            const attendanceType = result.attendance.check_out ? 'Salida' : 'Entrada';
            const currentTime = new Date().toLocaleTimeString();

            if (this.continuousMode) {
                // Mostrar overlay grande
                this._showBigSuccessIndicator(employeeName, currentTime, attendanceType);
                this.attempts = 0;
                this._scheduleAttempt();
            } else {
                this.employeeData = result;
                this._stopDetection();
                this._stopStream(this.video);
                this.overlay.remove();
                this.switchDisplay('greet');
                if (this.cameraResolve) this.cameraResolve(true);
            }
        } else {
            console.error("Error en registro de asistencia:", result);
            this.attempts++;
            this._scheduleAttempt();
        }
    },

    // NUEVO: Mostrar overlay grande
    _showBigSuccessIndicator(name, time, type) {
        const bigOverlay = document.getElementById('big-success-overlay');
        if (!bigOverlay) return;
        document.getElementById('big-success-name').innerText = name;
        document.getElementById('big-success-time').innerText = `Hora: ${time}`;
        document.getElementById('big-success-type').innerText = type;
        bigOverlay.style.display = 'flex';
        setTimeout(() => {
            bigOverlay.style.display = 'none';
        }, 3000);
    },

    _showWarningIndicator(message) {
        const warningOverlay = document.getElementById('warning-overlay');
        if (!warningOverlay) return;
        document.getElementById('warning-message').innerText = message || 'Ya se registró';
        warningOverlay.style.display = 'flex';
        setTimeout(() => {
            warningOverlay.style.display = 'none';
        }, 3000);
    },

    _handleError(video, overlay, resolve) {
        this._stopDetection();
        if (video) this._stopStream(video);
        if (overlay) overlay.remove();
        if (resolve) resolve(false);
    },

    _stopStream(video) {
        if (video && video.srcObject) {
            video.srcObject.getTracks().forEach((track) => track.stop());
            if (video.parentNode) video.parentNode.removeChild(video);
        }
        this.stream = null;
        this.video = null;
    },

    _base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64.split(',')[1] || base64);
        const byteArrays = [];

        for (let offset = 0; offset < byteCharacters.length; offset += 512) {
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteArray = new Uint8Array([...slice].map((char) => char.charCodeAt(0)));
            byteArrays.push(byteArray);
        }

        return new Blob(byteArrays, { type: mimeType });
    },
});
