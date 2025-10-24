import os
import subprocess
from datetime import datetime
from flask import jsonify, request
from . import service_bp
from auths import token_auth as auth
from utils import bash_command

# Log file paths configuration
LOG_PATHS = {
    'mqtt_publish.service': {
        'mqtt_errors.log': '/var/lib/sundaya/ehub-universal/logs/mqtt_errors.log',
        'mqtt_warnings.log': '/var/lib/sundaya/ehub-universal/logs/mqtt_warnings.log',
        'mqtt_all.log': '/var/lib/sundaya/ehub-universal/logs/mqtt_all.log'
    },
    'thread_bms.service': {
        'bms_errors.log': '/var/lib/sundaya/ehub-universal/logs/bms_errors.log',
        'bms_warnings.log': '/var/lib/sundaya/ehub-universal/logs/bms_warnings.log',
        'bms_all.log': '/var/lib/sundaya/ehub-universal/logs/bms_all.log'
    },
    'scc.service': {
        'scc_errors.log': '/var/lib/sundaya/ehub-universal/logs/scc_errors.log',
        'scc_warnings.log': '/var/lib/sundaya/ehub-universal/logs/scc_warnings.log',
        'scc_all.log': '/var/lib/sundaya/ehub-universal/logs/scc_all.log'
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
    'scc_logs.timer',
    'store_data_5min.timer',
    'accumulate_energy.service',
    'webapp.service',
    'nginx.service',
    'i2c-heartbeat.service',
    'handle_canbus.service'
]

# Allowed actions
ALLOWED_ACTIONS = ['status', 'start', 'stop', 'restart', 'enable', 'disable', 'logs', 'download_logs']

def run_systemctl_command(action, service):
    """
    Execute systemctl command and return the result
    
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
    """Read log file for a service"""
    try:
        if service in LOG_PATHS and log_file in LOG_PATHS[service]:
            file_path = LOG_PATHS[service][log_file]
        else:
            # Fallback to systemd logs
            cmd = ['journalctl', '-u', service, '-n', str(lines), '--no-pager']
            result = bash_command(cmd, universal_newlines=True)
            
            if result:
                return {
                    'success': True,
                    'logs': result.strip().split('\n'),
                    'source': 'systemd',
                    'service': service,
                    'lines': lines
                }
            else:
                return {
                    'success': False,
                    'error': 'No logs found'
                }
        
        # Read from file
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Get last N lines
            if lines > 0 and lines < len(all_lines):
                log_lines = all_lines[-lines:]
            else:
                log_lines = all_lines
            
            return {
                'success': True,
                'logs': [line.strip() for line in log_lines if line.strip()],
                'source': 'file',
                'file_path': file_path,
                'service': service,
                'log_file': log_file,
                'lines': len(log_lines)
            }
        else:
            return {
                'success': False,
                'error': f'Log file not found: {file_path}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Error reading log file: {str(e)}'
        }

@service_bp.route('/systemd', methods=['GET'])
@auth.login_required
def get_systemd_overview():
    """
    Get systemd service status overview
    
    Returns:
        JSON response with service status summary
    """
    try:
        # Get overview of all services
        active_services = []
        inactive_services = []
        failed_services = []
        
        for service in ALLOWED_SERVICES:
            try:
                # Check if service is active using bash_command
                status_output = bash_command(['systemctl', 'is-active', service], universal_newlines=True)
                status = status_output.strip() if status_output else 'unknown'
                
                service_info = {
                    'name': service,
                    'status': status
                }
                
                if status == 'active':
                    active_services.append(service_info)
                elif status == 'inactive':
                    inactive_services.append(service_info)
                elif status == 'failed':
                    failed_services.append(service_info)
                else:
                    # Unknown status, add to inactive
                    inactive_services.append(service_info)
                    
            except Exception as e:
                print(f"Error checking service {service}: {e}")
                service_info = {
                    'name': service,
                    'status': 'unknown'
                }
                inactive_services.append(service_info)
        
        return jsonify({
            'status': 'success',
            'data': {
                'overview': {
                    'total_services': len(ALLOWED_SERVICES),
                    'active': len(active_services),
                    'inactive': len(inactive_services),
                    'failed': len(failed_services)
                },
                'services': {
                    'active': active_services,
                    'inactive': inactive_services,
                    'failed': failed_services
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get systemd status: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/systemd/list', methods=['GET'])
@auth.login_required
def list_systemd_services():
    """
    Get detailed list of monitored services with their current status
    """
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
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting systemd status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@service_bp.route('/systemd/services-detail', methods=['GET'])
@auth.login_required
def get_systemd_services_detail():
    """
    Get detailed service information including logs availability
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
            'status': 'success',
            'data': services_status,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/systemd/action', methods=['POST'])
@auth.login_required
def handle_systemd_action():
    """Handle POST requests for systemd service actions"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400
        
        service = data.get('service')
        action = data.get('action')
        
        # Validate service and action
        if not service or not action:
            return jsonify({
                'status': 'error',
                'message': 'Service and action are required'
            }), 400
        
        if service not in ALLOWED_SERVICES:
            return jsonify({
                'status': 'error',
                'message': f'Service {service} is not allowed for monitoring'
            }), 400
        
        if action not in ALLOWED_ACTIONS:
            return jsonify({
                'status': 'error',
                'message': f'Action {action} is not allowed'
            }), 400
        
        # Handle different actions
        if action == 'status':
            result = run_systemctl_command('status', service)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'data': result['data'],
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('error', 'Unknown error'),
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
                        'status': 'error',
                        'message': f'No logs available for service {service}'
                    }), 400
            
            # Read more lines for download action
            lines = 1000 if action == 'download_logs' else 100
            result = read_log_file(service, log_file, lines)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('error', 'Failed to read logs'),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        elif action in ['start', 'stop', 'restart', 'enable', 'disable']:
            # Control actions require authentication
            password = data.get('password')
            user = data.get('user')
            
            if not password or not user:
                return jsonify({
                    'status': 'error',
                    'message': 'Password and user are required for control actions'
                }), 400
            
            # Password validation using environment variables
            valid_passwords = {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
            
            if user not in valid_passwords or valid_passwords[user] != password:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid credentials'
                }), 401
            
            # Execute systemctl command
            result = run_systemctl_command(action, service)
            
            if result['success']:
                return jsonify({
                    'status': 'success',
                    'message': f'Service {action} completed successfully',
                    'data': {
                        'output': result.get('output', ''),
                        'service': service,
                        'action': action,
                        'user': user
                    },
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('error', 'Command failed'),
                    'data': {
                        'output': result.get('output', ''),
                        'return_code': result.get('return_code', -1)
                    },
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown action: {action}'
            }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/info', methods=['GET'])
def get_service_info():
    """
    Get service API information and available endpoints
    """
    return jsonify({
        'status': 'success',
        'data': {
            'service': 'Service Management API',
            'description': 'Unified API endpoints for systemd, MQTT, and SNMP services',
            'modules': {
                'systemd': {
                    'endpoints': {
                        'overview': {
                            'path': '/api/v1/service/systemd/',
                            'method': 'GET',
                            'description': 'Get systemd service status overview'
                        },
                        'list': {
                            'path': '/api/v1/service/systemd/list',
                            'method': 'GET',
                            'description': 'List all monitored systemd services'
                        },
                        'services-detail': {
                            'path': '/api/v1/service/systemd/services-detail',
                            'method': 'GET',
                            'description': 'Get detailed service information'
                        },
                        'action': {
                            'path': '/api/v1/service/systemd/action',
                            'method': 'POST',
                            'description': 'Perform actions on systemd services'
                        }
                    },
                    'supported_services': ALLOWED_SERVICES,
                    'supported_actions': ALLOWED_ACTIONS
                },
                'mqtt': {
                    'endpoints': {
                        'logs': {
                            'path': '/api/v1/service/mqtt/logs',
                            'method': 'GET',
                            'description': 'Get MQTT logs from log files'
                        },
                        'download_logs': {
                            'path': '/api/v1/service/mqtt/logs/download',
                            'method': 'GET',
                            'description': 'Download MQTT logs as file'
                        },
                        'data': {
                            'path': '/api/v1/service/mqtt/data',
                            'method': 'GET',
                            'description': 'Get MQTT monitoring data from database'
                        },
                        'latest_data': {
                            'path': '/api/v1/service/mqtt/data/latest',
                            'method': 'GET',
                            'description': 'Get latest MQTT data for real-time monitoring'
                        },
                        'stats': {
                            'path': '/api/v1/service/mqtt/data/stats',
                            'method': 'GET',
                            'description': 'Get MQTT database statistics'
                        },
                        'info': {
                            'path': '/api/v1/service/mqtt/info',
                            'method': 'GET',
                            'description': 'Get MQTT service information'
                        }
                    }
                },
                'snmp': {
                    'endpoints': {
                        'get': {
                            'path': '/api/v1/service/snmp/get',
                            'method': 'POST',
                            'description': 'Execute SNMP GET for single OID'
                        },
                        'bulk_get': {
                            'path': '/api/v1/service/snmp/bulk-get',
                            'method': 'POST',
                            'description': 'Execute SNMP BULK GET for multiple OIDs'
                        },
                        'test': {
                            'path': '/api/v1/service/snmp/test-connection',
                            'method': 'POST',
                            'description': 'Test SNMP connection to device'
                        },
                        'info': {
                            'path': '/api/v1/service/snmp/info',
                            'method': 'GET',
                            'description': 'Get SNMP service information'
                        }
                    }
                }
            }
        }
    }), 200