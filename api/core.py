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

# ================== Load Power Realtime ====================
@api.route('/api/realtime/lvd/', methods=("GET",))
def load_power():
    try:
        # untuk data power overview
        # relay / lvd status = 1 (on) / 0 (off)
        # mcb status = 1 (on) / 0 (off)
        
        # lvd load voltage
        lvd_result = {}
        mcb_result = {}
        load_current = {}
        system_voltage = None

        try:
            lvd1 = float(red.hget('lvd', 'lvd1') or -1)
            lvd2 = float(red.hget('lvd', 'lvd2') or -1)
            lvd3 = float(red.hget('lvd', 'lvd3') or -1)
            lvd_result = {
                "lvd1": lvd1,
                "lvd2": lvd2,
                "lvd3": lvd3,
            }
            mcb_result = {
                "mcb1": lvd1,
                "mcb2": lvd2,
                "mcb3": lvd3
            }
        except Exception as e:
            print(f"Error retrieving LVD data: {e}")

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

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'lvd': lvd_result,
                'mcb': mcb_result,
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
# ================== END Load Power ====================


# ================== SCC Realtime ====================
@api.route('/api/realtime/scc/', methods=("GET",))
def scc_realtime():
    try:
        pv_voltage = {}
        pv_current = {}
        load_status = {}

        # pv voltage, pv current, scc status
        for no in range(1, number_of_scc + 1):
            try:
                pv_voltage[f"pv{no}_voltage"] = float(red.hget(f'scc{no}', 'pv_voltage') or -1)
            except Exception as e:
                print(f"Error retrieving pv{no}_voltage: {e}")
                pv_voltage[f"pv{no}_voltage"] = 0

            try:
                pv_current[f"pv{no}_current"] = float(red.hget(f'scc{no}', 'pv_current') or -1)
            except Exception as e:
                print(f"Error retrieving pv{no}_current: {e}")
                pv_current[f"pv{no}_current"] = 0

            # get load status from scc
            try:
                load_status_value = red.hget(f"scc{no}", "load_status")

                if load_status_value is None:
                    load_status[f"load{no}_status"] = "data not found"
                elif load_status_value == b'1':
                    load_status[f"load{no}_status"] = "is running"
                elif load_status_value == b'0':
                    load_status[f"load{no}_status"] = "is standby"
                elif load_status_value == b'-1':
                    load_status[f"load{no}_status"] = "modbus error"
                else:
                    load_status[f"load{no}_status"] = "unknown status"
            except Exception as e:
                print(f"Error retrieving load_status for scc{no}: {e}")
                load_status[f"load{no}_status"] = "error retrieving data"

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'pv_voltage': pv_voltage,
                'pv_current': pv_current,
                'load_status': load_status
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
# ================== END SCC Realtime ====================


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
    try:
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


@api.route('/api/logger/talis/', methods=("GET",))
@auth.login_required
def logger_talis():
    result_talis_usb0 = []
    result_talis_usb1 = []
    result_mppt = []
    try:
        # logger energy mppt
        data_energy = red.hgetall('energy_data')
        if not data_energy:
            print("Data not found for energy data")

        for key, val in data_energy.items():
            try:
                # Convert dict bytes to dict
                conv_val = literal_eval(str(val)[2:-1])
                ts = str(key)[2:-1]
                conv_val['ts'] = ts
                result_mppt.append(conv_val)
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
                'mppt': result_mppt
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
        mppt_logs = red.hget('energy_data', str(timestamp)) 

        if not bms_data_json_usb0 and not bms_data_json_usb1 and not mppt_logs:
            response = {
                'code': 404,
                'message': 'Data not found',
                'status': 'error'
            }
            return jsonify(response), 404

        # Delete the data
        if mppt_logs:
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

# END
# ============== Talis 5 ===========================


@api.route('/api/device-version/', methods=("GET",))
@auth.login_required
def device_version():
    list_result = []
    try:
        data = red.hgetall('device_version')
        for key, val in data.items():
            result = {}
            conv_val = literal_eval(str(val)[2:-1])
            for k, v in conv_val.items():
                result[k] = v
            list_result.append(result)
    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500
    return jsonify(list_result), 200


@api.route('/api/status/system', methods=('GET',))
@auth.login_required
def system_status():
    try:
        disk = get_disk_detail()
        free_ram = get_free_ram()
        data = {
            'disk': {
                'total': f'{round(disk.total / 1000000000, 1)}',
                'used': f'{round(disk.used / 1000000000, 1)}',
                'free': f'{round(disk.free / 1000000000, 1)}'
            },
            "free_ram": f'{free_ram}'
        }
        return jsonify(data), 200
    except Exception as e:
        print(f"Error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500


@api.route('/api/dashboard/', methods=('GET',))
def dashboard():
    talis_log1 = red.hgetall("bms_usb0_log")
    talis_log2 = red.hgetall("bms_usb1_log")
    mppt_data = red.hgetall("energy_data")

    datas = [talis_log1, talis_log2, mppt_data]

    context = {
        'ip_address': get_ip_address('eth0'),
        'datalogger': len(datas)
    }
    return context


@api.route('/api/mppt-alarm-realtime/', methods=('GET',))
def mppt_alarm_realtime():
    mppt_result = {"message": "success"}
    try:
        for slave in range(1, number_of_mppt + 1):
            # get load status from mppt
            load_status = red.hget(f"mppt{slave}", "load_status")
            if load_status is None:
                status = "data not found"
            elif load_status == b'1':
                status = "is running"
            elif load_status == b'0':
                status = "is standby"
            elif load_status == b'-1':
                status = "modbus error"
            else:
                status = "unknown status"

            # check battery temperature
            try:
                _batt_temp = red.hget(f"mppt{slave}", "battery_temperature")
                if _batt_temp is None:
                    batt_temp = "data not found"
                elif _batt_temp == b'-1':
                    batt_temp = "modbus error"
                else:
                    batt_temp = literal_eval(str(_batt_temp)[2:-1])
            except Exception:
                batt_temp = "modbus error"

            # check device temperature
            try:
                _device_temp = red.hget(f"mppt{slave}", "device_temperature")
                if _device_temp is None:
                    device_temp = "data not found"
                elif _device_temp == b'-1':
                    device_temp = "modbus error"
                else:
                    device_temp = literal_eval(str(_device_temp)[2:-1])
            except Exception:
                device_temp = "modbus error"

            # get alarm info from mppt
            try:
                _alarm = red.hget(f"mppt{slave}_alarm", "alarm")
                if _alarm is None:
                    alarm = "data not found"
                else:
                    # convert bytes to string
                    str_alarm = _alarm.decode("utf-8")
                    # evaluate string to dict
                    alarm = literal_eval(str_alarm)
            except Exception:
                alarm = "modbus error"

            # add mppt data to dict
            mppt_result[f"mppt{slave}"] = {
                "load_status": status,
                "battery_temperature": batt_temp,
                "device_temperature": device_temp,
                "alarm": alarm
            }
        return jsonify(mppt_result), 200

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


@api.route('/api/mppt-alarm-loggers/', methods=('GET',))
def mppt_alarm_loggers():
    mppt_alarm_result = {"message": "success"}
    alarm_lists = []
    try:
        data = red.hgetall('mppt_logs')
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
        mppt_alarm_result["data"] = alarm_lists
        return jsonify(mppt_alarm_result), 200

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


@api.route('/api/mppt-alarm-loggers/', methods=('DELETE',))
def delete_mppt_alarm_loggers():
    try:
        red.delete('mppt_logs')
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
