/**
 * Medicine Reminder - Main Application JavaScript
 * React-like component management with vanilla JS
 */

// ============ Application State ============
const AppState = {
    user: null,
    medicines: [],
    reminders: [],
    adherence: { score: 0, total: 0, taken: 0 },
    notifications: [],
    isLoading: false,
    
    listeners: [],
    
    subscribe(callback) {
        this.listeners.push(callback);
        return () => {
            this.listeners = this.listeners.filter(l => l !== callback);
        };
    },
    
    notify() {
        this.listeners.forEach(callback => callback(this));
    },
    
    update(newState) {
        Object.assign(this, newState);
        this.notify();
    }
};

// ============ API Service ============
const API = {
    baseUrl: '',
    
    async request(endpoint, options = {}) {
        const response = await fetch(this.baseUrl + endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return response.json();
    },
    
    async getMedicines() {
        return this.request('/api/medicines');
    },
    
    async getTodayReminders() {
        return this.request('/api/reminders/today');
    },
    
    async getAdherence(days = 30) {
        return this.request(`/api/adherence?days=${days}`);
    },
    
    async getRiskPrediction() {
        return this.request('/api/prediction/risk');
    },
    
    async getHealth() {
        return this.request('/api/health');
    }
};

// ============ UI Components ============
const Components = {
    
    // Toast Notification Component
    Toast: {
        container: null,
        
        init() {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'fixed top-20 right-4 z-50 space-y-2 max-w-sm';
            document.body.appendChild(this.container);
        },
        
        show(message, type = 'info', duration = 5000) {
            const toast = document.createElement('div');
            toast.className = `toast p-4 rounded-xl shadow-lg flex items-center gap-3 animate__animated animate__slideInRight
                ${type === 'success' ? 'bg-green-50 border-l-4 border-green-500 text-green-700' : ''}
                ${type === 'error' ? 'bg-red-50 border-l-4 border-red-500 text-red-700' : ''}
                ${type === 'warning' ? 'bg-yellow-50 border-l-4 border-yellow-500 text-yellow-700' : ''}
                ${type === 'info' ? 'bg-blue-50 border-l-4 border-blue-500 text-blue-700' : ''}`;
            
            const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
            
            toast.innerHTML = `
                <span class="text-xl">${icons[type]}</span>
                <p class="flex-1 font-medium">${message}</p>
                <button class="text-gray-400 hover:text-gray-600 close-toast">✕</button>
            `;
            
            toast.querySelector('.close-toast').addEventListener('click', () => {
                this.hide(toast);
            });
            
            this.container.appendChild(toast);
            
            if (duration > 0) {
                setTimeout(() => this.hide(toast), duration);
            }
            
            return toast;
        },
        
        hide(toast) {
            toast.classList.remove('animate__slideInRight');
            toast.classList.add('animate__slideOutRight');
            setTimeout(() => toast.remove(), 500);
        },
        
        success(message) { return this.show(message, 'success'); },
        error(message) { return this.show(message, 'error'); },
        warning(message) { return this.show(message, 'warning'); },
        info(message) { return this.show(message, 'info'); }
    },
    
    // Modal Component
    Modal: {
        overlay: null,
        
        init() {
            this.overlay = document.createElement('div');
            this.overlay.className = 'modal-overlay';
            this.overlay.innerHTML = '<div class="modal"></div>';
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay) this.close();
            });
            document.body.appendChild(this.overlay);
        },
        
        open(content) {
            const modal = this.overlay.querySelector('.modal');
            modal.innerHTML = content;
            this.overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        },
        
        close() {
            this.overlay.classList.remove('active');
            document.body.style.overflow = '';
        },
        
        confirm(title, message, onConfirm) {
            this.open(`
                <div class="p-6">
                    <div class="text-center mb-6">
                        <div class="text-5xl mb-4">⚠️</div>
                        <h3 class="text-xl font-bold text-gray-900">${title}</h3>
                        <p class="text-gray-600 mt-2">${message}</p>
                    </div>
                    <div class="flex gap-3">
                        <button class="btn btn-secondary flex-1 cancel-btn">Cancel</button>
                        <button class="btn btn-danger flex-1 confirm-btn">Confirm</button>
                    </div>
                </div>
            `);
            
            this.overlay.querySelector('.cancel-btn').addEventListener('click', () => this.close());
            this.overlay.querySelector('.confirm-btn').addEventListener('click', () => {
                onConfirm();
                this.close();
            });
        }
    },
    
    // Loading Spinner
    Loader: {
        show(target) {
            const loader = document.createElement('div');
            loader.className = 'loader-overlay absolute inset-0 bg-white/80 flex items-center justify-center z-10';
            loader.innerHTML = `
                <div class="flex flex-col items-center">
                    <div class="spinner w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                    <p class="mt-3 text-gray-600 font-medium">Loading...</p>
                </div>
            `;
            target.style.position = 'relative';
            target.appendChild(loader);
            return loader;
        },
        
        hide(loader) {
            if (loader && loader.parentNode) {
                loader.remove();
            }
        }
    },
    
    // Progress Ring Component
    ProgressRing: {
        create(percent, size = 120, strokeWidth = 10, color = '#4F46E5') {
            const radius = (size - strokeWidth) / 2;
            const circumference = radius * 2 * Math.PI;
            const offset = circumference - (percent / 100) * circumference;
            
            return `
                <div class="circular-progress" style="width: ${size}px; height: ${size}px;">
                    <svg width="${size}" height="${size}">
                        <circle
                            stroke="#E5E7EB"
                            fill="transparent"
                            stroke-width="${strokeWidth}"
                            r="${radius}"
                            cx="${size/2}"
                            cy="${size/2}"
                        />
                        <circle
                            stroke="${color}"
                            fill="transparent"
                            stroke-width="${strokeWidth}"
                            stroke-linecap="round"
                            r="${radius}"
                            cx="${size/2}"
                            cy="${size/2}"
                            style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${offset}; transition: stroke-dashoffset 1s ease;"
                        />
                    </svg>
                    <div class="value">${percent}%</div>
                </div>
            `;
        }
    },
    
    // Countdown Timer
    Countdown: {
        create(targetTime, onComplete) {
            const container = document.createElement('div');
            container.className = 'countdown text-center';
            
            const update = () => {
                const now = new Date();
                const [hours, minutes] = targetTime.split(':');
                const target = new Date();
                target.setHours(parseInt(hours), parseInt(minutes), 0);
                
                if (target < now) {
                    target.setDate(target.getDate() + 1);
                }
                
                const diff = target - now;
                const h = Math.floor(diff / 3600000);
                const m = Math.floor((diff % 3600000) / 60000);
                const s = Math.floor((diff % 60000) / 1000);
                
                container.innerHTML = `
                    <div class="flex justify-center gap-4">
                        <div class="bg-primary-100 rounded-xl p-3 min-w-16">
                            <div class="text-2xl font-bold text-primary-700">${h.toString().padStart(2, '0')}</div>
                            <div class="text-xs text-primary-500">Hours</div>
                        </div>
                        <div class="bg-primary-100 rounded-xl p-3 min-w-16">
                            <div class="text-2xl font-bold text-primary-700">${m.toString().padStart(2, '0')}</div>
                            <div class="text-xs text-primary-500">Mins</div>
                        </div>
                        <div class="bg-primary-100 rounded-xl p-3 min-w-16">
                            <div class="text-2xl font-bold text-primary-700">${s.toString().padStart(2, '0')}</div>
                            <div class="text-xs text-primary-500">Secs</div>
                        </div>
                    </div>
                `;
                
                if (diff <= 0 && onComplete) {
                    onComplete();
                }
            };
            
            update();
            setInterval(update, 1000);
            
            return container;
        }
    },
    
    // Stat Card
    StatCard: {
        create(icon, label, value, color = 'blue') {
            return `
                <div class="bg-white rounded-xl shadow-lg p-5 card-hover">
                    <div class="flex items-center">
                        <div class="p-3 bg-${color}-100 rounded-xl">
                            <span class="text-2xl">${icon}</span>
                        </div>
                        <div class="ml-3">
                            <p class="text-gray-500 text-xs">${label}</p>
                            <p class="text-2xl font-bold text-gray-900">${value}</p>
                        </div>
                    </div>
                </div>
            `;
        }
    }
};

// ============ Utilities ============
const Utils = {
    // Format time
    formatTime(time) {
        const [hours, minutes] = time.split(':');
        const h = parseInt(hours);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const hour12 = h % 12 || 12;
        return `${hour12}:${minutes} ${ampm}`;
    },
    
    // Format date
    formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });
    },
    
    // Time until
    timeUntil(time) {
        const now = new Date();
        const [hours, minutes] = time.split(':');
        const target = new Date();
        target.setHours(parseInt(hours), parseInt(minutes), 0);
        
        if (target < now) {
            return 'Past';
        }
        
        const diff = Math.floor((target - now) / 60000);
        if (diff < 60) return `in ${diff}m`;
        return `in ${Math.floor(diff / 60)}h ${diff % 60}m`;
    },
    
    // Debounce
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Generate unique ID
    uid() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },
    
    // Local storage helpers
    storage: {
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch {
                return defaultValue;
            }
        },
        set(key, value) {
            localStorage.setItem(key, JSON.stringify(value));
        },
        remove(key) {
            localStorage.removeItem(key);
        }
    },
    
    // Get greeting based on time
    getGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return '🌅 Good Morning';
        if (hour < 17) return '☀️ Good Afternoon';
        if (hour < 21) return '🌆 Good Evening';
        return '🌙 Good Night';
    }
};

// ============ Form Validation ============
const Validator = {
    rules: {
        required: (value) => value.trim() !== '' || 'This field is required',
        email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || 'Invalid email address',
        minLength: (min) => (value) => value.length >= min || `Minimum ${min} characters required`,
        maxLength: (max) => (value) => value.length <= max || `Maximum ${max} characters allowed`,
        phone: (value) => /^[\d\s\-+()]{10,}$/.test(value) || 'Invalid phone number',
        time: (value) => /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(value) || 'Invalid time format',
        match: (field) => (value, form) => value === form.querySelector(`[name="${field}"]`).value || 'Fields do not match'
    },
    
    validate(form) {
        const errors = [];
        const inputs = form.querySelectorAll('[data-validate]');
        
        inputs.forEach(input => {
            const rules = input.dataset.validate.split('|');
            const value = input.value;
            
            rules.forEach(rule => {
                let validator;
                let param;
                
                if (rule.includes(':')) {
                    [rule, param] = rule.split(':');
                    validator = this.rules[rule](param);
                } else {
                    validator = this.rules[rule];
                }
                
                if (validator) {
                    const result = validator(value, form);
                    if (result !== true) {
                        errors.push({ field: input.name, message: result });
                        input.classList.add('border-red-500');
                    } else {
                        input.classList.remove('border-red-500');
                    }
                }
            });
        });
        
        return errors;
    }
};

// ============ Notification Handler ============
const Notifications = {
    permission: 'default',
    
    async init() {
        if ('Notification' in window) {
            this.permission = await Notification.requestPermission();
        }
    },
    
    send(title, body, icon = '💊') {
        if (this.permission === 'granted') {
            new Notification(title, { body, icon: '/static/icon.png', badge: icon });
        }
    },
    
    scheduleReminder(time, medicine) {
        const now = new Date();
        const [hours, minutes] = time.split(':');
        const target = new Date();
        target.setHours(parseInt(hours), parseInt(minutes), 0);
        
        if (target > now) {
            const delay = target - now;
            setTimeout(() => {
                this.send(
                    '💊 Medicine Reminder',
                    `Time to take ${medicine.name} (${medicine.dosage})`
                );
                // Play sound
                this.playAlarm();
            }, delay);
        }
    },
    
    playAlarm() {
        const audio = new Audio('/static/alarm.mp3');
        audio.play().catch(() => {
            // Audio autoplay was prevented
            console.log('Audio playback prevented');
        });
    }
};

// ============ Application Controller ============
const App = {
    async init() {
        console.log('💊 Medicine Reminder - Initializing...');
        
        // Initialize components
        Components.Toast.init();
        Components.Modal.init();
        
        // Initialize notifications
        await Notifications.init();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadData();
        
        // Setup auto-refresh
        setInterval(() => this.refreshReminders(), 60000);
        
        console.log('✅ Medicine Reminder - Ready');
    },
    
    setupEventListeners() {
        // Form submissions
        document.querySelectorAll('form[data-ajax]').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleFormSubmit(form);
            });
        });
        
        // Delete confirmations
        document.querySelectorAll('[data-delete]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                Components.Modal.confirm(
                    'Delete Item',
                    'Are you sure you want to delete this? This action cannot be undone.',
                    () => {
                        btn.closest('form').submit();
                    }
                );
            });
        });
        
        // Time input formatting
        document.querySelectorAll('input[type="time"]').forEach(input => {
            input.addEventListener('change', (e) => {
                const display = input.parentElement.querySelector('.time-display');
                if (display) {
                    display.textContent = Utils.formatTime(e.target.value);
                }
            });
        });
        
        // Dynamic form fields
        document.querySelectorAll('[data-add-field]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.addFormField(btn.dataset.addField, btn.dataset.template);
            });
        });
        
        // Real-time validation
        document.querySelectorAll('input[data-validate]').forEach(input => {
            input.addEventListener('blur', () => {
                const form = input.closest('form');
                Validator.validate(form);
            });
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + N = New medicine
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                window.location.href = '/medicines/add';
            }
            // Escape = Close modal
            if (e.key === 'Escape') {
                Components.Modal.close();
            }
        });
    },
    
    async loadData() {
        try {
            const [medicines, reminders, adherence] = await Promise.all([
                API.getMedicines().catch(() => ({ medicines: [] })),
                API.getTodayReminders().catch(() => ({ reminders: [] })),
                API.getAdherence().catch(() => ({ score: 0, total: 0, taken: 0 }))
            ]);
            
            AppState.update({
                medicines: medicines.medicines || [],
                reminders: reminders.reminders || [],
                adherence: adherence
            });
            
            // Schedule notifications for reminders
            AppState.reminders.forEach(reminder => {
                Notifications.scheduleReminder(reminder.reminder_time, reminder);
            });
            
        } catch (error) {
            console.error('Failed to load data:', error);
        }
    },
    
    async refreshReminders() {
        try {
            const data = await API.getTodayReminders();
            AppState.update({ reminders: data.reminders || [] });
        } catch (error) {
            console.error('Failed to refresh reminders');
        }
    },
    
    async handleFormSubmit(form) {
        const errors = Validator.validate(form);
        
        if (errors.length > 0) {
            Components.Toast.error(errors[0].message);
            return;
        }
        
        const loader = Components.Loader.show(form);
        
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: form.method,
                body: formData
            });
            
            if (response.ok) {
                Components.Toast.success('Saved successfully!');
                if (form.dataset.redirect) {
                    window.location.href = form.dataset.redirect;
                }
            } else {
                throw new Error('Form submission failed');
            }
        } catch (error) {
            Components.Toast.error('Something went wrong. Please try again.');
        } finally {
            Components.Loader.hide(loader);
        }
    },
    
    addFormField(containerId, templateId) {
        const container = document.getElementById(containerId);
        const template = document.getElementById(templateId);
        
        if (container && template) {
            const clone = template.content.cloneNode(true);
            container.appendChild(clone);
            
            // Add remove button functionality
            const newField = container.lastElementChild;
            const removeBtn = newField.querySelector('[data-remove]');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => newField.remove());
            }
        }
    }
};

// ============ Dashboard Specific Functions ============
const Dashboard = {
    init() {
        this.renderStats();
        this.setupReminderActions();
        this.initializeCharts();
    },
    
    renderStats() {
        const statsContainer = document.getElementById('dashboard-stats');
        if (!statsContainer) return;
        
        const { adherence, medicines, reminders } = AppState;
        
        statsContainer.innerHTML = `
            ${Components.StatCard.create('💊', 'Medicines', medicines.length, 'blue')}
            ${Components.StatCard.create('⏰', 'Today', reminders.length, 'green')}
            ${Components.StatCard.create('📊', 'Adherence', `${adherence.score}%`, adherence.score >= 80 ? 'green' : 'yellow')}
        `;
    },
    
    setupReminderActions() {
        document.querySelectorAll('.take-medicine-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const form = btn.closest('form');
                const loader = Components.Loader.show(btn);
                
                try {
                    await form.submit();
                    Components.Toast.success('Medicine marked as taken! 💪');
                } catch {
                    Components.Toast.error('Failed to update');
                } finally {
                    Components.Loader.hide(loader);
                }
            });
        });
    },
    
    initializeCharts() {
        const chartContainer = document.getElementById('adherence-chart');
        if (chartContainer) {
            chartContainer.innerHTML = Components.ProgressRing.create(
                AppState.adherence.score,
                150,
                12,
                AppState.adherence.score >= 80 ? '#10B981' : AppState.adherence.score >= 50 ? '#F59E0B' : '#EF4444'
            );
        }
    }
};

// ============ Initialize on DOM Ready ============
document.addEventListener('DOMContentLoaded', () => {
    App.init();
    
    // Initialize page-specific functionality
    if (document.getElementById('dashboard-page')) {
        Dashboard.init();
    }
});

// Export for use in templates
window.MedRemind = {
    App,
    API,
    Components,
    Utils,
    AppState,
    Dashboard
};
