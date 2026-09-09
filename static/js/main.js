// ==========================================
// OdontoCare - Main JavaScript
// ==========================================

// Auto-hide toasts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards';
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    });

    // Sidebar toggle for mobile
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        // Create overlay for mobile sidebar
        let overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);

        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
            document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';
        });

        // Close sidebar when clicking overlay
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        });

        // Close sidebar with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
});

// Toggle password visibility
function togglePassword() {
    const passwordInput = document.querySelector('#id_password');
    const toggleIcon = document.getElementById('toggleIcon');
    
    if (passwordInput && toggleIcon) {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleIcon.classList.remove('fa-eye');
            toggleIcon.classList.add('fa-eye-slash');
        } else {
            passwordInput.type = 'password';
            toggleIcon.classList.remove('fa-eye-slash');
            toggleIcon.classList.add('fa-eye');
        }
    }
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==========================================
// Control de Concurrencia (Lock Management)
// ==========================================
// Estrategia:
// - NO se adquiere lock al cargar la página (solo al empezar a editar)
// - Lock se adquiere cuando el usuario modifica cualquier campo del formulario
// - Lock se renueva mientras el usuario sigue editando
// - Lock se libera tras 2 minutos de inactividad o al salir de la página
// - Se verifica cada 30s si OTRO usuario tomó el lock (advertencia)

document.addEventListener('DOMContentLoaded', function() {
    const editForms = document.querySelectorAll('form[data-object-type]');

    editForms.forEach(form => {
        const objectType = form.dataset.objectType;
        const objectId = form.dataset.objectId;

        if (!objectType || !objectId) return;

        const banner = document.getElementById('concurrencyBanner');
        const messageEl = document.getElementById('concurrencyMessage');
        let lockAcquired = false;
        let lockInterval = null;
        let inactivityTimer = null;

        // Adquirir lock solo cuando el usuario edita un campo
        const editFields = form.querySelectorAll(
            'input:not([type="hidden"]):not([name="csrfmiddlewaretoken"]):not([name="object_version"]), ' +
            'textarea, select, .checkbox-input'
        );

        editFields.forEach(field => {
            field.addEventListener('change', function() { adquirirLock(); });
            field.addEventListener('input', function() { adquirirLock(); });
            field.addEventListener('focus', function() { adquirirLock(); });
        });

        function adquirirLock() {
            if (!lockAcquired) {
                lockAcquired = true;
                // Adquirir lock
                fetch('/api/lock/renew/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({
                        model_name: objectType,
                        object_id: parseInt(objectId),
                    }),
                }).catch(() => {});

                // Mostrar banner
                if (banner) {
                    banner.style.display = 'flex';
                    banner.className = 'concurrency-banner';
                    messageEl.textContent = '🔒 Tienes el bloqueo de edición activo.';
                }

                // Renovar lock cada 2 minutos mientras edita
                lockInterval = setInterval(() => {
                    fetch('/api/lock/renew/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken(),
                        },
                        body: JSON.stringify({
                            model_name: objectType,
                            object_id: parseInt(objectId),
                        }),
                    }).catch(() => {});
                }, 120000);
            }

            // Reiniciar timer de inactividad
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(() => {
                // 2 minutos sin editar → liberar lock
                liberarLock();
            }, 120000);
        }

        function liberarLock() {
            if (lockAcquired) {
                lockAcquired = false;
                clearInterval(lockInterval);
                lockInterval = null;
                clearTimeout(inactivityTimer);
                releaseLock(objectType, objectId);
                if (banner) {
                    banner.style.display = 'none';
                }
            }
        }

        // Verificar si otro usuario tomó el lock (cada 30 segundos)
        setInterval(() => {
            fetch(`/api/lock/check/?model_name=${objectType}&object_id=${objectId}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(r => r.json())
            .then(data => {
                if (data.locked && data.locked_by_other) {
                    if (banner) {
                        banner.style.display = 'flex';
                        banner.className = 'concurrency-banner warning';
                        messageEl.textContent = `⚠️ Este registro está siendo editado por ${data.locker_name}. Edita con precaución.`;
                    }
                } else if (!data.locked && !lockAcquired) {
                    if (banner) {
                        banner.style.display = 'none';
                    }
                }
                // Si lockAcquired=true y no hay otro, el banner ya se mostró
            })
            .catch(() => {});
        }, 30000);

        // Liberar lock al cerrar/navegar
        window.addEventListener('beforeunload', function() {
            liberarLock();
        });

        // Liberar lock al hacer clic en "Cerrar Sesión"
        document.querySelectorAll('a[href*="logout"]').forEach(btn => {
            btn.addEventListener('click', function() {
                liberarLock();
            });
        });

        // Botones de cancelar/volver liberan el lock
        form.querySelectorAll('.btn-secondary, .btn-cancel').forEach(btn => {
            btn.addEventListener('click', function(e) {
                liberarLock();
            });
        });

        function releaseLock(model, objId) {
            fetch(`/api/lock/release/?model_name=${model}&object_id=${objId}`, {
                method: 'GET',
                keepalive: true,
            }).catch(() => {});
        }

        function getCSRFToken() {
            const input = document.querySelector('[name=csrfmiddlewaretoken]');
            return input ? input.value : '';
        }
    });
});
