// Login Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    initializeLogin();
});

function initializeLogin() {
    // Auto-focus on username field
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }

    // Initialize password toggle
    initializePasswordToggle();
    
    // Initialize form submission
    initializeFormSubmission();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
}

function initializePasswordToggle() {
    const toggleBtn = document.getElementById('togglePasswordBtn');
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.getElementById('toggleIcon');
    
    if (!toggleBtn || !passwordInput || !toggleIcon) {
        console.warn('Password toggle elements not found');
        return;
    }

    // Add click event listener
    toggleBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        togglePasswordVisibility();
    });

    // Add keyboard support for accessibility
    toggleBtn.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            togglePasswordVisibility();
        }
    });

    // Make toggle button focusable for accessibility
    toggleBtn.setAttribute('tabindex', '0');
    toggleBtn.setAttribute('role', 'button');
    toggleBtn.setAttribute('aria-label', 'Toggle password visibility');
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.getElementById('toggleIcon');
    const inputGroup = passwordInput.closest('.input-group');
    
    if (!passwordInput || !toggleIcon) {
        console.error('Password toggle elements not found');
        return;
    }

    const isPasswordVisible = passwordInput.type === 'text';
    
    if (isPasswordVisible) {
        // Hide password
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
        inputGroup.classList.remove('password-visible');
        inputGroup.classList.add('password-hidden');
        toggleIcon.parentElement.setAttribute('aria-label', 'Show password');
    } else {
        // Show password
        passwordInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
        inputGroup.classList.remove('password-hidden');
        inputGroup.classList.add('password-visible');
        toggleIcon.parentElement.setAttribute('aria-label', 'Hide password');
    }

    // Keep focus on password input after toggle
    passwordInput.focus();
}

function initializeFormSubmission() {
    const loginForm = document.getElementById('loginForm');
    const loginButton = document.getElementById('loginButton');
    
    if (!loginForm || !loginButton) {
        console.warn('Form elements not found');
        return;
    }

    // Handle form submission
    loginForm.addEventListener('submit', function(e) {
        console.log('Form submit event triggered'); // Debug log
        
        // Validate form before submission
        if (!validateForm()) {
            e.preventDefault();
            return false;
        }

        // Show loading state
        showLoadingState();
        
        // Let the form submit naturally - don't prevent default
        console.log('Form validation passed, submitting...'); // Debug log
    });
    
    // Handle button click explicitly
    loginButton.addEventListener('click', function(e) {
        e.preventDefault(); // Prevent default button behavior
        console.log('Login button clicked'); // Debug log
        
        if (validateForm()) {
            showLoadingState();
            loginForm.submit(); // Explicitly submit the form
        }
    });
}

function validateForm() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    if (!username) {
        showAlert('Please enter your username', 'error');
        document.getElementById('username').focus();
        return false;
    }
    
    if (!password) {
        showAlert('Please enter your password', 'error');
        document.getElementById('password').focus();
        return false;
    }
    
    if (username.length < 3) {
        showAlert('Username must be at least 3 characters long', 'error');
        document.getElementById('username').focus();
        return false;
    }
    
    return true;
}

function showLoadingState() {
    const loginButton = document.getElementById('loginButton');
    const loginText = loginButton.querySelector('.login-text');
    const loginIcon = loginButton.querySelector('.fa-arrow-right');
    
    if (loginButton && loginText && loginIcon) {
        loginButton.disabled = true;
        loginText.textContent = 'Signing In...';
        loginIcon.className = 'loading-spinner';
        
        // Add loading class for additional styling
        loginButton.classList.add('loading');
    }
}

function hideLoadingState() {
    const loginButton = document.getElementById('loginButton');
    const loginText = loginButton.querySelector('.login-text');
    const loginIcon = loginButton.querySelector('.loading-spinner');
    
    if (loginButton && loginText && loginIcon) {
        loginButton.disabled = false;
        loginText.textContent = 'Sign In';
        loginIcon.className = 'fas fa-arrow-right';
        
        // Remove loading class
        loginButton.classList.remove('loading');
    }
}

function initializeKeyboardShortcuts() {
    // Handle Enter key globally
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
            const activeElement = document.activeElement;
            
            // If focus is on username field, move to password
            if (activeElement && activeElement.id === 'username') {
                e.preventDefault();
                const passwordField = document.getElementById('password');
                if (passwordField) {
                    passwordField.focus();
                }
                return;
            }
            
            // If focus is on password field, submit form
            if (activeElement && activeElement.id === 'password') {
                e.preventDefault();
                const form = document.getElementById('loginForm');
                if (form && validateForm()) {
                    showLoadingState();
                    form.submit(); // Use native form submit instead of dispatchEvent
                }
                return;
            }
            
            // If focus is on submit button, submit form
            if (activeElement && activeElement.id === 'loginButton') {
                e.preventDefault();
                const form = document.getElementById('loginForm');
                if (form && validateForm()) {
                    showLoadingState();
                    form.submit(); // Use native form submit instead of dispatchEvent
                }
                return;
            }
        }
        
        // Handle Escape key to clear form
        if (e.key === 'Escape') {
            clearForm();
        }
    });
    
    // Also add Enter key listener specifically to the form inputs
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    if (passwordInput) {
        passwordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const form = document.getElementById('loginForm');
                if (form && validateForm()) {
                    showLoadingState();
                    form.submit();
                }
            }
        });
    }
    
    if (usernameInput) {
        usernameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const passwordField = document.getElementById('password');
                if (passwordField) {
                    passwordField.focus();
                }
            }
        });
    }
}

function clearForm() {
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    
    if (username) username.value = '';
    if (password) password.value = '';
    
    // Reset password visibility to hidden
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.getElementById('toggleIcon');
    const inputGroup = passwordInput?.closest('.input-group');
    
    if (passwordInput && toggleIcon && inputGroup) {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
        inputGroup.classList.remove('password-visible');
        inputGroup.classList.add('password-hidden');
    }
    
    // Focus on username
    if (username) username.focus();
    
    // Clear any alerts
    clearAlerts();
}

function showAlert(message, type = 'info') {
    // Remove existing alerts
    clearAlerts();
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
    `;
    
    // Insert alert before the form
    const form = document.getElementById('loginForm');
    if (form) {
        form.parentNode.insertBefore(alertDiv, form);
        
        // Auto-remove alert after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }
}

function clearAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    });
}

// Utility function for form reset on page errors
function resetFormOnError() {
    hideLoadingState();
    
    // Re-enable form
    const form = document.getElementById('loginForm');
    if (form) {
        const inputs = form.querySelectorAll('input, button');
        inputs.forEach(input => {
            input.disabled = false;
        });
    }
}

// Export functions for global access if needed
window.LoginJS = {
    togglePasswordVisibility,
    showLoadingState,
    hideLoadingState,
    resetFormOnError,
    showAlert,
    clearAlerts
};

// Handle page visibility change to reset form if needed
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Reset loading state when page becomes visible again
        hideLoadingState();
    }
});
