/**
 * Enhanced Custom JavaScript for JSPro PowerDesk
 * Compatible with modern layout and original legacy components
 */

// Legacy functionality for older pages
const yearNow = () => {
    const date = new Date();
    const year = date.getFullYear();
    const yearBar = document.getElementById("dynamic-year");
    if (yearBar) {
        yearBar.innerHTML = `&copy ${year}&nbsp;<a target="_blank" href="https://www.sundaya.com/"> Sundaya Indonesia</a>`;
    }
};

const timeNow = () => {
    const date = new Date();
    // day/month/year
    const day = date.getDate();
    const month = date.getMonth() + 1;
    const year = date.getFullYear();
    const tanggal = `${day}/${month}/${year}`;
    // hour:minute:second
    const time = date.toLocaleTimeString("en-US", {
        timeZone: "Asia/Jakarta",
        hour12: false,
    });
    const timeBar = document.getElementById("datetime-bar");
    if (timeBar) {
        timeBar.innerHTML = `<b> ${tanggal} ${time}</b>`;
    }
};

// Modern functionality
const modernTimeNow = () => {
    const date = new Date();
    const options = {
        timeZone: "Asia/Jakarta",
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    const formatted = date.toLocaleString("en-GB", options);
    const timeElement = document.getElementById("current-time");
    if (timeElement) {
        timeElement.textContent = formatted;
    }
};

// Enhanced data fetching utilities
class DataFetcher {
    constructor() {
        this.baseUrl = window.location.origin;
        this.endpoints = {
            deviceInfo: '/api/device-information',
            lvdRealtime: '/api/lvd-realtime',
            sccRealtime: '/api/scc-realtime',
            batteryRealtime: '/api/battery-realtime'
        };
    }

    async fetchData(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error fetching data from ${endpoint}:`, error);
            return null;
        }
    }

    async getAllData() {
        const promises = Object.entries(this.endpoints).map(async ([key, endpoint]) => {
            const data = await this.fetchData(endpoint);
            return { key, data };
        });

        const results = await Promise.allSettled(promises);
        const dataMap = {};

        results.forEach(result => {
            if (result.status === 'fulfilled' && result.value.data) {
                dataMap[result.value.key] = result.value.data;
            }
        });

        return dataMap;
    }
}

// Enhanced animation utilities
class AnimationUtils {
    static fadeIn(element, duration = 300) {
        element.style.opacity = 0;
        element.style.display = 'block';
        
        let start = null;
        const animate = (timestamp) => {
            if (!start) start = timestamp;
            const progress = (timestamp - start) / duration;
            
            element.style.opacity = Math.min(progress, 1);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    static slideDown(element, duration = 300) {
        element.style.height = '0px';
        element.style.overflow = 'hidden';
        element.style.display = 'block';
        
        const targetHeight = element.scrollHeight;
        let start = null;
        
        const animate = (timestamp) => {
            if (!start) start = timestamp;
            const progress = (timestamp - start) / duration;
            
            element.style.height = Math.min(progress * targetHeight, targetHeight) + 'px';
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.style.height = '';
                element.style.overflow = '';
            }
        };
        
        requestAnimationFrame(animate);
    }

    static countUp(element, endValue, duration = 1000) {
        const startValue = 0;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const currentValue = startValue + (endValue - startValue) * progress;
            element.textContent = Math.floor(currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    static pulseElement(element, duration = 1000) {
        element.style.animation = `pulse ${duration}ms ease-in-out`;
        setTimeout(() => {
            element.style.animation = '';
        }, duration);
    }
}

// Enhanced status indicator utilities
class StatusIndicator {
    static updateStatus(element, status, options = {}) {
        const statusClasses = ['status-active', 'status-inactive', 'status-danger', 'status-warning'];
        
        // Remove existing status classes
        statusClasses.forEach(className => {
            element.classList.remove(className);
        });

        // Determine status class
        let statusClass = 'status-inactive';
        
        if (typeof status === 'boolean') {
            statusClass = status ? 'status-active' : 'status-inactive';
        } else if (typeof status === 'string') {
            const lowerStatus = status.toLowerCase();
            if (lowerStatus.includes('active') || lowerStatus.includes('on') || lowerStatus.includes('normal')) {
                statusClass = 'status-active';
            } else if (lowerStatus.includes('alarm') || lowerStatus.includes('error') || lowerStatus.includes('fault')) {
                statusClass = 'status-danger';
            } else if (lowerStatus.includes('warning')) {
                statusClass = 'status-warning';
            }
        }

        element.classList.add(statusClass);
        
        // Add animation if requested
        if (options.animate) {
            AnimationUtils.pulseElement(element, 500);
        }
    }

    static createIndicator(status, text = '') {
        const indicator = document.createElement('span');
        indicator.className = 'status-indicator';
        indicator.textContent = text || status;
        
        this.updateStatus(indicator, status);
        
        return indicator;
    }
}

// Enhanced chart utilities
class ChartUtils {
    static createGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    }

    static getChartColors() {
        return {
            primary: '#2563eb',
            secondary: '#64748b',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#3b82f6'
        };
    }

    static formatTooltip(tooltipItem) {
        const datasetLabel = tooltipItem.dataset.label || '';
        const value = tooltipItem.parsed.y;
        return `${datasetLabel}: ${value.toFixed(2)}`;
    }

    static defaultOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: title
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };
    }
}

// Form utilities
class FormUtils {
    static validateForm(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showFieldError(input, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(input);
            }
        });

        return isValid;
    }

    static showFieldError(input, message) {
        this.clearFieldError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error text-danger mt-1';
        errorDiv.textContent = message;
        
        input.parentNode.appendChild(errorDiv);
        input.classList.add('is-invalid');
    }

    static clearFieldError(input) {
        const existingError = input.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        input.classList.remove('is-invalid');
    }

    static showSuccess(message) {
        this.showNotification(message, 'success');
    }

    static showError(message) {
        this.showNotification(message, 'danger');
    }

    static showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            <strong>${type.charAt(0).toUpperCase() + type.slice(1)}!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize legacy functionality
yearNow();
setInterval(() => {
    timeNow();
    modernTimeNow();
}, 1000);

// Enhanced page-specific functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're using modern layout
    const isModernLayout = document.querySelector('.app-container');
    
    if (isModernLayout) {
        // Modern layout specific initialization
        console.log('Modern layout detected - enhanced functionality enabled');
        
        // Initialize data fetcher for modern pages
        window.dataFetcher = new DataFetcher();
        
        // Add smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });
        
        // Add loading states to buttons
        document.querySelectorAll('button[type="submit"]').forEach(button => {
            button.addEventListener('click', function() {
                const originalText = this.textContent;
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
                this.disabled = true;
                
                // Re-enable after 3 seconds (fallback)
                setTimeout(() => {
                    this.textContent = originalText;
                    this.disabled = false;
                }, 3000);
            });
        });
    } else {
        // Legacy layout specific initialization
        console.log('Legacy layout detected - maintaining compatibility');
        
        // Legacy sidebar toggle
        $("#sidebarCollapse").on("click", function () {
            $("#sidebar").toggleClass("active");
            $("#content").toggleClass("active");
        });

        $(".more-button,.body-overlay").on("click", function () {
            $("#sidebar,.body-overlay").toggleClass("show-nav");
        });
    }
    
    // Universal enhancements
    
    // Add tooltips to elements with title attribute
    document.querySelectorAll('[title]').forEach(element => {
        if (typeof bootstrap !== 'undefined') {
            new bootstrap.Tooltip(element);
        }
    });
    
    // Add confirm dialogs to dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => {
                    alert.remove();
                }, 150);
            }
        }, 5000);
    });
});

// Export utilities for use in other files
window.AnimationUtils = AnimationUtils;
window.StatusIndicator = StatusIndicator;
window.ChartUtils = ChartUtils;
window.FormUtils = FormUtils;

// Legacy support - make sure these are available globally
window.yearNow = yearNow;
window.timeNow = timeNow;
