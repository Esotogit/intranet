// ===========================================
// INTRANET - JavaScript Base
// ===========================================

// Utilidades generales
const Utils = {
    // Formatear fecha
    formatDate(dateStr, options = {}) {
        const date = new Date(dateStr + 'T00:00:00');
        return date.toLocaleDateString('es-MX', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            ...options
        });
    },

    // Obtener lunes de la semana
    getMonday(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(d.setDate(diff));
    },

    // Formatear fecha para API
    formatDateISO(date) {
        return date.toISOString().split('T')[0];
    },

    // Mostrar notificación
    notify(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// API Helper
const API = {
    async get(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error('Error en la petición');
        return response.json();
    },

    async post(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la petición');
        }
        return response.json();
    },

    async patch(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la petición');
        }
        return response.json();
    },

    async delete(endpoint) {
        const response = await fetch(endpoint, { method: 'DELETE' });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la petición');
        }
        return response.json();
    }
};

// Inicialización global
document.addEventListener('DOMContentLoaded', () => {
    console.log('Intranet cargada correctamente');
});
