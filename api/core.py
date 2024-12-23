import time
import json
from ast import literal_eval
from flask import jsonify
from . import api
from .redisconnection import red
from config import number_of_batt, number_of_scc, slave_ids
from auths import token_auth as auth
from functions import get_ip_address, get_disk_detail, get_free_ram
from redis.exceptions import RedisError


# ============== Device Information ===========================
@api.route('/api/device-information/', methods=("GET",))
def device_information():
    try:
        device_information = {}
        data = red.hgetall('device_version')
        for key, val in data.items():
            conv_val = literal_eval(str(val)[2:-1])
            for k, v in conv_val.items():
                device_information[k] = v
        
        # datalog length
        talis_log1 = red.hgetall("bms_usb0_log")
        talis_log2 = red.hgetall("bms_usb1_log")
        scc_data = red.hgetall("energy_data")

        datalog = [talis_log1, talis_log2, scc_data]
        datalog_length = len(datalog)
        
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
                'datalog_length': datalog_length,
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
            feedback_status = literal_eval(red.hget('lvd', 'mcb_status').decode())
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
                load_status_value = red.hget(scc_key, "load_status")

                if load_status_value is None:
                    scc_data[scc_key]['load_status'] = "data not found"
                elif load_status_value == b'1':
                    scc_data[scc_key]['load_status'] = "is running"
                elif load_status_value == b'0':
                    scc_data[scc_key]['load_status'] = "is standby"
                elif load_status_value == b'-1':
                    scc_data[scc_key]['load_status'] = "modbus error"
                else:
                    scc_data[scc_key]['load_status'] = "unknown status"
            except Exception as e:
                print(f"Error retrieving load_status for {scc_key}: {e}")
                scc_data[scc_key]['load_status'] = "error retrieving data"

            # battery temperature
            try:
                _batt_temp = red.hget(scc_key, "battery_temperature")
                if _batt_temp is None:
                    scc_data[scc_key]['battery_temperature'] = -1
                elif _batt_temp == b'-1':
                    scc_data[scc_key]['battery_temperature'] = "modbus error"
                else:
                    scc_data[scc_key]['battery_temperature'] = literal_eval(str(_batt_temp)[2:-1])
            except Exception as e:
                print(f"Error retrieving battery_temperature for {scc_key}: {e}")
                scc_data[scc_key]['battery_temperature'] = "modbus error"

            # device temperature
            try:
                _device_temp = red.hget(scc_key, "device_temperature")
                if _device_temp is None:
                    scc_data[scc_key]['device_temperature'] = -1
                elif _device_temp == b'-1':
                    scc_data[scc_key]['device_temperature'] = "modbus error"
                else:
                    scc_data[scc_key]['device_temperature'] = literal_eval(str(_device_temp)[2:-1])
            except Exception as e:
                print(f"Error retrieving device temperature for {scc_key}: {e}")
                scc_data[scc_key]['device_temperature'] = "modbus error"

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
                    # convert bytes to string
                    str_alarm = _alarm.decode("utf-8")
                    # evaluate string to dict
                    alarm = literal_eval(str_alarm)
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

# ================== END API Realtime ====================


# ============== Talis 5 ===========================
@api.route('/api/bmsactive/', methods=("GET",))
def bms_active():
    try:
        # bms active in usb0
        bms_active = red.hgetall('bms_active_usb0')
        if not bms_active:
            print("BMS active USB0 data not found")

        bms_active_compare = dict()
        for key, val in bms_active.items():
            bms_active_compare[str(key)[2:-1]] = int(val)

        # bms active in usb1
        bms_active1 = red.hgetall('bms_active_usb1')
        if not bms_active1:
            print("BMS active USB1 data not found")

        bms_active_compare1 = dict()
        for key, val in bms_active1.items():
            bms_active_compare1[str(key)[2:-1]] = int(val)

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


@api.route('/api/realtime/talis', methods=("GET",))
@auth.login_required
def realtime_talis():
    talis_data_usb0 = []
    talis_data_usb1 = []
    energy_data = dict()
    scc_data = dict()
    scc_list = []
    try:
        # realtime energy mppt
        energy_data['batt_volt'] = int(
            red.hget('avg_volt', 'voltage').decode('utf-8'))

        for no in range(1, number_of_scc + 1):
            energy_data[f'load{no}'] = float(
                red.hget('sensor_arus', f'load{no}'))
            energy_data[f'pv{no}_volt'] = float(
                red.hget(f'scc{no}', 'pv_voltage'))
            energy_data[f'pv{no}_curr'] = float(
                red.hget(f'scc{no}', 'pv_current'))
        
        
        
        # untuk data scc overview (scc 1 dan 2)
        # pv voltage, pv current, scc status

        # logger data for usb0
        for slave_id in range(1, slave_ids + 1):
            bms_data_json = red.hget("bms_usb0", f"slave_id_{slave_id}")
            if bms_data_json:
                bms_logger = json.loads(bms_data_json)
                # trim pcb_code
                bms_logger['pcb_code'] = bms_logger['pcb_code'].strip()
                talis_data_usb0.append(bms_logger)
            else:
                print(f"No data found for slave_id_{slave_id} in usb0")

        # logger data for usb1
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
                'usb1': talis_data_usb1,
                'scc': scc_list
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


@api.route('/api/logger/talis/', methods=("GET",))
@auth.login_required
def logger_talis():
    result_talis_usb0 = []
    result_talis_usb1 = []
    result_scc = []
    try:
        # logger energy scc
        data_energy = red.hgetall('energy_data')
        if not data_energy:
            print("Data not found for energy data")

        for key, val in data_energy.items():
            try:
                # Convert dict bytes to dict
                conv_val = literal_eval(str(val)[2:-1])
                ts = str(key)[2:-1]
                conv_val['ts'] = ts
                result_scc.append(conv_val)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing data for key {key}: {e}")
                continue

        # logger data for usb0
        data_usb0 = red.hgetall('bms_usb0_log')
        if not data_usb0:
            print("Data not found for usb0")

        for key, val in data_usb0.items():
            try:
                # Convert list bytes to list
                conv_val = literal_eval(str(val)[2:-1])
                ts = str(key)[2:-1]
                for v in conv_val:
                    # Add ts to dict
                    v['ts'] = ts
                    # Trim pcb_code
                    v['pcb_code'] = v['pcb_code'].strip()
                    result_talis_usb0.append(v)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing data for key {key}: {e}")
                continue

        # logger data for usb1
        data_usb1 = red.hgetall('bms_usb1_log')
        if not data_usb1:
            print("Data not found for usb1")

        for key, val in data_usb1.items():
            try:
                # Convert list bytes to list
                conv_val = literal_eval(str(val)[2:-1])
                ts = str(key)[2:-1]
                for v in conv_val:
                    # Add ts to dict
                    v['ts'] = ts
                    # Trim pcb_code
                    v['pcb_code'] = v['pcb_code'].strip()
                    result_talis_usb1.append(v)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing data for key {key}: {e}")
                continue

        if result_talis_usb0 == [] and result_talis_usb1 == []:
            response = {
                'code': 404,
                'message': 'Data not found',
                'data': []
            }
            return jsonify(response), 404

        response = {
            'code': 200,
            'message': 'Success',
            'data': {
                'usb0': result_talis_usb0,
                'usb1': result_talis_usb1,
                'scc': result_scc
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
    
    except ValueError as e:
        print(f"Error: {e}")
        response = {
            'code': 404,
            'message': 'Data not found',
            'data': []
        }
        return jsonify(response), 404

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': []
        }
        return jsonify(response), 500


@api.route('/api/logger/talis/<timestamp>', methods=('DELETE',))
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
            for id in range(1, slave_ids + 1):
                red.hdel('bms_usb0', f"slave_id_{id}")
        
        if bms_data_json_usb1:
            red.hdel('bms_usb1_log', str(timestamp))
            for id in range(1, slave_ids + 1):
                red.hdel('bms_usb1', f"slave_id_{id}")

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

# ===================== End Talis 5 ===========================


# ===================== SCC Alarm ===========================


@api.route('/api/scc-alarm-loggers/', methods=('GET',))
def scc_alarm_loggers():
    scc_alarm_result = {"message": "success"}
    alarm_lists = []
    try:
        data = red.hgetall('scc_logs')
        if not data:
            response = {
                "code": 404,
                "message": "Data not found",
                "status": "error"
            }
            return jsonify(response), 404

        for key, value in data.items():
            dict_result = {}
            conv = literal_eval(str(value)[2:-1])
            # convert epoch time to human readable
            epoch_time = literal_eval(str(key)[2:-1]) / 1000
            dict_result['time'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))
            for k, v in conv.items():
                dict_result[k] = v
            alarm_lists.append(dict_result)

        # sort alarm_lists in descending order based on 'time'
        alarm_lists = sorted(
            alarm_lists, key=lambda x: x['time'], reverse=True)
        scc_alarm_result["data"] = alarm_lists
        return jsonify(scc_alarm_result), 200

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


@api.route('/api/scc-alarm-loggers/', methods=('DELETE',))
def delete_scc_alarm_loggers():
    try:
        red.delete('scc_logs')
        response = {
            "code": 200,
            "message": "Data deleted successfully",
            "status": "success"
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


# ===================== End SCC Alarm ===========================