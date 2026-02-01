/**
 * PWA API Client for Verbrauchstracker
 */
const PWA = {
    API_BASE: '/api/v1',
    STORAGE_KEY: 'pwa_api_key',

    // Storage
    getApiKey() {
        return localStorage.getItem(this.STORAGE_KEY);
    },

    setApiKey(key) {
        localStorage.setItem(this.STORAGE_KEY, key);
    },

    clearApiKey() {
        localStorage.removeItem(this.STORAGE_KEY);
    },

    // API Helpers
    async request(endpoint, options = {}) {
        const apiKey = this.getApiKey();
        if (!apiKey && !options.skipAuth) {
            const error = new Error('No API key');
            error.status = 401;
            throw error;
        }

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (apiKey && !options.skipAuth) {
            headers['X-API-Key'] = apiKey;
        }

        const response = await fetch(this.API_BASE + endpoint, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = new Error(response.statusText || 'Request failed');
            error.status = response.status;
            try {
                const data = await response.json();
                error.message = data.error || error.message;
            } catch (e) {
                // Ignore JSON parse errors
            }
            throw error;
        }

        return response.json();
    },

    async validateApiKey(key) {
        try {
            const response = await fetch(this.API_BASE + '/meters', {
                headers: {
                    'X-API-Key': key
                }
            });
            return response.ok;
        } catch (e) {
            return false;
        }
    },

    // API Methods
    async getMeters() {
        return this.request('/meters');
    },

    async getMeter(meterId) {
        return this.request(`/meters/${meterId}`);
    },

    async getLatestReading(meterId) {
        return this.request(`/meters/${meterId}/latest`);
    },

    async getMeterReadings(meterId, limit = 10) {
        return this.request(`/meters/${meterId}/readings?limit=${limit}`);
    },

    async createReading(meterId, date, value) {
        return this.request('/readings', {
            method: 'POST',
            body: JSON.stringify({
                meter_id: meterId,
                reading_date: date,
                value: value
            })
        });
    },

    // UI Helpers
    showLoading() {
        const el = document.getElementById('loading');
        if (el) el.classList.remove('hidden');
        const content = document.getElementById('content');
        if (content) content.classList.add('hidden');
    },

    hideLoading() {
        const el = document.getElementById('loading');
        if (el) el.classList.add('hidden');
        const content = document.getElementById('content');
        if (content) content.classList.remove('hidden');
    },

    showError(message) {
        const el = document.getElementById('error');
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    hideError() {
        const el = document.getElementById('error');
        if (el) el.classList.add('hidden');
    },

    // Formatting
    formatNumber(value) {
        if (value === null || value === undefined) return '-';
        // German number format: 1.234,56
        return value.toLocaleString('de-DE', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    },

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};
