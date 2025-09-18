import json
import sqlite3
import os
from datetime import datetime, timedelta
from flask import jsonify, request
from . import monitoring_bp
from ..redisconnection import connection as red
from auths import token_auth as auth
from config import number_of_scc, slave_ids, PATH


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
        # Path to SQLite database (adjust as needed)
        # db_path = "D:/sundaya/developments/ehub-developments/ehub_talis/ehub-talis/data_storage.db"
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
        
        # Get last 24 hours of energy data
        # Calculate timestamp for 24 hours ago
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        # Query energy data for the last 24 hours
        cursor.execute("""
            SELECT 
                collection_time, batt_volt
            FROM energy_data 
            WHERE collection_time >= ? 
            ORDER BY collection_time ASC
        """, (twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Process data for chart
        chart_data = {
            "labels": [],
            "datasets": []
        }
        
        # Initialize datasets for each SCC
        for i in range(1, number_of_scc + 1):
            chart_data["datasets"].append({
                "label": f"SCC {i} Battery (V)",
                "data": [],
            })
        
        # Process each row
        for row in rows:
            collection_time, batt_volt = row[0], row[1]
            
            # Parse datetime and format for chart label
            try:
                dt = datetime.strptime(collection_time, '%Y-%m-%d %H:%M:%S')
                time_label = dt.strftime('%H:%M')
                chart_data["labels"].append(time_label)
                
                # Calculate power from voltage * current for each SCC
                power_values = []
                voltage_values = []
                current_values = []
                
                # SCC 1
                if len(chart_data["datasets"]) >= 1:
                    power = batt_volt / 100 # Convert batt_volt to power in watts
                    chart_data["datasets"][0]["data"].append(round(power, 2))
                
                # SCC 2
                if len(chart_data["datasets"]) >= 2:
                    power = batt_volt / 100 # Convert batt_volt to power in watts
                    chart_data["datasets"][1]["data"].append(round(power, 2))
                
                # SCC 3
                if len(chart_data["datasets"]) >= 3:
                    power = batt_volt / 100 # Convert batt_volt to power in watts
                    chart_data["datasets"][2]["data"].append(round(power, 2))
                
            except ValueError as e:
                print(f"Error parsing datetime: {e}")
                continue
        
        # If no data found, generate dummy data for demonstration
        if not chart_data["labels"]:
            # Generate last 24 hours labels
            now = datetime.now()
            for i in range(24, 0, -1):
                time_point = now - timedelta(hours=i)
                chart_data["labels"].append(time_point.strftime('%H:%M'))
        
        response_data = {
            "chart_data": chart_data,
            "data_points": len(chart_data["labels"]),
            "query_time": twenty_four_hours_ago.strftime("%Y-%m-%d %H:%M:%S"),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": f"Database error: {str(e)}",
            "data": None
        }), 500
        
    except Exception as e:
        print(f"Error getting SCC chart data: {e}")
        return jsonify({
            "status_code": 500,
            "status": "error", 
            "message": "Internal server error",
            "data": None
        }), 500

@monitoring_bp.route('/battery', methods=['GET'])
@auth.login_required
def get_battery_monitoring():
    """Get battery monitoring data from Redis hget bms_usb* keys based on active slaves configuration"""
    try:
        bms_data = []
        active_slaves_config = {}
        
        # First, read bms_active_slaves configuration
        try:
            active_slaves_data = red.hget('bms_active_slaves', 'status')
            if active_slaves_data:
                # Parse the JSON data
                if isinstance(active_slaves_data, bytes):
                    active_slaves_data = active_slaves_data.decode('utf-8')
                
                active_slaves_config = json.loads(active_slaves_data)
                ports_config = active_slaves_config.get('ports', {})
                last_update = active_slaves_config.get('last_update', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                # Fallback to get active ports configuration
                active_ports = get_battery_port_configuration()
                ports_config = {}
                for port in active_ports:
                    ports_config[port] = list(range(1, slave_ids + 1))
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing active slaves configuration: {e}")
            # Fallback to get active ports configuration
            active_ports = get_battery_port_configuration()
            ports_config = {}
            for port in active_ports:
                ports_config[port] = list(range(1, slave_ids + 1))
            last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get BMS data from each active port and slave based on configuration
        for port, active_slave_list in ports_config.items():
            try:
                # Get data for each active slave ID on this port
                for slave_id in active_slave_list:
                    bms_data_json = red.hget(f"bms_{port}", f"slave_id_{slave_id}")
                    
                    if bms_data_json:
                        try:
                            bms_logger = json.loads(bms_data_json)
                            
                            # Only include data that has pcb_code
                            if 'pcb_code' in bms_logger and bms_logger['pcb_code']:
                                # Clean pcb_code
                                bms_logger['pcb_code'] = str(bms_logger['pcb_code']).strip()
                                
                                # Add port information
                                bms_logger['port'] = port
                                
                                bms_data.append(bms_logger)
                                
                        except json.JSONDecodeError as e:
                            print(f"Error parsing BMS data for {port} slave {slave_id}: {e}")
                            
            except Exception as e:
                print(f"Error processing port {port}: {e}")
        
        response_data = {
            "bms_data": bms_data,
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
    """Get active battery monitoring data based on bms_active_slaves configuration"""
    try:
        bms_data = []
        
        # Get Battery Voltage
        try:
            battery_voltage = int(red.hget('avg_volt', 'voltage'))
        except Exception as e:
            print(f"Error getting battery voltage: {e}")
            battery_voltage = 'N/A'
        
        # Get active slaves configuration from Redis
        try:
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
                last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing active slaves configuration: {e}")
            ports_config = {}
            last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Process each port from the configuration
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
                        "status": status
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
                        "error": f"Failed to read data for port {port}"
                    }
                    bms_data.append(bms_info)

        response_data = {
            "battery_voltage": battery_voltage,
            "bms_data": bms_data,
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

@monitoring_bp.route('/battery/chart', methods=['GET'])
@auth.login_required
def get_battery_chart_data():
    """Get battery monitoring data for chart from SQLite database by slave ID"""
    try:
        # Get query parameters
        slave_id = request.args.get('slave_id', type=int)
        hours = request.args.get('hours', 24, type=int)  # Default last 24 hours
        
        # Path to SQLite database
        db_path = f"{PATH}/database/data_storage.db"
        print(f"DEBUG: Database path: {db_path}")

        # Check if database exists
        if not os.path.exists(db_path):
            print(f"DEBUG: Database not found at: {db_path}")
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": "Database not found",
                "data": None
            }), 404

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Calculate timestamp for specified hours ago
        hours_ago = datetime.now() - timedelta(hours=hours)
        print(f"DEBUG: Querying data from: {hours_ago.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Build query based on whether slave_id is specified
        if slave_id:
            print(f"DEBUG: Querying for specific slave_id: {slave_id}")
            # Query for specific slave ID
            cursor.execute("""
                SELECT 
                    collection_time, slave_id, pcb_code, pack_voltage, 
                    pack_current, max_cell_voltage, min_cell_voltage,
                    cell_difference
                FROM bms_data 
                WHERE collection_time >= ? AND slave_id = ?
                ORDER BY collection_time ASC
            """, (hours_ago.strftime('%Y-%m-%d %H:%M:%S'), slave_id))
        else:
            print("DEBUG: Querying for all slave_ids")
            # Query for all slave IDs
            cursor.execute("""
                SELECT 
                    collection_time, slave_id, pcb_code, pack_voltage, 
                    pack_current, max_cell_voltage, min_cell_voltage,
                    cell_difference
                FROM bms_data 
                WHERE collection_time >= ?
                ORDER BY collection_time ASC, slave_id ASC
            """, (hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        
        rows = cursor.fetchall()
        print(f"DEBUG: Found {len(rows)} rows in database")
        
        # Debug: Print first few rows if any
        if rows:
            print(f"DEBUG: First row sample: {rows[0]}")
        else:
            # Check if table exists and has any data
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bms_data'")
            table_exists = cursor.fetchone()
            print(f"DEBUG: Table 'bms_data' exists: {table_exists is not None}")
            
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM bms_data")
                total_count = cursor.fetchone()[0]
                print(f"DEBUG: Total records in bms_data: {total_count}")
                
                cursor.execute("SELECT MAX(collection_time), MIN(collection_time) FROM bms_data")
                time_range = cursor.fetchone()
                print(f"DEBUG: Data time range: {time_range}")
        
        conn.close()
        
        # Process data for chart
        chart_data = {
            "labels": [],
            "datasets": {
                "pack_voltage": [],
                "pack_current": [],
                "max_cell_voltage": [],
                "min_cell_voltage": [],
                "cell_difference": []
            },
            "slave_data": {}
        }
        
        # Group data by slave_id
        slave_groups = {}
        time_labels = set()
        
        for row in rows:
            collection_time, s_id, pcb_code, pack_voltage, pack_current, max_cell_voltage, min_cell_voltage, cell_difference = row
            
            # Parse datetime and format for chart label
            try:
                dt = datetime.strptime(collection_time, '%Y-%m-%d %H:%M:%S')
                time_label = dt.strftime('%H:%M')
                time_labels.add(time_label)
                
                # Group by slave_id
                if s_id not in slave_groups:
                    slave_groups[s_id] = {
                        "pcb_code": pcb_code,
                        "data": [],
                        "pack_voltage": [],
                        "pack_current": [],
                        "max_cell_voltage": [],
                        "min_cell_voltage": [],
                        "cell_difference": []
                    }
                
                # Add data point
                data_point = {
                    "time": time_label,
                    "pack_voltage": round(float(pack_voltage or 0), 2),
                    "pack_current": round(float(pack_current or 0), 2),
                    "max_cell_voltage": (max_cell_voltage or 0),
                    "min_cell_voltage": (min_cell_voltage or 0),
                    "cell_difference": (cell_difference or 0),
                }
                
                slave_groups[s_id]["data"].append(data_point)
                slave_groups[s_id]["pack_voltage"].append(data_point["pack_voltage"])
                slave_groups[s_id]["pack_current"].append(data_point["pack_current"])
                slave_groups[s_id]["max_cell_voltage"].append(data_point["max_cell_voltage"])
                slave_groups[s_id]["min_cell_voltage"].append(data_point["min_cell_voltage"])
                slave_groups[s_id]["cell_difference"].append(data_point["cell_difference"])
                
            except ValueError as e:
                print(f"Error parsing datetime: {e}")
                continue
        
        print(f"DEBUG: Processed {len(slave_groups)} slave groups")
        
        # Sort time labels
        sorted_labels = sorted(list(time_labels))
        chart_data["labels"] = sorted_labels
        
        # Prepare datasets for chart visualization
        for s_id, slave_info in slave_groups.items():
            pcb_code = slave_info["pcb_code"] or f"Slave_{s_id}"
            
            chart_data["datasets"]["pack_voltage"].append({
                "label": f"{pcb_code} - Pack Voltage (V)",
                "slave_id": s_id,
                "data": slave_info["pack_voltage"]
            })
            
            chart_data["datasets"]["pack_current"].append({
                "label": f"{pcb_code} - Pack Current (A)",
                "slave_id": s_id,
                "data": slave_info["pack_current"]
            })
            
            chart_data["datasets"]["max_cell_voltage"].append({
                "label": f"{pcb_code} - Max Cell Voltage (mV)",
                "slave_id": s_id,
                "data": slave_info["max_cell_voltage"]
            })
            
            chart_data["datasets"]["min_cell_voltage"].append({
                "label": f"{pcb_code} - Min Cell Voltage (mV)",
                "slave_id": s_id,
                "data": slave_info["min_cell_voltage"]
            })
            
            chart_data["datasets"]["cell_difference"].append({
                "label": f"{pcb_code} - Cell Difference (mV)",
                "slave_id": s_id,
                "data": slave_info["cell_difference"]
            })
        
        # Store detailed slave data
        chart_data["slave_data"] = slave_groups
        
        # If no data found, return empty structure
        if not rows:
            chart_data["labels"] = []
            for metric in chart_data["datasets"]:
                chart_data["datasets"][metric] = []
        
        response_data = {
            "chart_data": chart_data,
            "query_params": {
                "slave_id": slave_id,
                "hours": hours
            },
            "data_points": len(rows),
            "slaves_count": len(slave_groups),
            "query_time": hours_ago.strftime("%Y-%m-%d %H:%M:%S"),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "debug_info": {
                "db_path": db_path,
                "db_exists": os.path.exists(db_path),
                "rows_found": len(rows),
                "time_range_query": hours_ago.strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": f"Database error: {str(e)}",
            "data": None
        }), 500
        
    except Exception as e:
        print(f"Error getting battery chart data: {e}")
        return jsonify({
            "status_code": 500,
            "status": "error", 
            "message": f"Internal server error: {str(e)}",
            "data": None
        }), 500

