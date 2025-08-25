import re
import subprocess
import os
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

def execute_snmpget(ip, community, oid, version='1', timeout=5):
    """Execute snmpget command and return the result"""
    try:
        # Construct the snmpget command
        cmd = [
            'snmpget',
            '-v', str(version),
            '-c', community,
            '-t', str(timeout),
            '-r', '1',  # Number of retries
            ip,
            oid
        ]
        
        # Execute the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2  # Add buffer to subprocess timeout
        )
        
        if result.returncode == 0:
            # Parse the output
            output = result.stdout.strip()
            if output:
                # Extract value from SNMP output
                # Format is usually: OID = TYPE: VALUE
                parts = output.split('=', 1)
                if len(parts) == 2:
                    value_part = parts[1].strip()
                    # Remove type information (e.g., "INTEGER: 42" -> "42")
                    if ':' in value_part:
                        value = value_part.split(':', 1)[1].strip()
                    else:
                        value = value_part
                    
                    # Try to convert to number if possible
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        # Keep as string if not a number
                        pass
                    
                    return {
                        'success': True,
                        'value': value,
                        'raw_output': output,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Invalid SNMP response format',
                        'raw_output': output
                    }
            else:
                return {
                    'success': False,
                    'error': 'Empty response from SNMP',
                    'raw_output': output
                }
        else:
            error_message = result.stderr.strip() if result.stderr else 'SNMP request failed'
            return {
                'success': False,
                'error': error_message,
                'returncode': result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'SNMP request timed out after {timeout} seconds'
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

@service_bp.route('/snmp/get', methods=['POST'])
@auth.login_required
def snmp_get():
    """
    Execute SNMP GET for a single OID
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "community": "public",
        "oid": ".1.3.6.1.2.1.25.1.11",
        "version": "1",  // optional, defaults to 1
        "timeout": 5     // optional, defaults to 5 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Extract required parameters
        ip = data.get('ip', '').strip()
        community = data.get('community', '').strip()
        oid = data.get('oid', '').strip()
        
        # Extract optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 5)
        
        # Validate required parameters
        if not ip:
            return jsonify({
                'success': False,
                'error': 'IP address is required'
            }), 400
            
        if not community:
            return jsonify({
                'success': False,
                'error': 'Community string is required'
            }), 400
            
        if not oid:
            return jsonify({
                'success': False,
                'error': 'OID is required'
            }), 400
        
        # Validate IP address format
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        # Validate OID format
        if not validate_oid(oid):
            return jsonify({
                'success': False,
                'error': 'Invalid OID format'
            }), 400
        
        # Validate timeout
        try:
            timeout = int(timeout)
            if timeout < 1 or timeout > 30:
                timeout = 5
        except (ValueError, TypeError):
            timeout = 5
        
        # Execute SNMP GET
        result = execute_snmpget(ip, community, oid, version, timeout)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'ip': ip,
                    'community': community,
                    'oid': oid,
                    'value': result['value'],
                    'raw_output': result['raw_output'],
                    'timestamp': result['timestamp']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'data': {
                    'ip': ip,
                    'community': community,
                    'oid': oid
                }
            }), 200  # Return 200 but with success: false for client handling
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@service_bp.route('/snmp/bulk-get', methods=['POST'])
@auth.login_required
def snmp_bulk_get():
    """
    Execute SNMP GET for multiple OIDs
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "community": "public",
        "oids": [".1.3.6.1.2.1.25.1.11", ".1.3.6.1.2.1.25.1.12"],
        "version": "1",  // optional, defaults to 1
        "timeout": 5     // optional, defaults to 5 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Extract required parameters
        ip = data.get('ip', '').strip()
        community = data.get('community', '').strip()
        oids = data.get('oids', [])
        
        # Extract optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 5)
        
        # Validate required parameters
        if not ip:
            return jsonify({
                'success': False,
                'error': 'IP address is required'
            }), 400
            
        if not community:
            return jsonify({
                'success': False,
                'error': 'Community string is required'
            }), 400
            
        if not oids or not isinstance(oids, list):
            return jsonify({
                'success': False,
                'error': 'OIDs list is required'
            }), 400
        
        # Validate IP address format
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        # Validate each OID
        for oid in oids:
            if not validate_oid(oid):
                return jsonify({
                    'success': False,
                    'error': f'Invalid OID format: {oid}'
                }), 400
        
        # Limit number of OIDs to prevent abuse
        if len(oids) > 50:
            return jsonify({
                'success': False,
                'error': 'Too many OIDs (maximum 50 allowed)'
            }), 400
        
        # Validate timeout
        try:
            timeout = int(timeout)
            if timeout < 1 or timeout > 30:
                timeout = 5
        except (ValueError, TypeError):
            timeout = 5
        
        # Execute SNMP GET for each OID
        results = {}
        success_count = 0
        
        for oid in oids:
            result = execute_snmpget(ip, community, oid, version, timeout)
            results[oid] = result
            if result['success']:
                success_count += 1
        
        return jsonify({
            'success': True,
            'data': {
                'ip': ip,
                'community': community,
                'total_oids': len(oids),
                'successful_oids': success_count,
                'failed_oids': len(oids) - success_count,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@service_bp.route('/snmp/test-connection', methods=['POST'])
@auth.login_required
def test_snmp_connection():
    """
    Test SNMP connection to a device
    Expected JSON payload:
    {
        "ip": "192.168.1.100",
        "community": "public",
        "version": "1",  // optional, defaults to 1
        "timeout": 5     // optional, defaults to 5 seconds
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Extract required parameters
        ip = data.get('ip', '').strip()
        community = data.get('community', '').strip()
        
        # Extract optional parameters
        version = data.get('version', '1')
        timeout = data.get('timeout', 5)
        
        # Validate required parameters
        if not ip:
            return jsonify({
                'success': False,
                'error': 'IP address is required'
            }), 400
            
        if not community:
            return jsonify({
                'success': False,
                'error': 'Community string is required'
            }), 400
        
        # Validate IP address format
        if not validate_ip(ip):
            return jsonify({
                'success': False,
                'error': 'Invalid IP address format'
            }), 400
        
        # Test with system uptime OID (commonly available)
        test_oid = '.1.3.6.1.2.1.1.3.0'
        result = execute_snmpget(ip, community, test_oid, version, timeout)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'SNMP connection successful',
                'data': {
                    'ip': ip,
                    'community': community,
                    'test_oid': test_oid,
                    'uptime': result['value'],
                    'timestamp': result['timestamp']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'SNMP connection failed: {result["error"]}',
                'data': {
                    'ip': ip,
                    'community': community,
                    'test_oid': test_oid
                }
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@service_bp.route('/snmp/info', methods=['GET'])
def snmp_info():
    """
    Get information about available SNMP OIDs for monitoring
    """
    snmp_oids = [
        {
            'oid': '.1.3.6.1.2.1.25.1.11',
            'name': 'pv1_voltage',
            'label': 'PV1 Voltage',
            'unit': 'V',
            'description': 'Photovoltaic 1 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.12',
            'name': 'pv2_voltage',
            'label': 'PV2 Voltage',
            'unit': 'V',
            'description': 'Photovoltaic 2 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.13',
            'name': 'pv1_current',
            'label': 'PV1 Current',
            'unit': 'A',
            'description': 'Photovoltaic 1 current measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.14',
            'name': 'pv2_current',
            'label': 'PV2 Current',
            'unit': 'A',
            'description': 'Photovoltaic 2 current measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.15',
            'name': 'batt1_voltage',
            'label': 'Battery 1 Voltage',
            'unit': 'V',
            'description': 'Battery 1 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.16',
            'name': 'batt2_voltage',
            'label': 'Battery 2 Voltage',
            'unit': 'V',
            'description': 'Battery 2 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.17',
            'name': 'arus1',
            'label': 'Current 1',
            'unit': 'A',
            'description': 'Current 1 measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.18',
            'name': 'arus2',
            'label': 'Current 2',
            'unit': 'A',
            'description': 'Current 2 measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.19',
            'name': 'lvd1',
            'label': 'LVD 1',
            'unit': '',
            'description': 'Low Voltage Disconnect 1 status'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.20',
            'name': 'lvd2',
            'label': 'LVD 2',
            'unit': '',
            'description': 'Low Voltage Disconnect 2 status'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.21',
            'name': 'pv3_current',
            'label': 'PV3 Current',
            'unit': 'A',
            'description': 'Photovoltaic 3 current measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.22',
            'name': 'pv3_voltage',
            'label': 'PV3 Voltage',
            'unit': 'V',
            'description': 'Photovoltaic 3 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.23',
            'name': 'batt3_voltage',
            'label': 'Battery 3 Voltage',
            'unit': 'V',
            'description': 'Battery 3 voltage measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.24',
            'name': 'arus3',
            'label': 'Current 3',
            'unit': 'A',
            'description': 'Current 3 measurement'
        },
        {
            'oid': '.1.3.6.1.2.1.25.1.25',
            'name': 'lvd3',
            'label': 'LVD 3',
            'unit': '',
            'description': 'Low Voltage Disconnect 3 status'
        }
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'total_oids': len(snmp_oids),
            'oids': snmp_oids,
            'supported_versions': ['1', '2c'],
            'default_community': 'public',
            'default_timeout': 5
        }
    })
