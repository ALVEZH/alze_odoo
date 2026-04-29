/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(FormController.prototype, {
    async saveButtonClicked() {
        const record = this.model.root;

        if (record.resModel === "hr.contract") {
            const outOfRange = record.data.salary_out_of_range;
            const forced = record.data.x_force_save;

            if (outOfRange && !forced) {
                const jobName = record.data.job_id ? record.data.job_id[1] : 'Sin puesto';
                const minSalary = parseFloat(record.data.x_salary_min) || 0;
                const maxSalary = parseFloat(record.data.x_salary_max) || 0;
                const currentWage = parseFloat(record.data.wage) || 0;

                const formatMoney = (value) => {
                    return new Intl.NumberFormat('es-MX', {
                        style: 'currency',
                        currency: 'MXN',
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                    }).format(value);
                };

                const minFormatted = formatMoney(minSalary);
                const maxFormatted = formatMoney(maxSalary);
                const wageFormatted = formatMoney(currentWage);

                // Construir el mensaje en texto plano con saltos de línea reales
                const messageBody = 
                    `El monto ingresado NO cumple con los parámetros permitidos.\n` +
                    `━━━━━━━━━━━━━━━━━━\n` +
                    `👤 Puesto: ${jobName}\n` +
                    `📊 Rango autorizado: ${minFormatted} – ${maxFormatted}\n` +
                    `💸 Monto capturado: ${wageFormatted}\n` +
                    `━━━━━━━━━━━━━━━━━━\n` +
                    `⚠️ Puedes mantener el monto o corregirlo.`;

                this.env.services.dialog.add(ConfirmationDialog, {
                    title: _t("🚨 ATENCIÓN OBLIGATORIA 🚨"),
                    body: messageBody,
                    confirmLabel: _t("Aceptar"),
                    cancelLabel: _t("Corregir"),
                    confirm: async () => {
                        await record.update({ x_force_save: true });
                        await record.save();
                    },
                    cancel: () => {},
                });
                return false;
            }
        }
        return super.saveButtonClicked(...arguments);
    },
});