import json
import re
from ast import literal_eval
from flask import jsonify, request
from . import api
from .redisconnection import connection as red
from config import number_of_scc, slave_ids
from auths import token_auth as auth
from functions import get_disk_detail, get_free_ram
from redis.exceptions import RedisError


# ============== Device Information ===========================
@api.route('/api/device-information/', methods=("GET",))
def device_information():
    try:
        device_information = {}
        data = red.hgetall('device_version')
        for key, val in data.items():
            # conv_val = literal_eval(str(val)[2:-1])
            conv_val = json.loads(val)
            for k, v in conv_val.items():
                device_information[k] = v
        
        # disk usage and ram usage
        disk = get_disk_detail()
        free_ram = get_free_ram()
        disk_ram = {
            'disk': {
                'total': f'{round(disk.total / 1000000000, 1)}',
                'used': f'{round(disk.used / 1000000000, 1)}',
                'free': f'{round(disk.free / 1000000000, 1)}'
            },
            "free_ram": f'{free_ram}'
        }
        
        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'device_information': device_information,
                'disk_ram': disk_ram
            }
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500
# ================== END Device Information ====================


# ================== API Realtime ====================
@api.route('/api/realtime/lvd/', methods=("GET",))
def lvd_realtime():
    try:
        # lvd load voltage
        lvd_result = {}
        mcb_result = {}
        load_current = {}
        relay_status = {}
        system_voltage = -1
        counter_heartbeat = -1

        try:
            lvd1 = float(red.hget('lvd', 'lvd1') or -1)
            lvd2 = float(red.hget('lvd', 'lvd2') or -1)
            lvd3 = float(red.hget('lvd', 'lvd3') or -1)
            lvd_result = {
                "lvd1": lvd1,
                "lvd2": lvd2,
                "lvd3": lvd3,
            }
        except Exception as e:
            print(f"Error retrieving LVD data: {e}")
            
        try:
            feedback_status = literal_eval(red.hget('lvd', 'mcb_status'))
            if feedback_status is None:
                mcb_result = "data not found"
            
            mcb_result = {
                "mcb1": "CLOSED" if "ON" in feedback_status[0] else "OPEN",
                "mcb2": "CLOSED" if "ON" in feedback_status[1] else "OPEN",
                "mcb3": "CLOSED" if "ON" in feedback_status[2] else "OPEN",
            }

            relay_status = {
                "relay1": "CLOSED" if "ON" in feedback_status[3] else "OPEN",
                "relay2": "CLOSED" if "ON" in feedback_status[4] else "OPEN",
                "relay3": "CLOSED" if "ON" in feedback_status[5] else "OPEN",
            }
            # mcb status
            mcb_result = {
                "mcb1": "CLOSED" if "ON" in feedback_status[0] else "OPEN",
                "mcb2": "CLOSED" if "ON" in feedback_status[1] else "OPEN",
                "mcb3": "CLOSED" if "ON" in feedback_status[2] else "OPEN",
            }
            
            # relay status
            relay_status = {
                "relay1": "CLOSED" if "ON" in feedback_status[3] else "OPEN",
                "relay2": "CLOSED" if "ON" in feedback_status[4] else "OPEN",
                "relay3": "CLOSED" if "ON" in feedback_status[5] else "OPEN",
            }
            
            
        except Exception as e:
            print(f"Error retrieving MCB data: {e}")

        try:
            load1_current = float(red.hget('sensor_arus', 'load1') or -1)
            load2_current = float(red.hget('sensor_arus', 'load2') or -1)
            load3_current = float(red.hget('sensor_arus', 'load3') or -1)
            load_current = {
                "load1_current": load1_current,
                "load2_current": load2_current,
                "load3_current": load3_current
            }
        except Exception as e:
            print(f"Error retrieving load current data: {e}")

        try:
            system_voltage = float(red.hget('lvd', 'system_voltage') or -1)
        except Exception as e:
            print(f"Error retrieving system voltage data: {e}")
            
        try:
            counter_heartbeat = int(red.hget('lvd', 'counter') or -1)
        except Exception as e:
            print(f"Error retrieving heartbeat counter: {e}")

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'counter_heartbeat': counter_heartbeat,
                'lvd': lvd_result,
                'relay_status': relay_status,
                'mcb_status': mcb_result,
                'load_current': load_current,
                'system_voltage': system_voltage
            }
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500


@api.route('/api/realtime/scc/', methods=("GET",))
def scc_realtime():
    try:
        scc_data = {}

        # pv voltage, pv current, scc status
        for no in range(1, number_of_scc + 1):
            scc_key = f"scc{no}"
            scc_data[scc_key] = {}

            try:
                scc_data[scc_key]['counter_heartbeat'] = int(red.hget(scc_key, 'counter') or -1)
            except Exception as e:
                print(f"Error retrieving {scc_key}_counter: {e}")
                scc_data[scc_key]['counter_heartbeat'] = -1

            try:
                scc_data[scc_key]['pv_voltage'] = float(red.hget(scc_key, 'pv_voltage') or -1)
            except Exception as e:
                print(f"Error retrieving {scc_key}_voltage: {e}")
                scc_data[scc_key]['pv_voltage'] = -1

            try:
                scc_data[scc_key]['pv_current'] = float(red.hget(scc_key, 'pv_current') or -1)
            except Exception as e:
                print(f"Error retrieving {scc_key}_current: {e}")
                scc_data[scc_key]['pv_current'] = -1

            # get load status from scc
            try:
                load_status_value = int(red.hget(scc_key, "load_status"))
                
                if load_status_value is None:
                    scc_data[scc_key]['load_status'] = "data not found"
                elif load_status_value == 1:
                    scc_data[scc_key]['load_status'] = "is running"
                elif load_status_value == 0:
                    scc_data[scc_key]['load_status'] = "is standby"
                elif load_status_value == -1:
                    scc_data[scc_key]['load_status'] = "modbus error"
                else:
                    scc_data[scc_key]['load_status'] = "unknown status"
            except Exception as e:
                print(f"Error retrieving load_status for {scc_key}: {e}")
                scc_data[scc_key]['load_status'] = "error retrieving data"

        response = {
            'code': 200,
            'message': 'success',
            'data': scc_data
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500


@api.route('/api/realtime/scc-alarm/', methods=('GET',))
def scc_alarm_realtime():
    scc_data = {}
    
    try:
        for slave in range(1, number_of_scc + 1):
            # get alarm info from scc
            try:
                _alarm = red.hget(f"scc{slave}_alarm", "alarm")
                if _alarm is None:
                    alarm = -1
                else:
                    alarm = literal_eval(_alarm)
            except Exception:
                alarm = "modbus error"
            
            scc_data[f"scc{slave}"] = alarm
            # response
            response = {
                'code': 200,
                'message': 'success',
                'data': scc_data
            }
        return jsonify(response), 200

    except RedisError as e:
        print(f"Redis error: {e}")
        response = {
            "code": 500,
            "message": "Internal server error",
            "status": "error"
        }
        return jsonify(response), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            "code": 500,
            "message": "Internal server error",
            "status": "error"
        }
        return jsonify(response), 500


@api.route('/api/realtime/talis-active/', methods=("GET",))
def talis_active():
    try:
        # bms active in usb0
        bms_active = red.hgetall('bms_active_usb0')
        if not bms_active:
            print("BMS active USB0 data not found")

        bms_active_compare = dict()
        for key, val in bms_active.items():
            bms_active_compare[key] = int(val)

        # bms active in usb1
        bms_active1 = red.hgetall('bms_active_usb1')
        if not bms_active1:
            print("BMS active USB1 data not found")

        bms_active_compare1 = dict()
        for key, val in bms_active1.items():
            bms_active_compare1[key] = int(val)

        if bms_active_compare == {} and bms_active_compare1 == {}:
            response = {
                'code': 404,
                'message': 'Data not found',
                'data': []
            }
            return jsonify(response), 404

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'usb0': bms_active_compare,
                'usb1': bms_active_compare1
            }
        }
        return jsonify(response), 200

    except RedisError as e:
        print(f"Redis error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': []
        }
        return jsonify(response), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': []
        }
        return jsonify(response), 500


@api.route('/api/realtime/talis/', methods=("GET",))
def realtime_talis():
    talis_data_usb0 = []
    talis_data_usb1 = []

    try:
        # data for usb0
        for slave_id in range(1, slave_ids + 1):
            bms_data_json = red.hget("bms_usb0", f"slave_id_{slave_id}")
            if bms_data_json:
                bms_logger = json.loads(bms_data_json)
                # trim pcb_code
                bms_logger['pcb_code'] = bms_logger['pcb_code'].strip()
                talis_data_usb0.append(bms_logger)
            else:
                print(f"No data found for slave_id_{slave_id} in usb0")

        # data for usb1
        for slave_id in range(1, slave_ids + 1):
            bms_data_json = red.hget("bms_usb1", f"slave_id_{slave_id}")
            if bms_data_json:
                bms_logger = json.loads(bms_data_json)
                # trim pcb_code
                bms_logger['pcb_code'] = bms_logger['pcb_code'].strip()
                talis_data_usb1.append(bms_logger)
            else:
                print(f"No data found for slave_id_{slave_id} in usb1")

        if talis_data_usb0 == [] and talis_data_usb1 == []:
            response = {
                'code': 404,
                'message': 'Data not found',
                'data': []
            }
            return jsonify(response), 404

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'usb0': talis_data_usb0,
                'usb1': talis_data_usb1
            }
        }
        return jsonify(response), 200

    except RedisError as e:
        print(f"Redis error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500

    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': []
        }
        return jsonify(response), 500
# ================== END API Realtime ====================


# =========================== Loggers ===========================
def clean_json_string(json_string):
    # Replace single quotes with double quotes
    json_string = json_string.replace("'", '"')
    # Ensure property names are enclosed in double quotes
    json_string = re.sub(r'(\w+):', r'"\1":', json_string)
    return json_string


@api.route('/api/loggers/data', methods=("GET",))
@auth.login_required
def data_loggers():
    result = {}
    try:
        # Get the cursor and page size from query parameters
        cursor = request.args.get('cursor', default=None, type=str)
        page_size = request.args.get('page_size', default=10, type=int)

        # Fetch all data from Redis in one go
        data_energy = red.hgetall('energy_data')
        data_usb0 = red.hgetall('bms_usb0_log')
        data_usb1 = red.hgetall('bms_usb1_log')
        
        # Process energy data
        if data_energy:
            for key, val in data_energy.items():
                try:
                    clean_val = clean_json_string(val)
                    conv_val = json.loads(clean_val)
                    ts = key
                    conv_val['ts'] = ts
                    result.setdefault(ts, {'scc': conv_val, 'battery': []})
                except (ValueError, SyntaxError) as e:
                    print(f"Error parsing data for key {key}: {e}")

        # Process USB0 data
        if data_usb0:
            for key, val in data_usb0.items():
                try:
                    clean_val = clean_json_string(val)
                    conv_val = json.loads(clean_val)
                    ts = key
                    for v in conv_val:
                        v['ts'] = ts
                        v['pcb_code'] = v['pcb_code'].strip()
                        result.setdefault(ts, {'scc': {}, 'battery': []})['battery'].append(v)
                except (ValueError, SyntaxError) as e:
                    print(f"Error parsing data for key {key}: {e}")

        # Process USB1 data
        if data_usb1:
            for key, val in data_usb1.items():
                try:
                    clean_val = clean_json_string(val)
                    conv_val = json.loads(clean_val)
                    ts = key
                    for v in conv_val:
                        v['ts'] = ts
                        v['pcb_code'] = v['pcb_code'].strip()
                        result.setdefault(ts, {'scc': {}, 'battery': []})['battery'].append(v)
                except (ValueError, SyntaxError) as e:
                    print(f"Error parsing data for key {key}: {e}")

        if not result:
            return jsonify({'code': 404, 'message': 'Data not found', 'data': {}}), 404

        # Convert result to a sorted list of items based on timestamp
        sorted_items = sorted(result.items(), key=lambda x: x[0])

        # Find the starting point based on the cursor
        if cursor:
            index = next((i for i, (ts, _) in enumerate(sorted_items) if ts == cursor), None)
            if index is not None:
                sorted_items = sorted_items[index + 1:]  # Get items after the cursor

        # Get the next set of results based on the page size
        paginated_result = dict(sorted_items[:page_size])

        # Calculate the next cursor
        next_cursor = sorted_items[page_size - 1][0] if len(sorted_items) > page_size else None

        # Prepare the response
        response = {
            'code': 200,
            'message': 'Success',
            'next_cursor': next_cursor,
            'page_size': page_size,
            'data': paginated_result
        }
        return jsonify(response), 200

    except RedisError as e:
        print(f"Redis error: {e}")
        return jsonify({'code': 500, 'message': 'Internal server error', 'status': 'error'}), 500

    except ValueError as e:
        print(f"Error: {e}")
        return jsonify({'code': 404, 'message': 'Data not found', 'data': []}), 404

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'code': 500, 'message': 'Internal server error', 'data': []}), 500


@api.route('/api/loggers/scc-alarm', methods=("GET", "DELETE"))
@auth.login_required
def scc_alarm_loggers():
    if request.method == 'GET':
        result = {}
        try:        
            # Get the cursor and page size from query parameters
            cursor = request.args.get('cursor', default=None, type=str)
            page_size = request.args.get('page_size', default=10, type=int)
            
            # Fetch all data from Redis in one go
            scc_logs = red.hgetall('scc_logs_epveper')
            
            # Process scc logs
            if scc_logs:
                for key, val in scc_logs.items():
                    try:
                        clean_val = clean_json_string(val)
                        conv_val = json.loads(clean_val)
                        ts = key
                        result.setdefault(ts, conv_val)
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing data for key {key}: {e}")
            
            if not result:
                return jsonify({'code': 404, 'message': 'Data not found', 'data': {}}), 404
            
            # Convert result to a sorted list of items based on timestamp
            sorted_items = sorted(result.items(), key=lambda x: x[0])
            
            # Find the starting point based on the cursor
            if cursor:
                index = next((i for i, (ts, _) in enumerate(sorted_items) if ts == cursor), None)
                if index is not None:
                    sorted_items = sorted_items[index + 1:]
            
            # Get the next set of results based on the page size
            paginated_result = dict(sorted_items[:page_size])
            
            # Calculate the next cursor
            next_cursor = sorted_items[page_size - 1][0] if len(sorted_items) > page_size else None
            
            # Prepare the response
            response = {
                'code': 200,
                'message': 'Success',
                'next_cursor': next_cursor,
                'page_size': page_size,
                'data': paginated_result
            }
            return jsonify(response), 200

        except RedisError as e:
            print(f"Redis error: {e}")
            return jsonify({'code': 500, 'message': 'Internal server error', 'status': 'error'}), 500

        except ValueError as e:
            print(f"Error: {e}")
            return jsonify({'code': 404, 'message': 'Data not found', 'data': []}), 404

        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({'code': 500, 'message': 'Internal server error', 'data': []}), 500
    if request.method == 'DELETE':
        try:
            scc_logs = red.hgetall('scc_logs_epveper')
            if scc_logs:
                red.delete('scc_logs_epveper')
                response = {
                    "code": 200,
                    "message": "Data deleted successfully",
                    "status": "success"
                }
                return jsonify(response), 200
            else:
                response = {
                    "code": 404,
                    "message": "Data not found",
                    "status": "error"
                }
                return jsonify(response), 404
        
        except RedisError as e:
            print(f"Redis error: {e}")
            response = {
                "code": 500,
                "message": "Internal server error",
                "status": "error"
            }
            return jsonify(response), 500

        except Exception as e:
            print(f"Unexpected error: {e}")
            response = {
                "code": 500,
                "message": "Internal server error",
                "status": "error"
            }
            return jsonify(response), 500

# =========================== End Loggers ===========================


# ===================== Delete Loggers ===========================
@api.route('/api/loggers/data/<timestamp>', methods=('DELETE',))
@auth.login_required
def delete_logger_talis(timestamp):
    try:
        # Check data in redis bms_usb0_log and bms_usb1_log
        bms_data_json_usb0 = red.hget('bms_usb0_log', str(timestamp))
        bms_data_json_usb1 = red.hget('bms_usb1_log', str(timestamp))
        scc_logs = red.hget('energy_data', str(timestamp)) 

        if not bms_data_json_usb0 and not bms_data_json_usb1 and not scc_logs:
            response = {
                'code': 404,
                'message': 'Data not found',
                'status': 'error'
            }
            return jsonify(response), 404

        # Delete the data
        if scc_logs:
            red.hdel('energy_data', str(timestamp))

        if bms_data_json_usb0:
            red.hdel('bms_usb0_log', str(timestamp))
        
        if bms_data_json_usb1:
            red.hdel('bms_usb1_log', str(timestamp))

        response = {
            'code': 200,
            'message': 'Data deleted successfully',
            'status': 'success'
        }
        return jsonify(response), 200
    except RedisError as e:
        print(f"Redis error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500

# ===================== End Delete Loggers ===========================
