import json
import platform
import os
import subprocess
from datetime import datetime
from flask import jsonify, request
from . import device_bp
from ..redisconnection import connection as red
from auths import token_auth as auth
from functions import bash_command, get_disk_detail, get_cpu_usage, get_memory_usage, get_temperature
from redis.exceptions import RedisError

# Log file paths configuration
LOG_PATHS = {
    'mqtt_publish.service': {
        'mqtt_errors.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_errors.log',
        'mqtt_warnings.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_warnings.log',
        'mqtt_all.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_all.log'
    },
    'thread_bms.service': {
        'bms_errors.log': '/var/lib/sundaya/ehub-talis/logs/bms_errors.log',
        'bms_warnings.log': '/var/lib/sundaya/ehub-talis/logs/bms_warnings.log',
        'bms_all.log': '/var/lib/sundaya/ehub-talis/logs/bms_all.log'
    },
    'scc.service': {
        'scc_errors.log': '/var/lib/sundaya/ehub-talis/logs/scc_errors.log',
        'scc_warnings.log': '/var/lib/sundaya/ehub-talis/logs/scc_warnings.log',
        'scc_all.log': '/var/lib/sundaya/ehub-talis/logs/scc_all.log'
    },
    'i2c-heartbeat.service': {
        'i2c_communication.log': '/var/lib/sundaya/jspro-powerdesk/logs/i2c_communication.log'
    }
}

# Allowed services for monitoring
ALLOWED_SERVICES = [
    'mqtt_publish.service',
    'redis.service',
    'snmp_handler.service',
    'thread_bms.service',
    'scc.service',
    'store_data_5min.timer',
    'accumulate_energy.service',
    'webapp.service',
    'i2c-heartbeat.service'
]

# Allowed actions
ALLOWED_ACTIONS = ['status', 'start', 'stop', 'restart', 'enable', 'disable', 'logs', 'download_logs']

def run_systemctl_command(action, service):
    """
    Run systemctl command and return the result
    
    Args:
        action (str): The systemctl action (start, stop, restart, etc.)
        service (str): The service name
        
    Returns:
        dict: Command result with success, output, and error
    """
    try:
        cmd = ['sudo', 'systemctl', action, service]
        
        # Special handling for status command
        if action == 'status':
            # Get detailed status information
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse systemctl status output
            status_info = {
                'status': 'unknown',
                'enabled': False,
                'active': False,
                'running': False,
                'output': result.stdout,
                'error': result.stderr
            }
            
            # Also get quick status check for cross-validation
            try:
                is_active_cmd = ['sudo', 'systemctl', 'is-active', service]
                is_active_result = subprocess.run(is_active_cmd, capture_output=True, text=True, timeout=10)
                is_active_status = is_active_result.stdout.strip()
                
                is_enabled_cmd = ['sudo', 'systemctl', 'is-enabled', service]
                is_enabled_result = subprocess.run(is_enabled_cmd, capture_output=True, text=True, timeout=10)
                is_enabled_status = is_enabled_result.stdout.strip()
                
                # Debug info
                status_info['debug'] = {
                    'is_active': is_active_status,
                    'is_enabled': is_enabled_status
                }
                
            except Exception as e:
                status_info['debug'] = {
                    'error': f'Failed to get quick status: {str(e)}'
                }
            
            # Parse the output to get status information
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'Active:' in line:
                    if 'active (running)' in line:
                        status_info['status'] = 'active'
                        status_info['active'] = True
                        status_info['running'] = True
                    elif 'active (waiting)' in line:
                        # For timers that are active but waiting
                        status_info['status'] = 'active'
                        status_info['active'] = True
                        status_info['running'] = False  # Timer is waiting, not running
                    elif 'active (elapsed)' in line:
                        # For timers that have elapsed
                        status_info['status'] = 'active'
                        status_info['active'] = True
                        status_info['running'] = False
                    elif 'inactive' in line:
                        status_info['status'] = 'inactive'
                        status_info['active'] = False
                        status_info['running'] = False
                    elif 'failed' in line:
                        status_info['status'] = 'failed'
                        status_info['active'] = False
                        status_info['running'] = False
                    else:
                        # Fallback: check if line contains 'active'
                        if 'active' in line.lower():
                            status_info['status'] = 'active'
                            status_info['active'] = True
                            # For timers, they might be active but not running
                            status_info['running'] = 'running' in line.lower()
                elif 'Loaded:' in line:
                    if 'enabled' in line:
                        status_info['enabled'] = True
                    elif 'disabled' in line:
                        status_info['enabled'] = False
            
            # Cross-validate with quick status check
            if 'debug' in status_info and 'is_active' in status_info['debug']:
                is_active_status = status_info['debug']['is_active']
                is_enabled_status = status_info['debug']['is_enabled']
                
                # If parsing failed but quick check succeeded, use quick check result
                if status_info['status'] == 'unknown' and is_active_status == 'active':
                    status_info['status'] = 'active'
                    status_info['active'] = True
                    # For timers, they are active but not necessarily running
                    if service.endswith('.timer'):
                        status_info['running'] = False  # Timers don't "run" like services
                    else:
                        status_info['running'] = True
                
                # Update enabled status from quick check
                if is_enabled_status == 'enabled':
                    status_info['enabled'] = True
                elif is_enabled_status == 'disabled':
                    status_info['enabled'] = False
            
            return {
                'success': True,
                'data': status_info
            }
        else:
            # For other actions (start, stop, restart, enable, disable)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out'
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'error': f'Command failed: {e}',
            'return_code': e.returncode
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def read_log_file(service, log_file, lines=100):
    """
    Read log file for a service
    
    Args:
        service (str): Service name
        log_file (str): Log file name
        lines (int): Number of lines to read from the end
        
    Returns:
        dict: Log content or error
    """
    try:
        if service not in LOG_PATHS:
            return {
                'success': False,
                'error': f'No logs available for service {service}'
            }
        
        if log_file not in LOG_PATHS[service]:
            return {
                'success': False,
                'error': f'Log file {log_file} not found for service {service}'
            }
        
        log_path = LOG_PATHS[service][log_file]
        
        # Check if log file exists
        if not os.path.exists(log_path):
            return {
                'success': False,
                'error': f'Log file does not exist: {log_path}'
            }
        
        # Read last N lines from the log file
        try:
            result = subprocess.run(
                ['tail', '-n', str(lines), log_path], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'logs': result.stdout,
                    'log_file': log_file,
                    'log_path': log_path
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to read log file: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Log reading timed out'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Error reading log file: {str(e)}'
        }


@device_bp.route('/system-resources', methods=['GET'])
@auth.login_required
def get_system_resources():
    """Get system resources including CPU, memory, temperature, and disk usage"""
    try:
        # Get CPU usage
        cpu_usage = get_cpu_usage()
        cpu_dict = {
            "value": float(cpu_usage),
            "unit": "%"
        }

        # Get memory usage
        memory_usage = get_memory_usage()
        memory_dict = {
            "value": float(memory_usage),
            "unit": "%"
        }
        
        # Get temperature using the fixed function
        temperature = get_temperature()
        temperature_dict = {
            "value": round(temperature, 1),
            "unit": "°C"
        }
        
        # Get disk usage
        disk = get_disk_detail()
        disk_usage = {
            "free": round(disk.free / (1024**3), 1),  # Convert to GB
            "used": round(disk.used / (1024**3), 1),  # Convert to GB
            "total": round(disk.total / (1024**3), 1),  # Convert to GB
            "unit": "GB"
        }
        
        response_data = {
            "cpu_usage": cpu_dict,
            "memory_usage": memory_dict,
            "temperature": temperature_dict,
            "disk_usage": disk_usage,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting system resources: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error",
            "data": None
        }), 500


@device_bp.route('/information', methods=['GET'])
@auth.login_required
def get_device_information():
    """Get device information including site information, device version, and device model"""
    try:
        device_data = red.hgetall("device_config")
        if not device_data:
            return jsonify({
                "status_code": 404,
                "message": "Device configuration not found",
                "data": None
            }), 404
        
        # Parse JSON strings to objects
        site_information = {}
        device_version = {}
        device_model = {}
        
        try:
            site_info_str = device_data.get("site_information", "{}")
            if isinstance(site_info_str, str):
                site_information = json.loads(site_info_str)
            else:
                site_information = site_info_str or {}
        except (json.JSONDecodeError, TypeError):
            site_information = {
                "site_id": "PAP9999",
                "site_name": "Site Name",
                "address": "Jl. Bakti No. 1"
            }
        
        try:
            device_version_str = device_data.get("device_version", "{}")
            if isinstance(device_version_str, str):
                device_version = json.loads(device_version_str)
            else:
                device_version = device_version_str or {}
        except (json.JSONDecodeError, TypeError):
            device_version = {
                "ehub_version": "new",
                "panel2_type": "new",
                "site_type": "bakti",
                "scc_type": "scc-epveper",
                "scc_id": [2, 1],
                "scc_source": "serial",
                "battery_type": "talis5"
            }
        
        try:
            device_model_str = device_data.get("device_model", "{}")
            if isinstance(device_model_str, str):
                device_model = json.loads(device_model_str)
            else:
                device_model = device_model_str or {}
        except (json.JSONDecodeError, TypeError):
            device_model = {
                "model": "JSPro MPPT",
                "part_number": "JP-MPPT-40A",
                "serial_number": "SN123456789",
                "software_version": "2.0.0",
                "hardware_version": "2.0.0"
            }
        
        response_data = {
            "site_information": site_information,
            "device_version": device_version,
            "device_model": device_model,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting device information: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error",
            "data": None
        }), 500


@device_bp.route('/systemd-status', methods=['GET', 'POST'])
@auth.login_required
def handle_systemd_status():
    """
    Handle systemd service operations - both status checking and control actions
    
    GET: Get status overview of all services
    POST: Handle specific service operations
    
    POST Request JSON:
    {
        "service": "service_name",
        "action": "status|start|stop|restart|enable|disable|logs|download_logs",
        "log_file": "log_file_name" (for logs actions),
        "password": "user_password" (for control actions),
        "user": "username" (for control actions)
    }
    """
    if request.method == 'GET':
        # Original GET behavior for backward compatibility
        return get_systemd_status_overview()
    
    elif request.method == 'POST':
        return handle_systemd_action()

def get_systemd_status_overview():
    """Get systemd service status overview (original functionality)"""
    try:
        services_status = {}
        active_count = 0
        inactive_count = 0
        failed_count = 0
        
        for service in ALLOWED_SERVICES:
            try:
                # Check if service is active
                status_output = bash_command(['systemctl', 'is-active', service], universal_newlines=True)
                status = status_output.strip() if status_output else 'unknown'
                
                services_status[service] = status
                
                if status == 'active':
                    active_count += 1
                elif status == 'inactive':
                    inactive_count += 1
                elif status == 'failed':
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error checking service {service}: {e}")
                services_status[service] = 'unknown'
                
        # Get system uptime
        try:
            uptime_output = bash_command(['uptime', '-p'], universal_newlines=True)
            system_uptime = uptime_output.strip().replace('up ', '') if uptime_output else 'unknown'
        except:
            system_uptime = "unknown"
        
        response_data = {
            "active_service": active_count,
            "inactive_service": inactive_count, 
            "failed_service": failed_count,
            "services_status": services_status,
            "system_uptime": system_uptime,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting systemd status: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error", 
            "data": None
        }), 500

def handle_systemd_action():
    """Handle POST requests for systemd service actions"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        service = data.get('service')
        action = data.get('action')
        
        # Validate service and action
        if not service or not action:
            return jsonify({
                'success': False,
                'error': 'Service and action are required'
            }), 400
        
        if service not in ALLOWED_SERVICES:
            return jsonify({
                'success': False,
                'error': f'Service {service} is not allowed for monitoring'
            }), 400
        
        if action not in ALLOWED_ACTIONS:
            return jsonify({
                'success': False,
                'error': f'Action {action} is not allowed'
            }), 400
        
        # Handle different actions
        if action == 'status':
            result = run_systemctl_command('status', service)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result['data'],
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        elif action in ['logs', 'download_logs']:
            log_file = data.get('log_file')
            
            if not log_file:
                # If no specific log file requested, use the first available one
                if service in LOG_PATHS and LOG_PATHS[service]:
                    log_file = list(LOG_PATHS[service].keys())[0]
                else:
                    return jsonify({
                        'success': False,
                        'error': f'No logs available for service {service}'
                    }), 400
            
            # Read more lines for download action
            lines = 1000 if action == 'download_logs' else 100
            result = read_log_file(service, log_file, lines)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to read logs'),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        elif action in ['start', 'stop', 'restart', 'enable', 'disable']:
            # Control actions require authentication
            password = data.get('password')
            user = data.get('user')
            
            if not password or not user:
                return jsonify({
                    'success': False,
                    'error': 'Password and user are required for control actions'
                }), 400
            
            # Password validation using environment variables
            valid_passwords = {
                'apt': os.getenv('APT_PASSWORD', 'powerapt'),
                'teknisi': os.getenv('TEKNISI_PASSWORD', 'Joulestore2020'),
                'admin': os.getenv('ADMIN_PASSWORD', 'admin')
            }
            
            if user not in valid_passwords or valid_passwords[user] != password:
                return jsonify({
                    'success': False,
                    'error': 'Invalid credentials'
                }), 401
            
            # Execute systemctl command
            result = run_systemctl_command(action, service)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f'Service {action} completed successfully',
                    'data': {
                        'output': result.get('output', ''),
                        'service': service,
                        'action': action,
                        'user': user
                    },
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Command failed'),
                    'data': {
                        'output': result.get('output', ''),
                        'return_code': result.get('return_code', -1)
                    },
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown action: {action}'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@device_bp.route('/systemd-services', methods=['GET'])
@auth.login_required
def list_systemd_services():
    """
    Get list of monitored services with their current status
    """
    try:
        services_status = []
        
        for service in ALLOWED_SERVICES:
            result = run_systemctl_command('status', service)
            
            if result['success']:
                service_info = {
                    'name': service,
                    'status': result['data'],
                    'has_logs': service in LOG_PATHS,
                    'log_files': list(LOG_PATHS.get(service, {}).keys()) if service in LOG_PATHS else []
                }
            else:
                service_info = {
                    'name': service,
                    'status': {
                        'status': 'unknown',
                        'enabled': False,
                        'active': False,
                        'running': False,
                        'error': result.get('error', 'Unknown error')
                    },
                    'has_logs': service in LOG_PATHS,
                    'log_files': list(LOG_PATHS.get(service, {}).keys()) if service in LOG_PATHS else []
                }
            
            services_status.append(service_info)
        
        return jsonify({
            'success': True,
            'data': services_status,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500