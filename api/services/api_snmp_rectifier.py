import re
import subprocess
from flask import jsonify, request, Response
from . import service_bp
from auths import token_auth as auth
from datetime import datetime

def validate_ip(ip):
    """Validate IP address format"""
    pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    return pattern.match(ip) is not None

def validate_oid(oid):
    """Validate OID format"""
    pattern = re.compile(r'^\.?([0-9]+\.)*[0-9]+$')
    return pattern.match(oid) is not None

def execute_snmpget_rectifier(ip, community, oid, version='1', timeout=10, port=161):
    """Execute snmpget command for rectifier and return the result"""
    try:
        # Construct the snmpget command for rectifier
        cmd = [
            'snmpget',
            '-v', str(version),
            '-c', community,
            '-t', str(timeout),
            '-r', '2',  # Number of retries for rectifier
            f'{ip}:{port}',  # Include port for rectifier
            oid
        ]
        
        # Execute the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 3  # Add buffer to subprocess timeout
        )
        
        if result.returncode == 0:
            # Parse the output
            output = result.stdout.strip()
            if output:
                # Parse different data types from SNMP output
                if 'INTEGER:' in output:
                    try:
                        value = int(output.split('INTEGER:')[1].strip())
                        return {'success': True, 'value': value, 'type': 'integer', 'raw': output}
                    except (ValueError, IndexError):
                        return {'success': True, 'value': output, 'type': 'string', 'raw': output}
                elif 'Gauge32:' in output:
                    try:
                        value = float(output.split('Gauge32:')[1].strip())
                        return {'success': True, 'value': value, 'type': 'gauge', 'raw': output}
                    except (ValueError, IndexError):
                        return {'success': True, 'value': output, 'type': 'string', 'raw': output}
                elif 'Counter32:' in output:
                    try:
                        value = int(output.split('Counter32:')[1].strip())
                        return {'success': True, 'value': value, 'type': 'counter', 'raw': output}
                    except (ValueError, IndexError):
                        return {'success': True, 'value': output, 'type': 'string', 'raw': output}
                elif 'STRING:' in output:
                    value = output.split('STRING:')[1].strip().strip('"')
                    return {'success': True, 'value': value, 'type': 'string', 'raw': output}
                elif 'Hex-STRING:' in output:
                    value = output.split('Hex-STRING:')[1].strip()
                    return {'success': True, 'value': value, 'type': 'hex-string', 'raw': output}
                elif 'OID:' in output:
                    value = output.split('OID:')[1].strip()
                    return {'success': True, 'value': value, 'type': 'oid', 'raw': output}
                elif 'IpAddress:' in output:
                    value = output.split('IpAddress:')[1].strip()
                    return {'success': True, 'value': value, 'type': 'ipaddress', 'raw': output}
                else:
                    # Generic parsing - try to extract value after colon
                    if ':' in output:
                        value = output.split(':', 1)[1].strip()
                        return {'success': True, 'value': value, 'type': 'unknown', 'raw': output}
                    else:
                        return {'success': True, 'value': output, 'type': 'raw', 'raw': output}
            else:
                return {
                    'success': False,
                    'error': 'Empty response from rectifier SNMP agent'
                }
        else:
            error_message = result.stderr.strip() if result.stderr else 'Rectifier SNMP request failed'
            return {
                'success': False,
                'error': error_message,
                'return_code': result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'Rectifier SNMP request timed out after {timeout} seconds'
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'snmpget command not found. Please install SNMP tools.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

@service_bp.route('/snmp-rectifier/get', methods=['POST'])
@auth.login_required
def snmp_rectifier_get():
    """
    Execute SNMP GET for a single rectifier OID
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "port": 161,
        "community": "public",
        "oid": ".1.3.6.1.4.1.2011.6.164.1.3.2.2.1.6",
        "version": "1",  // optional, defaults to 1
        "timeout": 10    // optional, defaults to 10 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Required parameters
        ip = data.get('ip')
        community = data.get('community')
        oid = data.get('oid')
        
        if not ip or not community or not oid:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: ip, community, and oid'
            }), 400
        
        # Optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 10)
        port = data.get('port', 161)
        
        # Validate parameters
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        if not validate_oid(oid):
            return jsonify({
                'success': False,
                'error': 'Invalid OID format'
            }), 400
        
        if version not in ['1', '2c']:
            return jsonify({
                'success': False,
                'error': 'Unsupported SNMP version. Use 1 or 2c'
            }), 400
        
        if not isinstance(timeout, int) or timeout < 1 or timeout > 30:
            return jsonify({
                'success': False,
                'error': 'Timeout must be between 1 and 30 seconds'
            }), 400
        
        if not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({
                'success': False,
                'error': 'Port must be between 1 and 65535'
            }), 400
        
        # Execute SNMP GET
        result = execute_snmpget_rectifier(ip, community, oid, version, timeout, port)
        
        # Add metadata
        result['timestamp'] = datetime.now().isoformat()
        result['request'] = {
            'ip': ip,
            'port': port,
            'community': community,
            'oid': oid,
            'version': version,
            'timeout': timeout
        }
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/snmp-rectifier/bulk-get', methods=['POST'])
@auth.login_required
def snmp_rectifier_bulk_get():
    """
    Execute SNMP GET for multiple rectifier OIDs
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "port": 161,
        "community": "public",
        "oids": [".1.3.6.1.4.1.2011.6.164.1.3.2.2.1.6", ".1.3.6.1.4.1.2011.6.164.1.4.2.12"],
        "version": "1",  // optional, defaults to 1
        "timeout": 10    // optional, defaults to 10 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Required parameters
        ip = data.get('ip')
        community = data.get('community')
        oids = data.get('oids')
        
        if not ip or not community or not oids:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: ip, community, and oids'
            }), 400
        
        if not isinstance(oids, list) or len(oids) == 0:
            return jsonify({
                'success': False,
                'error': 'oids must be a non-empty list'
            }), 400
        
        # Optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 10)
        port = data.get('port', 161)
        
        # Validate parameters
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        for oid in oids:
            if not validate_oid(oid):
                return jsonify({
                    'success': False,
                    'error': f'Invalid OID format: {oid}'
                }), 400
        
        if version not in ['1', '2c']:
            return jsonify({
                'success': False,
                'error': 'Unsupported SNMP version. Use 1 or 2c'
            }), 400
        
        if not isinstance(timeout, int) or timeout < 1 or timeout > 30:
            return jsonify({
                'success': False,
                'error': 'Timeout must be between 1 and 30 seconds'
            }), 400
        
        if not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({
                'success': False,
                'error': 'Port must be between 1 and 65535'
            }), 400
        
        # Execute SNMP GET for each OID
        results = {}
        successful_requests = 0
        failed_requests = 0
        
        for oid in oids:
            result = execute_snmpget_rectifier(ip, community, oid, version, timeout, port)
            results[oid] = result
            
            if result['success']:
                successful_requests += 1
            else:
                failed_requests += 1
        
        # Prepare response
        response = {
            'success': True,
            'results': results,
            'summary': {
                'total_requests': len(oids),
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / len(oids)) * 100
            },
            'timestamp': datetime.now().isoformat(),
            'request': {
                'ip': ip,
                'port': port,
                'community': community,
                'oids': oids,
                'version': version,
                'timeout': timeout
            }
        }
        
        return jsonify(response)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/snmp-rectifier/test-connection', methods=['POST'])
@auth.login_required
def test_snmp_rectifier_connection():
    """
    Test SNMP connection to a rectifier device
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "port": 161,
        "community": "public",
        "version": "1",  // optional, defaults to 1
        "timeout": 10    // optional, defaults to 10 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Required parameters
        ip = data.get('ip')
        community = data.get('community')
        
        if not ip or not community:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: ip and community'
            }), 400
        
        # Optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 10)
        port = data.get('port', 161)
        
        # Validate parameters
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        if version not in ['1', '2c']:
            return jsonify({
                'success': False,
                'error': 'Unsupported SNMP version. Use 1 or 2c'
            }), 400
        
        if not isinstance(timeout, int) or timeout < 1 or timeout > 30:
            return jsonify({
                'success': False,
                'error': 'Timeout must be between 1 and 30 seconds'
            }), 400
        
        if not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({
                'success': False,
                'error': 'Port must be between 1 and 65535'
            }), 400
        
        # Test connection using system description OID
        test_oid = '.1.3.6.1.2.1.1.1.0'  # System description
        result = execute_snmpget_rectifier(ip, community, test_oid, version, timeout, port)
        
        if result['success']:
            response = {
                'success': True,
                'message': 'Rectifier SNMP connection successful',
                'connection_status': 'connected',
                'system_description': result.get('value', 'N/A'),
                'timestamp': datetime.now().isoformat(),
                'request': {
                    'ip': ip,
                    'port': port,
                    'community': community,
                    'version': version,
                    'timeout': timeout
                }
            }
        else:
            response = {
                'success': False,
                'message': 'Rectifier SNMP connection failed',
                'connection_status': 'disconnected',
                'error': result.get('error', 'Unknown error'),
                'timestamp': datetime.now().isoformat(),
                'request': {
                    'ip': ip,
                    'port': port,
                    'community': community,
                    'version': version,
                    'timeout': timeout
                }
            }
        
        return jsonify(response)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/snmp-rectifier/info', methods=['GET'])
def snmp_rectifier_info():
    """
    Get information about available SNMP OIDs for rectifier monitoring
    """
    rectifier_oids = [
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.3.2.2.1.6',
            'name': 'hwRectACVoltage',
            'label': 'Rectifier AC Voltage',
            'unit': 'V',
            'description': 'AC input voltage measurement for rectifier'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.4.2.12',
            'name': 'hwBatteryVoltage',
            'label': 'Battery Voltage',
            'unit': 'V',
            'description': 'Battery voltage measurement'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.1',
            'name': 'hwAcInputStatus',
            'label': 'AC Input Status',
            'unit': '',
            'description': 'AC input status indicator'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.2',
            'name': 'hwRectifierStatus',
            'label': 'Rectifier Status',
            'unit': '',
            'description': 'Overall rectifier status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.3',
            'name': 'hwBatteryDischarge',
            'label': 'Battery Discharge',
            'unit': '',
            'description': 'Battery discharge status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.4',
            'name': 'hwBatteryLowVoltage',
            'label': 'Battery Low Voltage',
            'unit': '',
            'description': 'Battery low voltage alarm status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.5',
            'name': 'hwBatteryUltraLowVoltage',
            'label': 'Battery Ultra Low Voltage',
            'unit': '',
            'description': 'Battery ultra low voltage alarm status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.6',
            'name': 'hwBatteryDisconnect',
            'label': 'Battery Disconnect',
            'unit': '',
            'description': 'Battery disconnect status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.1.3.7',
            'name': 'hwFuseBroken',
            'label': 'Fuse Broken',
            'unit': '',
            'description': 'Fuse broken alarm status'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.1.3.2.2.1.8',
            'name': 'hwRectifierTemperature',
            'label': 'Rectifier Temperature',
            'unit': '°C',
            'description': 'Rectifier temperature measurement'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.2.1.0.23',
            'name': 'hwLoadFuseAlarmTraps',
            'label': 'Load Fuse Alarm',
            'unit': '',
            'description': 'Load fuse alarm traps'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.2.1.0.139',
            'name': 'hwTcucDoorOpenAlarmTraps',
            'label': 'TCUC Door Open Alarm',
            'unit': '',
            'description': 'TCUC door open alarm traps'
        },
        {
            'oid': '.1.3.6.1.4.1.2011.6.164.2.1.0.149',
            'name': 'hwEsduDoorOpenAlarmTraps',
            'label': 'ESDU Door Open Alarm',
            'unit': '',
            'description': 'ESDU door open alarm traps'
        }
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'total_oids': len(rectifier_oids),
            'oids': rectifier_oids,
            'supported_versions': ['1', '2c'],
            'default_community': 'public',
            'default_timeout': 10,
            'default_port': 161,
            'device_type': 'Huawei Rectifier',
            'base_oid': '.1.3.6.1.4.1.2011.6.164'
        }
    })
