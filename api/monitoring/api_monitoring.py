import json
import sqlite3
import os
from datetime import datetime, timedelta
from flask import jsonify
from . import monitoring_bp
from ..redisconnection import connection as red
from auths import token_auth as auth
from config import number_of_scc, slave_ids, PATH
from redis.exceptions import RedisError


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
        try:
            relay_configuration = {
                "vsat_reconnect": int(red.hget('relay_config', 'vsat_reconnect') or 4700),
                "vsat_cutoff": int(red.hget('relay_config', 'vsat_cutoff') or 4600),
                "bts_reconnect": int(red.hget('relay_config', 'bts_reconnect') or 4900),
                "bts_cutoff": int(red.hget('relay_config', 'bts_cutoff') or 4800)
            }
        except:
            relay_configuration = {
                "vsat_reconnect": 4700,
                "vsat_cutoff": 4600,
                "bts_reconnect": 4900,
                "bts_cutoff": 4800
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
        db_path = f"{PATH}/data_storage.db"

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
    """Get battery monitoring data for all BMS units"""
    try:
        bms_data = []

        # Get BMS data for USB0
        # logger data for usb0
        for slave_id in range(1, slave_ids + 1):
            bms_data_json = red.hget("bms_usb0", f"slave_id_{slave_id}")
            if bms_data_json:
                bms_logger = json.loads(bms_data_json)
                # trim pcb_code
                bms_logger['pcb_code'] = bms_logger['pcb_code'].strip()
                bms_data.append(bms_logger)
            else:
                print(f"No data found for slave_id_{slave_id} in usb0")

        # logger data for usb1
        for slave_id in range(1, slave_ids + 1):
            bms_data_json = red.hget("bms_usb1", f"slave_id_{slave_id}")
            if bms_data_json:
                bms_logger = json.loads(bms_data_json)
                # trim pcb_code
                bms_logger['pcb_code'] = bms_logger['pcb_code'].strip()
                bms_data.append(bms_logger)
            else:
                print(f"No data found for slave_id_{slave_id} in usb1")

        response_data = {
            "bms_data": bms_data,
            "last_update": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
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
            "message": "Internal server error",
            "data": None
        }), 500


@monitoring_bp.route('/battery/active', methods=['GET'])
@auth.login_required
def get_battery_monitoring_active():
    """Get active battery monitoring data with status information"""
    try:
        bms_data = []

        # Get BMS active data for USB0
        bms_active_usb0 = red.hgetall('bms_active_usb0')
        for slave_id in range(1, slave_ids + 1):
            slave_key = f"slave_id_{slave_id}"
            status = bool(int(bms_active_usb0.get(slave_key, 0)))
            
            bms_info = {
                "slave_id": slave_id,
                "port": "usb0",
                "status": status
            }
            bms_data.append(bms_info)

        # Get BMS active data for USB1
        bms_active_usb1 = red.hgetall('bms_active_usb1')
        for slave_id in range(1, slave_ids + 1):
            slave_key = f"slave_id_{slave_id}"
            status = bool(int(bms_active_usb1.get(slave_key, 0)))
            
            bms_info = {
                "slave_id": slave_id,
                "port": "usb1", 
                "status": status
            }
            bms_data.append(bms_info)

        response_data = {
            "bms_data": bms_data,
            "last_update": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
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
            "message": "Internal server error",
            "data": None
        }), 500
