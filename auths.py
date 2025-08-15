import os
import hashlib
import secrets
from datetime import datetime, timedelta
from flask_httpauth import HTTPTokenAuth, HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, environment variables should be set manually
    print("[WARNING] python-dotenv not installed. Please set environment variables manually or install with: pip install python-dotenv")

token_auth = HTTPTokenAuth(scheme='Bearer')
basic_auth = HTTPBasicAuth()

# Secure token storage using environment variables
# In production, these should be set as environment variables
TOKENS = {
    os.getenv('API_TOKEN_1'): 'admin',
    os.getenv('API_TOKEN_2'): 'teknisi',
    os.getenv('API_TOKEN_3'): 'apt'
}

# Secure user storage with hashed passwords
# In production, this should be moved to a database
USERS = {
    'teknisi': {
        'password_hash': generate_password_hash(os.getenv('TEKNISI_PASSWORD')),
        'role': 'teknisi',
        'last_login': None,
        'failed_attempts': 0,
        'locked_until': None
    },
    'apt': {
        'password_hash': generate_password_hash(os.getenv('APT_PASSWORD')),
        'role': 'apt', 
        'last_login': None,
        'failed_attempts': 0,
        'locked_until': None
    },
    'admin': {
        'password_hash': generate_password_hash(os.getenv('ADMIN_PASSWORD')),
        'role': 'admin',
        'last_login': None,
        'failed_attempts': 0,
        'locked_until': None
    }
}

# Security configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)
TOKEN_EXPIRY = timedelta(hours=24)

# Role-based access control configuration
ROLE_PERMISSIONS = {
    'teknisi': {
        'pages': [
            'dashboard',
            'scc_monitoring',
            'battery_monitoring',
            'systemd_service',
            'snmp_service',
            'site_information',
            'device_settings',
            'scc_settings',
            'ip_configuration',
            'power_operations'
        ],
        'actions': [
            'view_dashboard',
            'view_scc_data',
            'view_battery_data',
            'manage_systemd_services',
            'view_site_info',
            'configure_device',
            'configure_scc',
            'configure_network',
            'system_reboot',
            'system_shutdown'
        ],
        'api_endpoints': [
            '/api/v1/device/*',
            '/api/v1/monitoring/*',
            '/api/v1/loggers/*',
        ]
    },
    'apt': {
        'pages': [
            'dashboard',
            'scc_monitoring',
            'snmp_service',
            'site_information',
            'device_settings'
        ],
        'actions': [
            'view_dashboard',
            'view_scc_data',
            'view_site_info',
            'configure_device'
        ],
        'api_endpoints': [
            '/api/v1/device/*',
            '/api/v1/monitoring/*',
            '/api/v1/loggers/*',
        ]
    },
    'admin': {
        'pages': [
            'dashboard',
            'scc_monitoring',
            'battery_monitoring',
            'mqtt_service',
            'systemd_service',
            'snmp_service',
            'datalog',
            'scc_alarm_log',
            'site_information',
            'device_settings',
            'scc_settings',
            'ip_configuration',
            'power_operations',
            'user_management'
        ],
        'actions': [
            'view_dashboard',
            'view_scc_data',
            'view_battery_data',
            'manage_mqtt_service',
            'manage_systemd_services',
            'view_historical_data',
            'view_alarm_logs',
            'view_site_info',
            'configure_device',
            'configure_scc',
            'configure_network',
            'system_reboot',
            'system_shutdown',
            'manage_users',
            'view_security_logs'
        ],
        'api_endpoints': [
            '/api/v1/*'  # Admin has access to all API endpoints
        ]
    }
}

# Menu visibility configuration based on roles
MENU_ACCESS = {
    'teknisi': {
        'dashboard': True,
        'monitoring': {
            'scc': True,
            'battery': True
        },
        'services': {
            'mqtt': False,
            'systemd': True,
            'snmp': True
        },
        'historical': {
            'datalog': False,
            'scc_alarm_log': False
        },
        'site_information': True,
        'settings': {
            'device_settings': True,
            'scc_settings': True,
            'ip_configuration': True
        },
        'power_operations': True
    },
    'apt': {
        'dashboard': True,
        'monitoring': {
            'scc': True,
            'battery': False
        },
        'services': {
            'mqtt': False,
            'systemd': False,
            'snmp': True
        },
        'historical': {
            'datalog': False,
            'scc_alarm_log': False
        },
        'site_information': True,
        'settings': {
            'device_settings': True,
            'scc_settings': False,
            'ip_configuration': False
        },
        'power_operations': False
    },
    'admin': {
        'dashboard': True,
        'monitoring': {
            'scc': True,
            'battery': True
        },
        'services': {
            'mqtt': True,
            'systemd': True,
            'snmp': True
        },
        'historical': {
            'datalog': True,
            'scc_alarm_log': True
        },
        'site_information': True,
        'settings': {
            'device_settings': True,
            'scc_settings': True,
            'ip_configuration': True
        },
        'power_operations': True
    }
}

# Active sessions storage (in production, use Redis or database)
ACTIVE_SESSIONS = {}

def generate_secure_token():
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(32)

def hash_token(token):
    """Create a secure hash of the token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def is_user_locked(username):
    """Check if user account is locked due to failed attempts"""
    if username not in USERS:
        return True
    
    user = USERS[username]
    if user.get('locked_until'):
        if datetime.now() < user['locked_until']:
            return True
        else:
            # Unlock user if lockout period has expired
            user['locked_until'] = None
            user['failed_attempts'] = 0
    
    return False

def record_failed_attempt(username):
    """Record a failed login attempt"""
    if username in USERS:
        user = USERS[username]
        user['failed_attempts'] = user.get('failed_attempts', 0) + 1
        
        if user['failed_attempts'] >= MAX_FAILED_ATTEMPTS:
            user['locked_until'] = datetime.now() + LOCKOUT_DURATION

def record_successful_login(username):
    """Record a successful login"""
    if username in USERS:
        user = USERS[username]
        user['last_login'] = datetime.now()
        user['failed_attempts'] = 0
        user['locked_until'] = None

def validate_token_format(token):
    """Validate token format and structure"""
    if not token:
        return False
    
    # Check if token is properly base64 encoded
    try:
        import base64
        base64.b64decode(token)
        return len(token) >= 16  # Minimum token length
    except:
        return False

@token_auth.verify_token
def verify_token(token):
    """Verify Bearer token with enhanced security"""
    if not validate_token_format(token):
        return None
    
    # Check against configured tokens
    if token in TOKENS:
        # Log token usage for auditing
        print(f"[AUTH] Token authentication successful for role: {TOKENS[token]} at {datetime.now()}")
        return TOKENS[token]
    
    # Check active sessions (for generated tokens)
    token_hash = hash_token(token)
    if token_hash in ACTIVE_SESSIONS:
        session = ACTIVE_SESSIONS[token_hash]
        if datetime.now() < session['expires_at']:
            return session['user']
        else:
            # Remove expired session
            del ACTIVE_SESSIONS[token_hash]
    
    print(f"[AUTH] Invalid token attempt at {datetime.now()}")
    return None

@basic_auth.verify_password
def verify_password(username, password):
    """Verify username/password with enhanced security"""
    if not username or not password:
        return None
    
    # Check if user exists
    if username not in USERS:
        print(f"[AUTH] Login attempt for non-existent user: {username}")
        return None
    
    # Check if user is locked
    if is_user_locked(username):
        remaining_time = USERS[username].get('locked_until', datetime.now()) - datetime.now()
        print(f"[AUTH] Login attempt for locked user: {username}. Remaining lockout: {remaining_time}")
        return None
    
    # Verify password
    user = USERS[username]
    if check_password_hash(user['password_hash'], password):
        record_successful_login(username)
        print(f"[AUTH] Successful login for user: {username} at {datetime.now()}")
        return username
    else:
        record_failed_attempt(username)
        print(f"[AUTH] Failed login attempt for user: {username}. Attempts: {user['failed_attempts']}")
        return None

def create_session_token(username):
    """Create a temporary session token for a user"""
    if username not in USERS:
        return None
    
    token = generate_secure_token()
    token_hash = hash_token(token)
    
    ACTIVE_SESSIONS[token_hash] = {
        'user': username,
        'role': USERS[username]['role'],
        'created_at': datetime.now(),
        'expires_at': datetime.now() + TOKEN_EXPIRY
    }
    
    return token

def revoke_session_token(token):
    """Revoke a session token"""
    token_hash = hash_token(token)
    if token_hash in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token_hash]
        return True
    return False

def cleanup_expired_sessions():
    """Clean up expired session tokens"""
    current_time = datetime.now()
    expired_tokens = [
        token_hash for token_hash, session in ACTIVE_SESSIONS.items()
        if current_time >= session['expires_at']
    ]
    
    for token_hash in expired_tokens:
        del ACTIVE_SESSIONS[token_hash]
    
    return len(expired_tokens)

def get_user_info(username):
    """Get user information safely"""
    if username in USERS:
        user = USERS[username].copy()
        # Remove sensitive information
        user.pop('password_hash', None)
        return user
    return None

# Security utility functions
def log_security_event(event_type, username=None, details=None):
    """Log security events for auditing"""
    timestamp = datetime.now().isoformat()
    log_entry = f"[SECURITY] {timestamp} - {event_type}"
    
    if username:
        log_entry += f" - User: {username}"
    
    if details:
        log_entry += f" - Details: {details}"
    
    print(log_entry)
    
    # In production, write to security log file or database
    # with open('security.log', 'a') as f:
    #     f.write(log_entry + '\n')

def validate_session():
    """Validate current session and clean up expired ones"""
    cleanup_expired_sessions()
    return True

# Role-based access control functions
def get_user_role(username):
    """Get user role"""
    if username in USERS:
        return USERS[username].get('role', 'guest')
    return 'guest'

def get_role_api_token(role):
    """Get API token based on user role"""
    role_token_mapping = {
        'admin': os.getenv('API_TOKEN_1'),
        'teknisi': os.getenv('API_TOKEN_2'),
        'apt': os.getenv('API_TOKEN_3')
    }
    return role_token_mapping.get(role)

def get_user_api_token(username):
    """Get API token for a specific user based on their role"""
    user_role = get_user_role(username)
    return get_role_api_token(user_role)

def has_permission(username, permission_type, permission_name):
    """Check if user has specific permission"""
    user_role = get_user_role(username)
    
    if user_role not in ROLE_PERMISSIONS:
        return False
    
    permissions = ROLE_PERMISSIONS[user_role].get(permission_type, [])
    
    # For API endpoints, check pattern matching
    if permission_type == 'api_endpoints':
        for endpoint_pattern in permissions:
            if endpoint_pattern.endswith('/*'):
                # Wildcard matching
                base_pattern = endpoint_pattern[:-2]
                if permission_name.startswith(base_pattern):
                    return True
            elif endpoint_pattern == permission_name:
                return True
        return False
    
    return permission_name in permissions

def can_access_page(username, page_name):
    """Check if user can access a specific page"""
    return has_permission(username, 'pages', page_name)

def can_perform_action(username, action_name):
    """Check if user can perform a specific action"""
    return has_permission(username, 'actions', action_name)

def can_access_api(username, endpoint):
    """Check if user can access a specific API endpoint"""
    return has_permission(username, 'api_endpoints', endpoint)

def get_menu_access(username):
    """Get menu access configuration for user"""
    user_role = get_user_role(username)
    return MENU_ACCESS.get(user_role, {})

def is_menu_visible(username, menu_path):
    """Check if specific menu item should be visible for user"""
    menu_config = get_menu_access(username)
    
    # Handle nested menu paths like 'monitoring.scc' or 'settings.device_settings'
    path_parts = menu_path.split('.')
    current_config = menu_config
    
    for part in path_parts:
        if isinstance(current_config, dict) and part in current_config:
            current_config = current_config[part]
        else:
            return False
    
    return bool(current_config) if isinstance(current_config, bool) else False

def get_accessible_pages(username):
    """Get list of pages user can access"""
    user_role = get_user_role(username)
    return ROLE_PERMISSIONS.get(user_role, {}).get('pages', [])

def get_user_capabilities(username):
    """Get comprehensive user capabilities"""
    user_role = get_user_role(username)
    user_info = get_user_info(username)
    
    if not user_info:
        return None
    
    return {
        'username': username,
        'role': user_role,
        'permissions': ROLE_PERMISSIONS.get(user_role, {}),
        'menu_access': get_menu_access(username),
        'last_login': user_info.get('last_login'),
        'account_status': 'locked' if is_user_locked(username) else 'active'
    }

def require_permission(permission_type, permission_name):
    """Decorator to require specific permission for routes"""
    def decorator(f):
        from functools import wraps
        from flask import abort, session
        from flask_login import current_user
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            username = current_user.id
            if not has_permission(username, permission_type, permission_name):
                log_security_event(
                    'PERMISSION_DENIED',
                    username,
                    f'Attempted to access {permission_type}: {permission_name}'
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(required_role):
    """Decorator to require specific role for routes"""
    def decorator(f):
        from functools import wraps
        from flask import abort
        from flask_login import current_user
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            username = current_user.id
            user_role = get_user_role(username)
            
            if user_role != required_role:
                log_security_event(
                    'ROLE_ACCESS_DENIED',
                    username,
                    f'Required role: {required_role}, User role: {user_role}'
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_access(username, resource, action='access'):
    """Audit user access to resources"""
    log_security_event(
        'RESOURCE_ACCESS',
        username,
        f'Action: {action}, Resource: {resource}'
    )
