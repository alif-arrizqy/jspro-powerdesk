/**
 * Modern JSPro PowerDesk Application
 * Interactive and responsive web application for monitoring power systems
 */

class PowerDeskApp {
    constructor() {
        this.dataUpdateInterval = 5000; // 5 seconds
        this.animationDelay = 100;
        this.currentData = {};
        this.charts = {};
        this.websocket = null;
        this.isConnected = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.setupDateTime();
        this.setupDataUpdates();
        this.setupWebSocket();
        this.setupAnimations();
        this.initializeSidebar();
        this.initializeTheme();  // Initialize theme on app start
        this.hideLoadingSpinner();
    }

    initializeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        
        // Initialize sidebar state based on screen size
        if (window.innerWidth <= 1024) {
            sidebar.classList.add('hidden');
            mainContent.classList.remove('sidebar-open');
        } else {
            sidebar.classList.remove('hidden');
            mainContent.classList.remove('sidebar-open');
        }
    }

    setupEventListeners() {
        // Menu toggle
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        const closeSidebar = document.getElementById('closeSidebar');
        const mobileOverlay = document.getElementById('mobileSidebarOverlay');

        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        if (closeSidebar) {
            closeSidebar.addEventListener('click', () => {
                this.closeSidebar();
            });
        }

        if (mobileOverlay) {
            mobileOverlay.addEventListener('click', () => {
                this.closeSidebar();
            });
        }

        // Refresh button
        const refreshButton = document.getElementById('refreshData');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                this.refreshAllData();
            });
        }

        // Theme toggle - Fixed ID matching
        const themeToggle = document.getElementById('toggleTheme');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Responsive handling
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        // Handle clicks outside sidebar on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                const menuToggle = document.getElementById('menuToggle');
                
                if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                    this.closeSidebar();
                }
            }
        });

        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSidebar();
            }
        });
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        const mobileOverlay = document.getElementById('mobileSidebarOverlay');
        const hamburger = document.getElementById('menuToggle');

        if (window.innerWidth <= 768) {
            // Mobile behavior
            sidebar.classList.toggle('active');
            mobileOverlay.classList.toggle('active');
            hamburger.classList.toggle('active');
        } else {
            // Desktop behavior
            sidebar.classList.toggle('hidden');
            mainContent.classList.toggle('sidebar-collapsed');
        }
    }

    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        const mobileOverlay = document.getElementById('mobileSidebarOverlay');
        const hamburger = document.getElementById('menuToggle');

        if (window.innerWidth <= 768) {
            sidebar.classList.remove('active');
            mobileOverlay.classList.remove('active');
            hamburger.classList.remove('active');
        } else {
            sidebar.classList.add('hidden');
            mainContent.classList.add('sidebar-collapsed');
        }
    }

    toggleTheme() {
        const body = document.body;
        const themeToggle = document.getElementById('toggleTheme');
        const themeIcon = themeToggle?.querySelector('i');
        
        // Toggle theme class
        const isDarkMode = body.classList.toggle('dark-theme');
        
        // Update icon
        if (themeIcon) {
            if (isDarkMode) {
                themeIcon.className = 'fas fa-sun';
                themeToggle.setAttribute('title', 'Switch to Light Mode');
            } else {
                themeIcon.className = 'fas fa-moon';
                themeToggle.setAttribute('title', 'Switch to Dark Mode');
            }
        }
        
        // Save preference to localStorage
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        
        // Apply theme to all charts if they exist
        this.updateChartsTheme(isDarkMode);
        
        // Trigger custom event for theme change
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { isDarkMode, theme: isDarkMode ? 'dark' : 'light' } 
        }));
        
        console.log(`Theme switched to: ${isDarkMode ? 'Dark' : 'Light'} mode`);
    }

    // Initialize theme from localStorage or system preference
    initializeTheme() {
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const shouldUseDarkTheme = savedTheme === 'dark' || (!savedTheme && systemPrefersDark);
        
        const body = document.body;
        const themeToggle = document.getElementById('toggleTheme');
        const themeIcon = themeToggle?.querySelector('i');
        
        if (shouldUseDarkTheme) {
            body.classList.add('dark-theme');
            if (themeIcon) {
                themeIcon.className = 'fas fa-sun';
                themeToggle.setAttribute('title', 'Switch to Light Mode');
            }
        } else {
            body.classList.remove('dark-theme');
            if (themeIcon) {
                themeIcon.className = 'fas fa-moon';
                themeToggle.setAttribute('title', 'Switch to Dark Mode');
            }
        }
        
        // Update charts theme if they exist
        this.updateChartsTheme(shouldUseDarkTheme);
    }

    // Update charts theme colors
    updateChartsTheme(isDarkMode) {
        if (typeof Chart !== 'undefined' && Object.keys(this.charts).length > 0) {
            const textColor = isDarkMode ? '#e2e8f0' : '#374151';
            const gridColor = isDarkMode ? '#374151' : '#e5e7eb';
            
            Object.values(this.charts).forEach(chart => {
                if (chart && chart.options) {
                    // Update text colors
                    if (chart.options.scales) {
                        Object.keys(chart.options.scales).forEach(scaleKey => {
                            const scale = chart.options.scales[scaleKey];
                            if (scale.ticks) scale.ticks.color = textColor;
                            if (scale.grid) scale.grid.color = gridColor;
                        });
                    }
                    
                    // Update legend colors
                    if (chart.options.plugins && chart.options.plugins.legend) {
                        chart.options.plugins.legend.labels = {
                            ...chart.options.plugins.legend.labels,
                            color: textColor
                        };
                    }
                    
                    chart.update('none');
                }
            });
        }
    }

    setupNavigation() {
        // Setup submenu toggles
        const submenuToggles = document.querySelectorAll('.submenu-toggle');
        
        submenuToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                const parent = toggle.closest('.has-submenu');
                const isOpen = parent.classList.contains('open');
                
                // Close all other submenus
                document.querySelectorAll('.has-submenu.open').forEach(item => {
                    if (item !== parent) {
                        item.classList.remove('open');
                    }
                });
                
                // Toggle current submenu
                parent.classList.toggle('open');
                
                // Update aria-expanded
                toggle.setAttribute('aria-expanded', !isOpen);
            });
        });

        // Set active states based on current page
        this.setActiveNavigation();
    }

    setActiveNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
                link.classList.add('active');
                
                // Open parent submenu if exists
                const parentSubmenu = link.closest('.has-submenu');
                if (parentSubmenu) {
                    parentSubmenu.classList.add('open');
                    const toggle = parentSubmenu.querySelector('.submenu-toggle');
                    if (toggle) {
                        toggle.setAttribute('aria-expanded', 'true');
                    }
                }
            }
        });
    }

    updateSiteStatus() {
        const statusElement = document.querySelector('.site-status');
        const statusIndicator = document.querySelector('.status-indicator');
        
        if (statusElement && statusIndicator) {
            if (this.isConnected) {
                statusElement.classList.remove('offline');
                statusElement.classList.add('online');
                statusElement.querySelector('.status-text').textContent = 'Online';
            } else {
                statusElement.classList.remove('online');
                statusElement.classList.add('offline');
                statusElement.querySelector('.status-text').textContent = 'Offline';
            }
        }
    }

    handleResize() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        const mobileOverlay = document.getElementById('mobileSidebarOverlay');
        
        if (window.innerWidth <= 768) {
            // Mobile mode
            sidebar.classList.remove('hidden');
            mainContent.classList.remove('sidebar-collapsed');
            
            // Close sidebar on mobile
            if (!sidebar.classList.contains('active')) {
                mobileOverlay.classList.remove('active');
            }
        } else {
            // Desktop mode
            sidebar.classList.remove('active');
            mobileOverlay.classList.remove('active');
            document.getElementById('menuToggle').classList.remove('active');
        }
    }

    setupDateTime() {
        const updateDateTime = () => {
            const now = new Date();
            const options = {
                timeZone: 'Asia/Jakarta',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            };
            
            const formatted = now.toLocaleString('en-GB', options);
            const timeElement = document.getElementById('current-time');
            if (timeElement) {
                timeElement.textContent = formatted;
            }
        };

        updateDateTime();
        setInterval(updateDateTime, 1000);
    }

    setupDataUpdates() {
        // Start periodic data updates
        this.startDataUpdates();
    }

    startDataUpdates() {
        this.dataUpdateTimer = setInterval(() => {
            this.updateDeviceData();
        }, this.dataUpdateInterval);
    }

    stopDataUpdates() {
        if (this.dataUpdateTimer) {
            clearInterval(this.dataUpdateTimer);
        }
    }

    async updateDeviceData() {
        try {
            const endpoints = [
                '/api/device-information',
                '/api/lvd-realtime',
                '/api/scc-realtime',
                '/api/battery-realtime'
            ];

            const promises = endpoints.map(endpoint => 
                fetch(endpoint)
                    .then(response => response.json())
                    .catch(error => {
                        console.warn(`Failed to fetch ${endpoint}:`, error);
                        return null;
                    })
            );

            const results = await Promise.allSettled(promises);
            
            results.forEach((result, index) => {
                if (result.status === 'fulfilled' && result.value) {
                    this.processData(endpoints[index], result.value);
                }
            });

        } catch (error) {
            console.error('Error updating device data:', error);
        }
    }

    processData(endpoint, data) {
        switch (endpoint) {
            case '/api/device-information':
                this.updateDeviceInfo(data);
                break;
            case '/api/lvd-realtime':
                this.updateLVDData(data);
                break;
            case '/api/scc-realtime':
                this.updateSCCData(data);
                break;
            case '/api/battery-realtime':
                this.updateBatteryData(data);
                break;
        }
    }

    updateDeviceInfo(data) {
        const fields = [
            { id: 'scc-type', key: 'scc_type' },
            { id: 'disk-usage', key: 'disk_usage' },
            { id: 'datalog-length', key: 'datalog_length' }
        ];

        fields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element && data[field.key]) {
                this.animateValueUpdate(element, data[field.key]);
            }
        });
    }

    updateLVDData(data) {
        const fields = [
            { id: 'lvd-counter-heartbeat', key: 'counter_heartbeat', suffix: '' },
            { id: 'vsat-lvd', key: 'vsat_lvd' },
            { id: 'bts-lvd', key: 'bts_lvd' },
            { id: 'system-voltage', key: 'system_voltage', suffix: 'V' },
            { id: 'mcb1', key: 'mcb1_status' },
            { id: 'mcb2', key: 'mcb2_status' },
            { id: 'mcb3', key: 'mcb3_status' }
        ];

        fields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element && data[field.key] !== undefined) {
                let value = data[field.key];
                if (field.suffix) {
                    value = `${value} ${field.suffix}`;
                }
                this.animateValueUpdate(element, value);
                this.updateStatusIndicator(element, data[field.key]);
            }
        });
    }

    updateSCCData(data) {
        // Update SCC data for multiple SCCs
        for (let i = 1; i <= 3; i++) {
            const fields = [
                { id: `scc${i}-status`, key: `scc${i}_status` },
                { id: `scc${i}-counter-heartbeat`, key: `scc${i}_counter_heartbeat` },
                { id: `pv${i}-voltage`, key: `pv${i}_voltage`, suffix: 'V' },
                { id: `pv${i}-current`, key: `pv${i}_current`, suffix: 'A' },
                { id: `pv${i}-power`, key: `pv${i}_power`, suffix: 'W' },
                { id: `battery${i}-voltage`, key: `battery${i}_voltage`, suffix: 'V' },
                { id: `battery${i}-current`, key: `battery${i}_current`, suffix: 'A' },
                { id: `load${i}-voltage`, key: `load${i}_voltage`, suffix: 'V' },
                { id: `load${i}-current`, key: `load${i}_current`, suffix: 'A' }
            ];

            fields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element && data[field.key] !== undefined) {
                    let value = data[field.key];
                    if (field.suffix && typeof value === 'number') {
                        value = `${value.toFixed(2)} ${field.suffix}`;
                    }
                    this.animateValueUpdate(element, value);
                    this.updateStatusIndicator(element, data[field.key]);
                }
            });
        }
    }

    updateBatteryData(data) {
        const fields = [
            { id: 'battery-voltage', key: 'voltage', suffix: 'V' },
            { id: 'battery-current', key: 'current', suffix: 'A' },
            { id: 'battery-soc', key: 'soc', suffix: '%' },
            { id: 'battery-temperature', key: 'temperature', suffix: '°C' }
        ];

        fields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element && data[field.key] !== undefined) {
                let value = data[field.key];
                if (field.suffix && typeof value === 'number') {
                    value = `${value.toFixed(2)} ${field.suffix}`;
                }
                this.animateValueUpdate(element, value);
            }
        });
    }

    animateValueUpdate(element, newValue) {
        const currentValue = element.textContent;
        
        if (currentValue !== newValue) {
            element.style.opacity = '0.5';
            element.style.transform = 'scale(0.95)';
            
            setTimeout(() => {
                element.textContent = newValue;
                element.style.opacity = '1';
                element.style.transform = 'scale(1)';
                element.style.transition = 'all 0.3s ease';
            }, 150);
        }
    }

    updateStatusIndicator(element, value) {
        const statusClasses = ['status-active', 'status-inactive', 'status-danger', 'status-warning'];
        
        // Remove existing status classes
        statusClasses.forEach(className => {
            element.classList.remove(className);
        });

        // Add appropriate status class based on value
        if (typeof value === 'boolean') {
            element.classList.add(value ? 'status-active' : 'status-inactive');
        } else if (typeof value === 'string') {
            const lowerValue = value.toLowerCase();
            if (lowerValue.includes('active') || lowerValue.includes('on') || lowerValue.includes('normal')) {
                element.classList.add('status-active');
            } else if (lowerValue.includes('alarm') || lowerValue.includes('error') || lowerValue.includes('fault')) {
                element.classList.add('status-danger');
            } else if (lowerValue.includes('warning')) {
                element.classList.add('status-warning');
            } else {
                element.classList.add('status-inactive');
            }
        }
    }

    setupWebSocket() {
        if (typeof io !== 'undefined') {
            this.websocket = io();
            
            this.websocket.on('connect', () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.showConnectionStatus(true);
            });

            this.websocket.on('disconnect', () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.showConnectionStatus(false);
            });

            this.websocket.on('data_update', (data) => {
                this.processWebSocketData(data);
            });

            this.websocket.on('alert', (data) => {
                this.showAlert(data.message, data.type);
            });
        }
    }

    processWebSocketData(data) {
        // Process real-time data from WebSocket
        if (data.type === 'device_info') {
            this.updateDeviceInfo(data.data);
        } else if (data.type === 'lvd_data') {
            this.updateLVDData(data.data);
        } else if (data.type === 'scc_data') {
            this.updateSCCData(data.data);
        } else if (data.type === 'battery_data') {
            this.updateBatteryData(data.data);
        }
    }

    showConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = connected ? 'status-active' : 'status-inactive';
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.querySelector('.alert-container');
        if (!alertContainer) return;

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show modern-alert`;
        alertDiv.innerHTML = `
            <i class="fas fa-${type === 'danger' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <strong>${type.charAt(0).toUpperCase() + type.slice(1)}!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        alertContainer.appendChild(alertDiv);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    setupAnimations() {
        // Animate elements on page load
        const animatedElements = document.querySelectorAll('.stats-card, .modern-card');
        
        animatedElements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                element.style.transition = 'all 0.6s ease';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * this.animationDelay);
        });
    }

    handleResize() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (window.innerWidth > 1024) {
            sidebar.classList.remove('hidden');
            mainContent.classList.remove('sidebar-open');
        } else {
            sidebar.classList.add('hidden');
            mainContent.classList.remove('sidebar-open');
        }
    }

    refreshAllData() {
        const refreshButton = document.getElementById('refreshData');
        const refreshText = refreshButton?.querySelector('.d-none.d-md-inline');
        
        if (refreshButton) {
            const icon = refreshButton.querySelector('i');
            
            // Add spinning animation and disable button
            refreshButton.disabled = true;
            icon.style.animation = 'spin 1s linear infinite';
            
            if (refreshText) {
                refreshText.textContent = 'Refreshing...';
            }
            
            // Update button styling
            refreshButton.classList.add('btn-loading');
        }

        console.log('🔄 Refreshing all data...');
        
        // Perform actual data refresh
        Promise.all([
            this.updateDeviceData(),
            this.updateMonitoringData(),
            this.updateSystemStatus()
        ]).then(() => {
            console.log('✅ Data refresh completed successfully');
            this.showRefreshSuccess();
        }).catch((error) => {
            console.error('❌ Data refresh failed:', error);
            this.showRefreshError();
        }).finally(() => {
            // Reset button state
            if (refreshButton) {
                const icon = refreshButton.querySelector('i');
                
                setTimeout(() => {
                    refreshButton.disabled = false;
                    icon.style.animation = '';
                    refreshButton.classList.remove('btn-loading');
                    
                    if (refreshText) {
                        refreshText.textContent = 'Refresh';
                    }
                }, 500);
            }
        });
    }

    // Show refresh success feedback
    showRefreshSuccess() {
        this.showToast('Data refreshed successfully', 'success');
    }

    // Show refresh error feedback
    showRefreshError() {
        this.showToast('Failed to refresh data', 'error');
    }

    // Update device data (system resources, device info)
    async updateDeviceData() {
        try {
            // Update system resources if we're on dashboard
            if (typeof updateSystemResources === 'function') {
                await updateSystemResources();
            }
            
            // Update device information
            if (typeof updateDeviceInfo === 'function') {
                await updateDeviceInfo();
            }
            
            console.log('📱 Device data updated');
        } catch (error) {
            console.error('Failed to update device data:', error);
            throw error;
        }
    }

    // Update monitoring data (SCC, battery)
    async updateMonitoringData() {
        try {
            // Update SCC data if we're on SCC page
            if (typeof updateSccData === 'function') {
                await updateSccData();
            }
            
            // Update battery data if we're on battery page
            if (typeof updateBatteryData === 'function') {
                await updateBatteryData();
            }
            
            console.log('📊 Monitoring data updated');
        } catch (error) {
            console.error('Failed to update monitoring data:', error);
            throw error;
        }
    }

    // Update system status
    async updateSystemStatus() {
        try {
            // Update systemd services status
            if (typeof updateSystemdStatus === 'function') {
                await updateSystemdStatus();
            }
            
            // Update MQTT status
            if (typeof updateMqttStatus === 'function') {
                await updateMqttStatus();
            }
            
            console.log('⚙️ System status updated');
        } catch (error) {
            console.error('Failed to update system status:', error);
            throw error;
        }
    }

    // Show toast notification
    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        // Show toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        bsToast.show();

        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    hideLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) {
            setTimeout(() => {
                spinner.classList.add('hidden');
            }, 500);
        }
    }

    // Chart utilities
    createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    updateChart(chartId, data) {
        const chart = this.charts[chartId];
        if (!chart) return;

        chart.data = data;
        chart.update('none');
    }

    destroyChart(chartId) {
        const chart = this.charts[chartId];
        if (chart) {
            chart.destroy();
            delete this.charts[chartId];
        }
    }

    // Utility methods
    formatValue(value, unit = '', decimals = 2) {
        if (typeof value === 'number') {
            return `${value.toFixed(decimals)} ${unit}`.trim();
        }
        return value;
    }

    showConfirmModal(message, callback) {
        const modal = document.getElementById('confirmModal');
        const messageElement = document.getElementById('confirmMessage');
        const confirmButton = document.getElementById('confirmAction');
        
        if (modal && messageElement && confirmButton) {
            messageElement.textContent = message;
            
            const newConfirmButton = confirmButton.cloneNode(true);
            confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
            
            newConfirmButton.addEventListener('click', () => {
                callback();
                bootstrap.Modal.getInstance(modal).hide();
            });
            
            new bootstrap.Modal(modal).show();
        }
    }

    // Cleanup
    destroy() {
        this.stopDataUpdates();
        
        Object.keys(this.charts).forEach(chartId => {
            this.destroyChart(chartId);
        });
        
        if (this.websocket) {
            this.websocket.disconnect();
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.powerDeskApp = new PowerDeskApp();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.powerDeskApp) {
        window.powerDeskApp.destroy();
    }
});

// CSS Animation for spinning
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
