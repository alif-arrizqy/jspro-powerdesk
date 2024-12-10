import time
import json
from ast import literal_eval
from config import number_of_batt, number_of_mppt, slave_ids
from flask import jsonify
from .redisconnection import red
from . import api
from auths import token_auth as auth
from functions import get_ip_address, get_disk_detail, get_free_ram
from redis.exceptions import RedisError

# ============== PMS ===============================
@api.route('/api/realtime/', methods=("GET",))
@auth.login_required
def realtime():
    mppt_result = dict()
    pms_result = dict()
    try:
        dock_active = red.hgetall('dock_active')
        if not dock_active:
            raise ValueError("Dock active data not found")

        dock_active_compare = dict()
        for key, val in dock_active.items():
            if key != b'pms0':
                dock_active_compare[str(key)[2:-1]] = int(val)

        mppt_data = [red.hgetall(f'mppt{device}')
                    for device in range(1, number_of_mppt + 1)]
        pms_data = [red.hgetall(f'pms{dock}')
                    for dock in range(1, number_of_batt + 1)]

        for counter, data in enumerate(mppt_data):
            mppt_dict = dict()
            for key, val in data.items():
                mppt_dict[str(key)[2:-1]] = float(val)
            mppt_result[f'mppt{counter + 1}'] = mppt_dict

        for counter, data in enumerate(pms_data):
            pms_dict = dict()
            if data:
                for key, val in data.items():
                    try:
                        pms_dict[str(key)[2:-1]] = int(val)
                    except ValueError:
                        pms_dict[str(key)[2:-1]] = str(val)[2:-1]
                if dock_active_compare.get(f'pms{counter + 1}'):
                    pms_result[f'pms{counter + 1}'] = pms_dict

        vsat = red.hget('relay_status', 'vsat')
        bts = red.hget('relay_status', 'bts')
        obl = red.hget('relay_status', 'obl')

        vsat_state = vsat == b'1'
        bts_state = bts == b'1'
        obl_state = obl == b'1'

        load = {
            'vsat_curr': round(float(red.hget('sensor_arus', 'load1')), 2),
            'bts_curr': round(float(red.hget('sensor_arus', 'load2')), 2),
            'obl': round(float(red.hget('sensor_arus', 'load3')), 2),
            'relay_state': {
                'vsat': vsat_state,
                'bts': bts_state,
                'obl': obl_state
            }
        }

        battery_voltage = int(float(red.hget("avg_volt", "voltage")))
        battery_voltage = round((battery_voltage / 100), 2)

        response = {
            'code': 200,
            'message': 'success',
            'data': {
                'battery_voltage': battery_voltage,
                'mppt_data': mppt_result,
                'pms_data': pms_result,
                'load': load
            }
        }
        return jsonify(response), 200

    except (RedisError, ValueError) as e:
        print(f"Error: {e}")
        response = {
            'code': 404,
            'message': 'data not found',
            'data': {
                'battery_voltage': 0,
                'mppt_data': mppt_result,
                'pms_data': pms_result,
                'load': {
                    'vsat_curr': -1,
                    'bts_curr': -1,
                    'obl': -1,
                    'relay_state': {
                        'vsat': True,
                        'bts': False,
                        'obl': True
                    }
                }
            }
        }
        return jsonify(response), 404

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': {}
        }
        return jsonify(response), 500


@api.route('/api/dockactive/', methods=("GET",))
def dockactive():
    try:
        dock_active = red.hgetall('dock_active')
        if not dock_active:
            raise ValueError("Dock active data not found")

        dock_active_compare = dict()
        for key, val in dock_active.items():
            if key != b'pms0':
                dock_active_compare[str(key)[2:-1]] = int(val)

        response = {
            'code': 200,
            'message': 'success',
            'data': dock_active_compare
        }
        return jsonify(response), 200

    except (RedisError, ValueError) as e:
        print(f"Error: {e}")
        response = {
            'code': 404,
            'message': 'data not found',
            'data': {}
        }
        return jsonify(response), 404

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'data': {}
        }
        return jsonify(response), 500


@api.route('/api/logger/', methods=("GET",))
@auth.login_required
def logger():
    list_result = list()
    try:
        data = red.hgetall('data')
        if not data:
            raise ValueError("Logger data not found")

        for key, val in data.items():
            result = dict()
            conv_val = literal_eval(str(val)[2:-1])
            result['ts'] = str(key)[2:-1]
            for k, v in conv_val.items():
                result[k] = v

            # tvd only
            try:
                bsp = result.get("bspwatt")
                mcb_voltage = result.get("mcb_voltage")
                rxlevel = result.get("rxlevel")
                plpfill = result.get("plpfill")
                sync = result.get("sync")
                software_uptime = result.get("software_uptime")

                if software_uptime in [b'', None]:
                    result["software_uptime"] = 0
                if bsp in [b'', None]:
                    result["bspwatt"] = 0
                if mcb_voltage in [b'', None]:
                    result["mcb_voltage"] = 0
                if rxlevel in [b'', None]:
                    result["rxlevel"] = 0
                if plpfill in [b'', None]:
                    result["plpfill"] = 0
                if sync in [b'', None]:
                    result["sync"] = 0
            except Exception as e:
                print(f"Error processing logger data: {e}")
                pass
            
            list_result.append(result)
        
        response = {
            'code': 200,
            'message': 'success',
            'data': list_result
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


@api.route('/api/logger/<timestamp>', methods=('DELETE',))
@auth.login_required
def delete_logger(timestamp):
    try:
        result = red.hdel('data', str(timestamp))
        if result == 0:
            raise ValueError("Data not found")

        response = {
            'code': 200,
            'message': 'Data deleted successfully',
            'status': 'success'
        }
        return jsonify(response), 200

    except (RedisError, ValueError) as e:
        print(f"Error: {e}")
        response = {
            'code': 404,
            'message': 'data not found',
            'status': 'error'
        }
        return jsonify(response), 404

    except Exception as e:
        print(f"Unexpected error: {e}")
        response = {
            'code': 500,
            'message': 'Internal server error',
            'status': 'error'
        }
        return jsonify(response), 500

# END
# ============== PMS ===============================

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
