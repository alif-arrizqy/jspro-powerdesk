import json
import sqlite3
import os
from datetime import datetime, timedelta
from flask import jsonify, request
from . import monitoring_bp
from ..redisconnection import connection as red
from auths import token_auth as auth
from config import number_of_scc, slave_ids, PATH

# Import battery configuration for section filtering
try:
    from config import battery_type as default_battery_type
except ImportError:
    default_battery_type = 'talis5'


def get_battery_port_configuration():
    """
    Get battery port configuration based on device settings
    Returns list of active USB ports
    """
    try:
        # Get device configuration from Redis
        device_config = red.hget('device_config', 'device_version')
        if device_config:
            device = json.loads(device_config)
            battery_type = device.get('battery_type', 'mix')
        else:
            # Fallback to checking bms_system_info
            bms_info = red.hget('bms_system_info', 'battery_type')
            battery_type = bms_info.decode('utf-8') if bms_info else 'mix'
        
        # Determine active ports based on battery type
        if battery_type == 'talis5':
            # Talis5 typically uses both USB ports
            active_ports = ['usb0', 'usb1']
        else:
            # Mix and other types typically use only USB0
            active_ports = ['usb0']
        
        # Verify which ports actually have active data
        verified_ports = []
        for port in active_ports:
            # Check if there's any active data for this port
            active_data = red.hgetall(f'bms_active_{port}')
            if active_data:
                verified_ports.append(port)
        
        # If no verified ports found, fallback to usb0
        return verified_ports if verified_ports else ['usb0']
        
    except Exception as e:
        print(f"Error getting battery port configuration: {e}")
        # Fallback to default configuration
        return ['usb0']


def get_redis_keys_for_section(section=None):
    """
    Get appropriate Redis keys based on section parameter
    
    Args:
        section: Battery section (talis5, jspro, mix) or None for default
        
    Returns:
        dict: Dictionary with key patterns for different data types
    """
    if section is None:
        section = default_battery_type
    
    if section == 'talis5':
        return {
            'bms_pattern': 'bms_usb*',
            'active_pattern': 'bms_active_*',
            'ports': ['usb0', 'usb1']
        }
    elif section == 'jspro':
        return {
            'bms_pattern': 'jspro_battery_*',
            'active_pattern': 'jspro_active_*',
            'ports': []  # JSPro doesn't use USB ports
        }
    elif section == 'mix':
        return {
            'bms_pattern': ['bms_usb*', 'jspro_battery_*'],
            'active_pattern': ['bms_active_*', 'jspro_active_*'],
            'ports': ['usb0', 'usb1']
        }
    else:
        # Default fallback to talis5
        return {
            'bms_pattern': 'bms_usb*',
            'active_pattern': 'bms_active_*',
            'ports': ['usb0', 'usb1']
        }

@monitoring_bp.route('/scc', methods=['GET'])
@auth.login_required
def get_scc_monitoring():
    """Get SCC (Solar Charge Controller) monitoring data"""
    try:
        scc_data = {}
        relay_configuration = {}

        # Get SCC data for each controller
        for no in range(1, number_of_scc + 1):
            scc_key = f"scc{no}"
            scc_data[scc_key] = {}

            try:
                # Basic SCC data
                scc_data[scc_key]['scc_id'] = no
                scc_data[scc_key]['counter_heartbeat'] = int(red.hget(scc_key, 'counter_heartbeat') or -1)
                scc_data[scc_key]['pv_voltage'] = float(red.hget(scc_key, 'pv_voltage') or -1)
                scc_data[scc_key]['pv_current'] = float(red.hget(scc_key, 'pv_current') or -1)
                scc_data[scc_key]['load_voltage'] = float(red.hget(scc_key, 'load_voltage') or -1)
                scc_data[scc_key]['load_current'] = float(red.hget(scc_key, 'load_current') or -1)
                scc_data[scc_key]['load_power'] = float(red.hget(scc_key, 'load_power') or -1)

                # Temperature data
                scc_data[scc_key]['battery_temperature'] = float(red.hget(scc_key, 'battery_temperature') or -1)
                scc_data[scc_key]['device_temperature'] = float(red.hget(scc_key, 'device_temperature') or -1)

                # Load status
                load_status_value = int(red.hget(scc_key, "load_status") or -1)
                if load_status_value == 1:
                    scc_data[scc_key]['load_status'] = "is running"
                elif load_status_value == 0:
                    scc_data[scc_key]['load_status'] = "is standby"
                else:
                    scc_data[scc_key]['load_status'] = "modbus error"

                # Alarm status
                try:
                    alarm_data = red.hget(f"{scc_key}_alarm", "alarm")
                    if alarm_data:
                        # Handle different data formats
                        if isinstance(alarm_data, bytes):
                            alarm_data = alarm_data.decode('utf-8')
                        
                        # Try to parse as JSON first
                        try:
                            scc_data[scc_key]['alarm_status'] = json.loads(alarm_data)
                        except json.JSONDecodeError:
                            # If it's a string representation of a dict, use eval safely
                            try:
                                # Use ast.literal_eval for safe evaluation of string literals
                                import ast
                                scc_data[scc_key]['alarm_status'] = ast.literal_eval(alarm_data)
                            except (ValueError, SyntaxError):
                                # If all else fails, return as string for debugging
                                scc_data[scc_key]['alarm_status'] = {"raw_data": alarm_data}
                    else:
                        scc_data[scc_key]['alarm_status'] = {}
                except Exception as e:
                    print(f"Error parsing alarm data for {scc_key}: {e}")
                    scc_data[scc_key]['alarm_status'] = {}

            except Exception as e:
                print(f"Error retrieving data for {scc_key}: {e}")
                scc_data[scc_key] = {
                    'scc_id': no,
                    'error': f"Failed to retrieve data for {scc_key}"
                }

        # Get relay configuration
        relay_configuration = {}
        
        try:
            device_data = red.hgetall("device_config")
            handle_relay_data = device_data.get("handle_relay", "{}")
            
            if isinstance(handle_relay_data, str):
                relay_configuration = json.loads(handle_relay_data)
                relay_configuration = {
                    "vsat_reconnect": relay_configuration.get("voltage_reconnect_vsat", 'N/A'),
                    "vsat_cutoff": relay_configuration.get("voltage_cutoff_vsat", 'N/A'),
                    "bts_reconnect": relay_configuration.get("voltage_reconnect_bts", 'N/A'),
                    "bts_cutoff": relay_configuration.get("voltage_cutoff_bts", 'N/A')
                }
            else:
                relay_configuration = relay_configuration or {}
        except Exception as e:
            relay_configuration = {
                "vsat_reconnect": 'N/A',
                "vsat_cutoff": 'N/A',
                "bts_reconnect": 'N/A',
                "bts_cutoff": 'N/A'
            }
        
        response_data = scc_data.copy()
        response_data['relay_configuration'] = relay_configuration
        response_data['last_update'] = str(red.hget('scc_system_info', 'last_update'))

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200

    except Exception as e:
        print(f"Error getting SCC monitoring data: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error",
            "data": None
        }), 500


@monitoring_bp.route('/scc/chart', methods=['GET'])
@auth.login_required
def get_scc_chart_data():
    """Get SCC power generation data for chart from SQLite database"""
    try:
        # Path to SQLite database
        db_path = f"{PATH}/database/data_storage.db"

        # Check if database exists
        if not os.path.exists(db_path):
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": "Database not found",
                "data": None
            }), 404

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Calculate timestamp for 24 hours ago
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        # Query loggers_scc data for the last 24 hours
        cursor.execute("""
            SELECT 
                timestamp, battery_voltage
            FROM loggers_scc 
            WHERE timestamp >= ? 
            ORDER BY timestamp ASC
        """, (twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Process data for chart
        chart_data = {
            "datasets": [],
            "labels": []
        }
        
        # Initialize datasets for each SCC
        for i in range(1, number_of_scc + 1):
            chart_data["datasets"].append({
                "data": [],
                "label": f"SCC {i} Battery (V)"
            })
        
        # Process each row
        for row in rows:
            timestamp = row[0]
            battery_voltage = row[1] if row[1] and row[1] != -1 else 0
            
            # Parse datetime and format for chart label
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                time_label = dt.strftime('%H:%M')
                chart_data["labels"].append(time_label)
                
                # Add battery voltage to each SCC dataset
                for i in range(number_of_scc):
                    chart_data["datasets"][i]["data"].append(battery_voltage)
                
            except ValueError as e:
                print(f"Error parsing datetime: {e}")
                continue
        
        # If no data found, return empty chart with time labels
        if not chart_data["labels"]:
            now = datetime.now()
            for i in range(24, 0, -1):
                time_point = now - timedelta(hours=i)
                chart_data["labels"].append(time_point.strftime('%H:%M'))
        
        # Calculate total data points (labels * datasets)
        data_points = len(chart_data["labels"]) * number_of_scc
        
        response_data = {
            "chart_data": chart_data,
            "data_points": data_points,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query_time": twenty_four_hours_ago.strftime("%Y-%m-%d %H:%M:%S"),
            "scc_count": number_of_scc
        }

        return jsonify({
            "data": response_data,
            "status": "success",
            "status_code": 200
        }), 200

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return jsonify({
            "data": None,
            "status": "error",
            "status_code": 500,
            "message": f"Database error: {str(e)}"
        }), 500
        
    except Exception as e:
        print(f"Error getting SCC chart data: {e}")
        return jsonify({
            "data": None,
            "status": "error",
            "status_code": 500,
            "message": "Internal server error"
        }), 500


@monitoring_bp.route('/rectifier', methods=['GET'])
@auth.login_required
def get_rectifier_monitoring():
    """Get rectifier monitoring data from Redis"""
    try:
        # Get all rectifier data from Redis hash
        rectifier_data = red.hgetall('rectifier')
        
        if not rectifier_data:
            return jsonify({
                'status_code': 200,
                'status': 'success',
                'message': 'No rectifier data available',
                'data': {
                    'rectifier_data': {},
                    'last_update': None,
                    'status': 'no_data'
                }
            })
        
        # Process and format rectifier data
        formatted_data = {}
        status_mapping = {
            'hwAcInputStatus': { 0: 'No Alarm', 1: 'Alarm' },
            'hwRectifierStatus': { 0: 'No Alarm', 1: 'Alarm' },
            'hwBatteryDischarge': { 0: 'No Alarm', 1: 'Alarm' },
            'hwBatteryLowVoltage': { 0: 'No Alarm', 1: 'Alarm' },
            'hwBatteryUltraLowVoltage': { 0: 'No Alarm', 1: 'Alarm' },
            'hwBatteryDisconnect': { 0: 'No Alarm', 1: 'Alarm' },
            'hwFuseBroken': { 0: 'No Alarm', 1: 'Alarm' },
            'hwLoadFuseAlarmTraps': { 0: 'No Alarm', 1: 'Alarm' },
            'hwTcucDoorOpenAlarmTraps': { 0: 'Closed', 1: 'Open' },
            'hwEsduDoorOpenAlarmTraps': { 0: 'Closed', 1: 'Open' }
        }
        
        # Define units for each parameter
        units = {
            'hwRectACVoltage': 'V',
            'hwBatteryVoltage': 'V', 
            'hwRectifierTemperature': '°C'
        }
        
        # Process each field from Redis
        for key, value in rectifier_data.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
                
            # Convert numeric values
            try:
                numeric_value = float(value)
                
                # Apply status mapping for status fields
                if key in status_mapping:
                    formatted_data[key] = {
                        'value': numeric_value,
                        'unit': units.get(key, ''),
                    }
                else:
                    formatted_data[key] = {
                        'value': numeric_value,
                        'unit': units.get(key, ''),
                    }
            except (ValueError, TypeError):
                # Handle non-numeric values
                formatted_data[key] = {
                    'value': value,
                    'unit': '',
                }
        
        # Get last update timestamp
        last_update = red.hget('rectifier', 'last_update')
        if last_update:
            last_update = last_update.decode('utf-8') if isinstance(last_update, bytes) else last_update
        
        response_data = {
            'rectifier_data': formatted_data,
            'last_update': last_update or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_parameters': len(formatted_data),
        }
        
        return jsonify({
            'status_code': 200,
            'status': 'success',
            'message': 'Rectifier monitoring data retrieved successfully',
            'data': response_data
        })

    except Exception as e:
        print(f"Error getting rectifier monitoring data: {e}")
        return jsonify({
            'status_code': 500,
            'status': 'error',
            'message': f'Failed to retrieve rectifier monitoring data: {str(e)}',
            'data': None
        }), 500


@monitoring_bp.route('/battery', methods=['GET'])
@auth.login_required
def get_battery_monitoring():
    """
    Get battery monitoring data from Redis based on section configuration
    Query parameters:
    - section: Battery section (talis5, jspro, mix) for filtering data
    """
    try:
        # Parse query parameters
        section = request.args.get('section')
        
        bms_data = []
        active_slaves_config = {}
        
        # Get section-specific Redis key configuration
        redis_keys = get_redis_keys_for_section(section)
        
        # First, read bms_active_slaves configuration
        try:
            if section == 'jspro':
                # For JSPro, only include active docks (status = 1) like /battery/active
                ports_config = _get_jspro_active_ports_config()
                last_update = str(red.hget('dock_active', 'last_update') or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                # For talis5 and mix, get active batteries from Redis bms_active data
                if section == 'talis5':
                    # Talis5: Get active batteries from both USB ports (up to 10 each)
                    ports_config = {}
                    
                    for usb_port in ['usb0', 'usb1']:
                        try:
                            # Get active data from Redis for this USB port
                            bms_active_data = red.hgetall(f'bms_active_{usb_port}')
                            active_slaves = []
                            
                            if bms_active_data:
                                # Check each slave_id (1-10) for active status
                                for slave_id in range(1, 11):  # Talis5 has up to 10 slaves per USB
                                    slave_key = f"slave_id_{slave_id}"
                                    status_value = bms_active_data.get(slave_key) or bms_active_data.get(slave_key.encode('utf-8'))
                                    
                                    if status_value is not None:
                                        # Convert to boolean (handle bytes/string)
                                        if isinstance(status_value, bytes):
                                            status_value = status_value.decode('utf-8')
                                        
                                        try:
                                            if bool(int(status_value)):  # Only include if status is true
                                                active_slaves.append(slave_id)
                                        except (ValueError, TypeError):
                                            continue
                            
                            if active_slaves:
                                ports_config[usb_port] = active_slaves
                                
                        except Exception as e:
                            print(f"Error reading {usb_port} active data: {e}")
                            continue
                    
                    # If no active slaves found, fallback to empty config
                    if not ports_config:
                        ports_config = {}
                        
                elif section == 'mix':
                    # Mix: Get only active batteries from both Talis5 and JSPro
                    ports_config = _get_mix_active_ports_config()
                else:
                    # Default fallback using existing configuration
                    active_slaves_data = red.hget('bms_active_slaves', 'status')
                    
                    if active_slaves_data:
                        # Parse the JSON data
                        if isinstance(active_slaves_data, bytes):
                            active_slaves_data = active_slaves_data.decode('utf-8')
                        
                        active_slaves_config = json.loads(active_slaves_data)
                        ports_config = active_slaves_config.get('ports', {})
                    else:
                        # Fallback to get active ports configuration
                        active_ports = redis_keys['ports']
                        ports_config = {}
                        for port in active_ports:
                            ports_config[port] = list(range(1, slave_ids + 1))
                
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing active slaves configuration: {e}")
            # Fallback to section-based port configuration
            if section == 'jspro':
                ports_config = {'dock': []}  # JSPro: empty dock list if error (no active docks)
            elif section == 'talis5':
                # Fallback: empty config for Talis5 (will show no batteries if Redis fails)
                ports_config = {}
            elif section == 'mix':
                # Fallback: empty config for mix mode (will show no batteries if Redis fails)
                ports_config = {}
            else:
                active_ports = redis_keys['ports']
                ports_config = {}
                for port in active_ports:
                    ports_config[port] = list(range(1, slave_ids + 1))
            last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get BMS data from each active port/dock and slave based on configuration
        for port_or_dock, active_slave_list in ports_config.items():
            try:
                # Get data for each active slave ID on this port/dock
                for slave_id in active_slave_list:
                    if section == 'jspro' or (section == 'mix' and port_or_dock == 'dock'):
                        # For JSPro or JSPro part in mix mode, use individual pms keys (pms0, pms1, etc.)
                        pms_key = f"pms{slave_id}"
                        bms_data_raw = red.hgetall(pms_key)
                        
                        if bms_data_raw:
                            # Convert JSPro data format to standard BMS format
                            jspro_data = {
                                'slave_id': slave_id,
                                'port': 'N/A',
                                'dock': slave_id,  # Add dock identifier for JSPro
                                'pack_voltage': int(float(bms_data_raw.get('voltage', 0)) if bms_data_raw.get('voltage') else 0),
                                'pack_current': int(float(bms_data_raw.get('current', 0)) if bms_data_raw.get('current') else 0),
                                'cmos_state': bms_data_raw.get('cmos_state', 'OFF') if bms_data_raw.get('cmos_state') else 'OFF',
                                'dmos_state': bms_data_raw.get('dmos_state', 'OFF') if bms_data_raw.get('dmos_state') else 'OFF',
                                'temp_top': int(float(bms_data_raw.get('temp_top', 0)) if bms_data_raw.get('temp_top') else 0),
                                'temp_mid': int(float(bms_data_raw.get('temp_mid', 0)) if bms_data_raw.get('temp_mid') else 0),
                                'temp_bot': int(float(bms_data_raw.get('temp_bot', 0)) if bms_data_raw.get('temp_bot') else 0),
                                'temp_cmos': int(float(bms_data_raw.get('temp_cmos', 0)) if bms_data_raw.get('temp_cmos') else 0),
                                'temp_dmos': int(float(bms_data_raw.get('temp_dmos', 0)) if bms_data_raw.get('temp_dmos') else 0),
                                'cell_voltage': [],
                                'section': section or default_battery_type,
                                'battery_type': 'jspro',  # Add battery type identifier
                                'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Extract cell voltages (cell1_v to cell14_v for JSPro)
                            for cell_num in range(1, 15):  # JSPro has 14 cells
                                cell_key = f'cell{cell_num}_v'
                                cell_voltage = int(float(bms_data_raw.get(cell_key, 0)) if bms_data_raw.get(cell_key) else 0)
                                jspro_data['cell_voltage'].append(cell_voltage)
                            
                            # Calculate max, min, and difference
                            active_cells = [v for v in jspro_data['cell_voltage'] if v > 0]
                            if active_cells:
                                jspro_data['max_cell_voltage'] = max(active_cells)
                                jspro_data['min_cell_voltage'] = min(active_cells)
                                jspro_data['cell_difference'] = jspro_data['max_cell_voltage'] - jspro_data['min_cell_voltage']
                            else:
                                jspro_data['max_cell_voltage'] = 0
                                jspro_data['min_cell_voltage'] = 0
                                jspro_data['cell_difference'] = 0
                            
                            bms_data.append(jspro_data)
                    else:
                        # For talis5 and talis5 part in mix mode, use port-based keys
                        bms_data_json = red.hget(f"bms_{port_or_dock}", f"slave_id_{slave_id}")
                        
                        if bms_data_json:
                            try:
                                bms_logger = json.loads(bms_data_json)
                                
                                # Only include data that has pcb_code
                                if 'pcb_code' in bms_logger and bms_logger['pcb_code']:
                                    # Clean pcb_code
                                    bms_logger['pcb_code'] = str(bms_logger['pcb_code']).strip()
                                    
                                    # Add port/dock information
                                    bms_logger['port'] = port_or_dock
                                    bms_logger['section'] = section or default_battery_type
                                    bms_logger['battery_type'] = 'talis5'  # Add battery type identifier
                                    
                                    bms_data.append(bms_logger)
                                    
                            except json.JSONDecodeError as e:
                                print(f"Error parsing BMS data for {port_or_dock} slave {slave_id}: {e}")
                            
            except Exception as e:
                print(f"Error processing {port_or_dock}: {e}")
        
        # Structure bms_data by battery type (same as /battery/active endpoint)
        structured_bms_data = {}
        
        if section == 'talis5':
            # For talis5 section, only include talis5 data
            talis5_data = [item for item in bms_data if item.get('battery_type') == 'talis5']
            if talis5_data:
                structured_bms_data['talis5'] = talis5_data
        elif section == 'jspro':
            # For jspro section, only include jspro data
            jspro_data = [item for item in bms_data if item.get('battery_type') == 'jspro']
            if jspro_data:
                structured_bms_data['jspro'] = jspro_data
        elif section == 'mix':
            # For mix section, include both talis5 and jspro data
            talis5_data = [item for item in bms_data if item.get('battery_type') == 'talis5']
            jspro_data = [item for item in bms_data if item.get('battery_type') == 'jspro']
            
            if talis5_data:
                structured_bms_data['talis5'] = talis5_data
            if jspro_data:
                structured_bms_data['jspro'] = jspro_data
        else:
            # For other sections, group by battery_type if available
            battery_types = {}
            for item in bms_data:
                battery_type = item.get('battery_type', 'unknown')
                if battery_type not in battery_types:
                    battery_types[battery_type] = []
                battery_types[battery_type].append(item)
            structured_bms_data = battery_types
        
        response_data = {
            "bms_data": structured_bms_data,
            "section": section or default_battery_type,
            "pack_active": ports_config,
            "last_update": last_update
        }

        return jsonify({
            "status_code": 200,
            "status": "success", 
            "data": response_data
        }), 200

    except Exception as e:
        print(f"Error getting battery monitoring data: {e}")
        return jsonify({
            "status_code": 500,
            "message": f"Internal server error: {str(e)}",
            "data": None
        }), 500


@monitoring_bp.route('/battery/active', methods=['GET'])
@auth.login_required
def get_battery_monitoring_active():
    """
    Get active battery monitoring data based on section configuration
    Query parameters:
    - section: Battery section (talis5, jspro, mix) for filtering data
    """
    try:
        # Parse query parameters
        section = request.args.get('section')
        
        bms_data = []
        slave_mapping = {}  # Store mapping for Talis5: response_slave_id -> (usb_port, original_slave_id)
        
        # Get Battery Voltage
        try:
            battery_voltage = int(red.hget('avg_volt', 'voltage'))
        except Exception as e:
            print(f"Error getting battery voltage: {e}")
            battery_voltage = 'N/A'
        
        # Get section-specific Redis key configuration
        redis_keys = get_redis_keys_for_section(section)
        
        # Get active slaves configuration from Redis
        last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            ports_config = {}
            
            if section == 'jspro':
                ports_config = _get_jspro_ports_config()
            elif section == 'talis5':
                # Use the specific logic for Talis5 from bms_active_slaves
                active_slaves_data = red.hget('bms_active_slaves', 'status')
                if active_slaves_data:
                    # Parse the JSON data
                    if isinstance(active_slaves_data, bytes):
                        active_slaves_data = active_slaves_data.decode('utf-8')
                    
                    active_slaves_config = json.loads(active_slaves_data)
                    ports_config = active_slaves_config.get('ports', {})
                    last_update = active_slaves_config.get('last_update', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    # Fallback to empty configuration
                    ports_config = {}
            elif section == 'mix':
                ports_config = _get_mix_ports_config()
            else:
                ports_config = _get_default_ports_config(redis_keys)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing active slaves configuration: {e}")
            ports_config = _get_fallback_ports_config(section, redis_keys)
        
        # Process data based on section type
        if section == 'talis5':
            # Use the specific logic for Talis5
            for port, active_slave_list in ports_config.items():
                try:
                    # Get BMS active data for this port
                    bms_active_data = red.hgetall(f'bms_active_{port}')
                    
                    # Process all slaves (both active and inactive) for this port
                    for slave_id in active_slave_list:
                        slave_key = f"slave_id_{slave_id}"
                        
                        # Get status from Redis (handle both string and bytes)
                        status_value = bms_active_data.get(slave_key) or bms_active_data.get(slave_key.encode('utf-8'))
                        
                        if status_value is not None:
                            # Convert to boolean (handle bytes/string)
                            if isinstance(status_value, bytes):
                                status_value = status_value.decode('utf-8')
                            
                            try:
                                status = bool(int(status_value))
                            except (ValueError, TypeError):
                                status = False
                        else:
                            status = False
                        
                        bms_info = {
                            "slave_id": slave_id,
                            "port": port,
                            "status": status,
                            "section": "talis5",
                            "battery_type": "talis5"
                        }
                        bms_data.append(bms_info)
                        
                except Exception as e:
                    print(f"Error processing port {port}: {e}")
                    # Add error entries for this port's slaves
                    for slave_id in active_slave_list:
                        bms_info = {
                            "slave_id": slave_id,
                            "port": port,
                            "status": False,
                            "section": "talis5",
                            "battery_type": "talis5",
                            "error": f"Failed to read data for port {port}"
                        }
                        bms_data.append(bms_info)
        elif section == 'mix':
            # For mix mode, process Talis5 using the specific logic
            try:
                active_slaves_data = red.hget('bms_active_slaves', 'status')
                if active_slaves_data:
                    # Parse the JSON data
                    if isinstance(active_slaves_data, bytes):
                        active_slaves_data = active_slaves_data.decode('utf-8')
                    
                    active_slaves_config = json.loads(active_slaves_data)
                    talis5_ports_config = active_slaves_config.get('ports', {})
                else:
                    talis5_ports_config = {}
                
                # Process Talis5 part in mix mode
                for port, active_slave_list in talis5_ports_config.items():
                    try:
                        # Get BMS active data for this port
                        bms_active_data = red.hgetall(f'bms_active_{port}')
                        
                        # Process all slaves (both active and inactive) for this port
                        for slave_id in active_slave_list:
                            slave_key = f"slave_id_{slave_id}"
                            
                            # Get status from Redis (handle both string and bytes)
                            status_value = bms_active_data.get(slave_key) or bms_active_data.get(slave_key.encode('utf-8'))
                            
                            if status_value is not None:
                                # Convert to boolean (handle bytes/string)
                                if isinstance(status_value, bytes):
                                    status_value = status_value.decode('utf-8')
                                
                                try:
                                    status = bool(int(status_value))
                                except (ValueError, TypeError):
                                    status = False
                            else:
                                status = False
                            
                            bms_info = {
                                "slave_id": slave_id,
                                "port": port,
                                "status": status,
                                "section": "talis5",
                                "battery_type": "talis5"
                            }
                            bms_data.append(bms_info)
                            
                    except Exception as e:
                        print(f"Error processing Talis5 port {port} in mix mode: {e}")
                        # Add error entries for this port's slaves
                        for slave_id in active_slave_list:
                            bms_info = {
                                "slave_id": slave_id,
                                "port": port,
                                "status": False,
                                "section": "talis5",
                                "battery_type": "talis5",
                                "error": f"Failed to read data for port {port}"
                            }
                            bms_data.append(bms_info)
            except Exception as e:
                print(f"Error processing Talis5 in mix mode: {e}")
            
            # Add JSPro data for mix mode
            jspro_data = _process_mix_jspro_data()
            bms_data.extend(jspro_data)
        else:
            # For JSPro and other sections, use standard processing
            bms_data = _process_standard_data(section, ports_config)

        # Prepare response with structured bms_data by battery type
        response_section = _get_response_section(section)
        
        # Structure bms_data by battery type
        structured_bms_data = {}
        
        if section == 'talis5':
            # For talis5 section, only include talis5 data
            talis5_data = [item for item in bms_data if item.get('battery_type') == 'talis5' or item.get('section') == 'talis5']
            if talis5_data:
                structured_bms_data['talis5'] = talis5_data
        elif section == 'jspro':
            # For jspro section, only include jspro data
            jspro_data = [item for item in bms_data if item.get('battery_type') == 'jspro' or item.get('section') == 'jspro']
            if jspro_data:
                structured_bms_data['jspro'] = jspro_data
        elif section == 'mix':
            # For mix section, include both talis5 and jspro data
            talis5_data = [item for item in bms_data if item.get('battery_type') == 'talis5' or item.get('section') == 'talis5']
            jspro_data = [item for item in bms_data if item.get('battery_type') == 'jspro' or item.get('section') == 'jspro']
            
            if talis5_data:
                structured_bms_data['talis5'] = talis5_data
            if jspro_data:
                structured_bms_data['jspro'] = jspro_data
        else:
            # For other sections, group by battery_type if available, otherwise use flat structure
            battery_types = {}
            for item in bms_data:
                battery_type = item.get('battery_type', 'unknown')
                if battery_type not in battery_types:
                    battery_types[battery_type] = []
                battery_types[battery_type].append(item)
            structured_bms_data = battery_types
        
        response_data = {
            "battery_voltage": battery_voltage,
            "bms_data": structured_bms_data,
            "section": response_section,
            "last_update": last_update
        }

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200

    except Exception as e:
        print(f"Error getting active battery monitoring data: {e}")
        return jsonify({
            "status_code": 500,
            "message": f"Internal server error: {str(e)}",
            "data": None
        }), 500


def _get_jspro_ports_config():
    """Get ports configuration for JSPro section - show all docks (active and inactive)"""
    dock_active_data = red.hgetall('dock_active')
    if dock_active_data:
        # Parse JSPro dock_active data to get all pms list (regardless of status)
        all_pms_list = []
        for key, value in dock_active_data.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Include all pms regardless of status (active or inactive)
            if key.startswith('pms'):
                try:
                    pms_num = int(key[3:])  # Extract number from 'pmsX'
                    # For pms1-pms16, use direct mapping (no conversion needed)
                    if pms_num >= 1 and pms_num <= 16:
                        all_pms_list.append(pms_num)  # Direct mapping: pms1 -> slave_id 1
                except ValueError:
                    continue
        
        # Sort the list to ensure proper order
        all_pms_list.sort()
        return {'dock': all_pms_list}
    else:
        # No dock_active data found, return all possible docks (1-16)
        return {'dock': list(range(1, 17))}


def _get_jspro_active_ports_config():
    """Get ports configuration for JSPro section - show only active docks (status = 1)"""
    dock_active_data = red.hgetall('dock_active')
    if dock_active_data:
        # Parse JSPro dock_active data to get only active pms list (status = 1)
        active_pms_list = []
        for key, value in dock_active_data.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Include only pms with status = 1 (active)
            if key.startswith('pms'):
                try:
                    pms_num = int(key[3:])  # Extract number from 'pmsX'
                    # For pms1-pms16, use direct mapping (no conversion needed)
                    if pms_num >= 1 and pms_num <= 16:
                        # Check if status is 1 (active)
                        try:
                            status = bool(int(value))
                            if status:  # Only include if status is True/1
                                active_pms_list.append(pms_num)  # Direct mapping: pms1 -> slave_id 1
                        except (ValueError, TypeError):
                            continue
                except ValueError:
                    continue
        
        # Sort the list to ensure proper order
        active_pms_list.sort()
        return {'dock': active_pms_list}
    else:
        # No dock_active data found, return empty (no active docks)
        return {'dock': []}


def _get_mix_ports_config():
    """Get ports configuration for mix section"""
    ports_config = {}
    
    for usb_port in ['usb0', 'usb1']:
        try:
            # Get active data from Redis for this USB port
            bms_active_data = red.hgetall(f'bms_active_{usb_port}')
            active_slaves = []
            
            if bms_active_data:
                # Check each slave_id (1-10) for active status
                for slave_id in range(1, 11):  # Talis5 has up to 10 slaves per USB
                    slave_key = f"slave_id_{slave_id}"
                    status_value = bms_active_data.get(slave_key) or bms_active_data.get(slave_key.encode('utf-8'))
                    
                    if status_value is not None:
                        # Convert to boolean (handle bytes/string)
                        if isinstance(status_value, bytes):
                            status_value = status_value.decode('utf-8')
                        
                        try:
                            if bool(int(status_value)):  # Only include if status is true
                                active_slaves.append(slave_id)
                        except (ValueError, TypeError):
                            continue
            
            if active_slaves:
                ports_config[usb_port] = active_slaves
                
        except Exception as e:
            print(f"Error reading {usb_port} active data: {e}")
            continue
    
    return ports_config


def _get_mix_active_ports_config():
    """Get ports configuration for mix section - only active batteries"""
    ports_config = {}
    
    # Get active Talis5 batteries
    for usb_port in ['usb0', 'usb1']:
        try:
            # Get active data from Redis for this USB port
            bms_active_data = red.hgetall(f'bms_active_{usb_port}')
            active_slaves = []
            
            if bms_active_data:
                # Check each slave_id (1-10) for active status
                for slave_id in range(1, 11):  # Talis5 has up to 10 slaves per USB
                    slave_key = f"slave_id_{slave_id}"
                    status_value = bms_active_data.get(slave_key) or bms_active_data.get(slave_key.encode('utf-8'))
                    
                    if status_value is not None:
                        # Convert to boolean (handle bytes/string)
                        if isinstance(status_value, bytes):
                            status_value = status_value.decode('utf-8')
                        
                        try:
                            if bool(int(status_value)):  # Only include if status is true
                                active_slaves.append(slave_id)
                        except (ValueError, TypeError):
                            continue
            
            if active_slaves:
                ports_config[usb_port] = active_slaves
                
        except Exception as e:
            print(f"Error reading {usb_port} active data: {e}")
            continue
    
    # Get active JSPro batteries
    dock_active_data = red.hgetall('dock_active')
    if dock_active_data:
        active_pms_list = []
        for key, value in dock_active_data.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Include only pms with status = 1 (active)
            if key.startswith('pms'):
                try:
                    pms_num = int(key[3:])  # Extract number from 'pmsX'
                    # For pms1-pms16, use direct mapping (no conversion needed)
                    if pms_num >= 1 and pms_num <= 16:
                        # Check if status is 1 (active)
                        try:
                            status = bool(int(value))
                            if status:  # Only include if status is True/1
                                active_pms_list.append(pms_num)  # Direct mapping: pms1 -> slave_id 1
                        except (ValueError, TypeError):
                            continue
                except ValueError:
                    continue
        
        if active_pms_list:
            active_pms_list.sort()
            ports_config['dock'] = active_pms_list
    
    return ports_config


def _get_default_ports_config(redis_keys):
    """Get default ports configuration"""
    active_slaves_data = red.hget('bms_active_slaves', 'status')
    
    if active_slaves_data:
        # Parse the JSON data
        if isinstance(active_slaves_data, bytes):
            active_slaves_data = active_slaves_data.decode('utf-8')
        
        active_slaves_config = json.loads(active_slaves_data)
        return active_slaves_config.get('ports', {})
    else:
        # Fallback to section-based configuration
        ports_config = {}
        for port in redis_keys['ports']:
            ports_config[port] = list(range(1, slave_ids + 1))
        return ports_config


def _get_fallback_ports_config(section, redis_keys):
    """Get fallback ports configuration when error occurs"""
    if section == 'jspro':
        return {'dock': []}  # JSPro: empty dock list if error (no active docks)
    elif section == 'talis5':
        return {}
    elif section == 'mix':
        return {}
    else:
        ports_config = {}
        for port in redis_keys['ports']:
            ports_config[port] = list(range(1, slave_ids + 1))
        return ports_config


def _process_standard_data(section, ports_config):
    """Process data for JSPro and other standard sections"""
    bms_data = []
    
    for port_or_dock, active_slave_list in ports_config.items():
        try:
            # Get BMS active data for this port/dock based on section
            if section == 'jspro':
                # For JSPro, use dock_active data for status information
                bms_active_data = red.hgetall('dock_active')
            else:
                bms_active_data = red.hgetall(f'bms_active_{port_or_dock}')
            
            # Process all slaves for this port/dock
            for slave_id in active_slave_list:
                if section == 'jspro':
                    bms_info = _process_jspro_slave(slave_id, port_or_dock, bms_active_data)
                else:
                    bms_info = _process_other_slave(slave_id, port_or_dock, section)
                
                bms_data.append(bms_info)
                
        except Exception as e:
            print(f"Error processing {port_or_dock}: {e}")
            # Add error entries for this port/dock's slaves
            for slave_id in active_slave_list:
                bms_info = {
                    "slave_id": slave_id,
                    "status": False,
                    "error": f"Failed to read data for {port_or_dock}"
                }
                
                if section == 'jspro':
                    bms_info["port"] = "N/A"
                    bms_info["battery_type"] = "jspro"
                    bms_info["section"] = "jspro"
                else:
                    bms_info["port"] = port_or_dock
                    bms_info["battery_type"] = section or default_battery_type
                    bms_info["section"] = section or default_battery_type
                bms_data.append(bms_info)
    
    return bms_data


def _process_jspro_slave(slave_id, port_or_dock, bms_active_data):
    """Process individual JSPro slave data"""
    # For JSPro, check pms status from dock_active
    # Use pms1-pms16 mapping directly with slave_id (1-16)
    pms_key = f"pms{slave_id}"  # Direct mapping: slave_id 1 -> pms1, slave_id 2 -> pms2, etc.
    status_value = bms_active_data.get(pms_key) or bms_active_data.get(pms_key.encode('utf-8'))
    
    if status_value is not None:
        # Convert to boolean (handle bytes/string)
        if isinstance(status_value, bytes):
            status_value = status_value.decode('utf-8')
        
        try:
            status = bool(int(status_value))
        except (ValueError, TypeError):
            status = False
    else:
        status = False
    
    # Dock number is same as slave_id for JSPro (1-16)
    dock_number = slave_id
    
    return {
        "port": "N/A",
        "battery_type": "jspro",
        "section": "jspro",
        "slave_id": slave_id,
        "dock": dock_number,  # Add dock information
        "status": status,
    }


def _process_other_slave(slave_id, port_or_dock, section):
    """Process individual slave data for non-JSPro sections"""
    return {
        "port": port_or_dock,
        "battery_type": section or default_battery_type,
        "section": section or default_battery_type,
        "slave_id": slave_id,
        "status": True,
    }


def _process_mix_jspro_data():
    """Process JSPro data for mix mode"""
    jspro_data = []
    
    try:
        # Get JSPro dock_active data
        dock_active_data = red.hgetall('dock_active')
        if dock_active_data:
            # Parse JSPro dock_active data to get all pms list (regardless of status)
            all_pms_list = []
            for key, value in dock_active_data.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                
                # Include all pms1-pms16 regardless of status (0 or 1)
                if key.startswith('pms'):
                    try:
                        pms_num = int(key[3:])  # Extract number from 'pmsX'
                        # For pms1-pms16, use direct mapping (no conversion needed)
                        if pms_num >= 1 and pms_num <= 16:
                            all_pms_list.append(pms_num)  # Direct mapping: pms1 -> slave_id 1
                    except ValueError:
                        continue
            
            # Sort the list to ensure proper order
            all_pms_list.sort()
            
            # Process JSPro batteries for mix mode
            for slave_id in all_pms_list:
                pms_key = f"pms{slave_id}"  # Direct mapping: slave_id 1 -> pms1, slave_id 2 -> pms2, etc.
                status_value = dock_active_data.get(pms_key) or dock_active_data.get(pms_key.encode('utf-8'))
                
                if status_value is not None:
                    # Convert to boolean (handle bytes/string)
                    if isinstance(status_value, bytes):
                        status_value = status_value.decode('utf-8')
                    
                    try:
                        status = bool(int(status_value))
                    except (ValueError, TypeError):
                        status = False
                else:
                    status = False
                
                bms_info = {
                    "port": 'dock',
                    "section": 'jspro',  # Mark as JSPro section within mix
                    "slave_id": slave_id,
                    "dock": slave_id,  # Add dock information
                    "status": status,
                    "battery_type": 'jspro'  # Additional identifier for mix mode
                }
                
                jspro_data.append(bms_info)
        else:
            # Fallback: add all 16 JSPro batteries as inactive
            for slave_id in range(1, 17):
                bms_info = {
                    "port": 'dock',
                    "section": 'jspro',
                    "slave_id": slave_id,
                    "status": False,
                    "battery_type": 'jspro'
                }
                jspro_data.append(bms_info)
                
    except Exception as e:
        print(f"Error processing JSPro batteries in mix mode: {e}")
        # Add error entries for JSPro batteries
        for slave_id in range(1, 17):
            bms_info = {
                "port": 'dock',
                "section": 'jspro',
                "slave_id": slave_id,
                "status": False,
                "battery_type": 'jspro',
                "error": "Failed to read JSPro data"
            }
            jspro_data.append(bms_info)
    
    return jspro_data


def _get_response_section(section):
    """Get correct section name for response"""
    if section == 'talis5':
        return 'talis5'  # Force talis5 regardless of default_battery_type
    elif not section:
        return default_battery_type
    else:
        return section
