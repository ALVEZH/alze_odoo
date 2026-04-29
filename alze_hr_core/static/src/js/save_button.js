odoo.define('alze_hr_core.save_button', [], function (require) {
    "use strict";

    function addBigSaveButton() {
        var $saveBtn = $('.o_form_button_save');
        
        if ($saveBtn.length && !$('#o_alze_big_save_btn').length) {
            // Eliminamos márgenes que empujan el contenido y usamos 'd-none d-md-inline-block' 
            // para que en móviles muy pequeños no desplace el breadcrumb.
            var $bigBtn = $('<button id="o_alze_big_save_btn" class="btn btn-primary shadow-sm" style="font-weight: bold; white-space: nowrap; margin: 0 5px;">💾 Guardar Cambios</button>');
            
            $bigBtn.on('click', function (e) {
                e.preventDefault();
                $saveBtn.click();
            });

            // IMPORTANTE: En lugar de .append() al padre, usamos .after() 
            // Esto lo mantiene pegado al botón de guardado original y no altera el flexbox del padre
            $saveBtn.after($bigBtn);

            // Ajuste visual: Odoo 17 usa Flexbox en el control panel. 
            // Forzamos al contenedor de botones a no ocupar más espacio del necesario.
            $saveBtn.parent().css({
                'display': 'flex',
                'align-items': 'center',
                'flex-shrink': '0'
            });
        }
    }

    $(document).ready(function () {
        addBigSaveButton();
        var observer = new MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length) {
                    addBigSaveButton();
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    });
});