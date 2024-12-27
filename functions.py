import shutil
import subprocess
import json
from subprocess import Popen
from config import *


def change_ip(path, ip, gw, snmp_ip):
    p = Popen(["sudo", "python3", path, ip, gw, snmp_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, errors = p.communicate()
    return output


def bash_command(command, universal_newlines=False, shell=False):
    if isinstance(command, str):
        sep_command = command.split(' ')
    else:
        sep_command = command
    p = Popen(sep_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=universal_newlines, shell=shell)
    output, errors = p.communicate()
    if isinstance(output, bytes):
        return str(output)[2:-1]
    else:
        return output


def get_ip_address(interface):
    command = [f"ifconfig {interface} | grep 'inet ' | awk '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    ipaddress = output.replace("\n", "")
    return ipaddress


def get_subnet_mask(interface):
    command = [f"ip -o -f inet addr show {interface} | awk '/scope global/ {{print $4}}' | awk -F'/' '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    subnet_mask = output.strip()
    return subnet_mask


def get_gateway(interface):
    command = [f"ip route show dev {interface} | awk '/default/ {{print $3}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    gateway = output.replace("\n", "")
    return gateway


def get_free_ram():
    command = ["free -h | grep Mi"]
    output = bash_command(command, universal_newlines=True, shell=True)
    line = output[:output.find('\nSwap')][62:].replace(" ", "")
    free_ram = line[line.find('Mi')+2:].replace("Mi", "")
    return free_ram


def get_disk_detail():
    disk = shutil.disk_usage('/')
    return disk


def update_site_location(path, form):
    data = {}
    for key, value in form.items():
        data[key] = value

    site_id = data.get('site-id')
    site_name = data.get('site-name')
    address = data.get('address')

    # open json file
    with open(path, 'r') as f:
        json_data = json.load(f)

    json_data['site_location']['site_id'] = site_id
    json_data['site_location']['site_name'] = site_name
    json_data['site_location']['address'] = address

    #  write to json file
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)
    return True


def update_device_model(path, form):
    data = {}
    for key, value in form.items():
        data[key] = value

    model = data.get('device_model')
    part_number = data.get('part_number')
    serial_number = data.get('serial_number')
    software_version = data.get('software_version')
    hardware_version = data.get('hardware_version')

    # open json file
    with open(path, 'r') as f:
        json_data = json.load(f)

    json_data['device_model']['model'] = model
    json_data['device_model']['part_number'] = part_number
    json_data['device_model']['serial_number'] = serial_number
    json_data['device_model']['software_version'] = software_version
    json_data['device_model']['hardware_version'] = hardware_version

    # write to json file
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)
    return True


def update_scc_type(path, form):
    data = {}
    for key, value in form.items():
        # validate value
        if key == 'scc_type':
            if value == 'scc-srne':
                data[key] = value
            elif value == 'scc-epveper':
                data[key] = value
            elif value == 'scc-tristar':
                data[key] = value
            else:
                return False
        elif key == 'scc_source':
            if value == 'tcp':
                data[key] = value
            elif value == 'serial':
                data[key] = value
            elif value == 'usb':
                data[key] = value
            else:
                return False
        elif key == 'port':
            data[key] = value
        elif key == 'host':
            data[key] = value
        elif key == 'scan':
            data[key] = value

    scc_type = data.get('scc_type')
    scc_source = data.get('scc_source')
    port = data.get('port')
    host = data.get('host')
    scan = data.get('scan')

    # open json file
    with open(path, 'r') as f:
        data = json.load(f)
    data['device_version']['scc_type'] = scc_type
    data['device_version']['scc_source'] = scc_source

    if scc_type == 'scc-srne':
        data['scc_srne']['port'] = port
        data['scc_srne']['host'] = host
        data['scc_srne']['scan'] = scan
    elif scc_type == 'scc-epveper':
        data['scc_epveper']['port'] = port
        data['scc_epveper']['host'] = host
        data['scc_epveper']['scan'] = scan
    elif scc_type == 'scc-tristar':
        data['scc_tristar']['port'] = port
        data['scc_tristar']['host'] = host
        data['scc_tristar']['scan'] = scan

    # write json file
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    return True


def update_config_scc(path, form):
    data = {}
    for key, value in form.items():
        if key == 'submit':
            continue
        else:
            data[key] = value

    voltage_reconnect_bts = int(data.get('voltage_reconnect_bts'))
    voltage_cutoff_bts = int(data.get('voltage_cutoff_bts'))
    voltage_reconnect_vsat = int(data.get('voltage_reconnect_vsat'))
    voltage_cutoff_vsat = int(data.get('voltage_cutoff_vsat'))

    # validate
    bts_reconnect = round(voltage_reconnect_bts / 40) + 1
    bts_undervoltage_warning_level = bts_reconnect - 1
    # bts_overdischarge_voltage = bts_reconnect - 2
    bts_cutoff = round(voltage_cutoff_bts / 40)
    bts_discharging_limit_voltage = bts_cutoff - 2

    vsat_reconnect = round(voltage_reconnect_vsat / 40)
    vsat_undervoltage_warning_level = vsat_reconnect - 1
    # vsat_overdischarge_voltage = vsat_reconnect - 2
    vsat_cutoff = round(voltage_cutoff_vsat / 40)
    vsat_discharging_limit_voltage = vsat_cutoff - 2

    if vsat_reconnect > vsat_undervoltage_warning_level > vsat_cutoff > vsat_discharging_limit_voltage:
        if bts_reconnect > bts_undervoltage_warning_level > bts_cutoff > bts_discharging_limit_voltage:
            # scc srne
            if number_of_scc == 3:
                host = data.get('host')
                port = data.get('port')
                battery_capacity = int(data.get('battery_capacity'))
                system_voltage = int(data.get('system_voltage'))
                battery_type = int(data.get('battery_type'))
                overvoltage_threshold = int(data.get('overvoltage_threshold'))
                charging_limit_voltage = int(
                    data.get('charging_limit_voltage'))
                equalizing_charge_voltage = int(
                    data.get('equalizing_charge_voltage'))
                boost_charging_voltage = int(
                    data.get('boost_charging_voltage'))
                floating_charging_voltage = int(
                    data.get('floating_charging_voltage'))
                boost_charging_recovery_voltage = int(
                    data.get('boost_charging_recovery_voltage'))
                overdischarge_time_delay = int(
                    data.get('overdischarge_time_delay'))
                equalizing_charging_time = int(
                    data.get('equalizing_charging_time'))
                boost_charging_time = int(data.get('boost_charging_time'))
                equalizing_charging_interval = int(
                    data.get('equalizing_charging_interval'))
                temperature_comp = int(data.get('temperature_comp'))

                # read json file
                with open(path, 'r') as f:
                    data = json.load(f)
                data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
                data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
                data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
                data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

                data['scc_srne']['host'] = host
                data['scc_srne']['port'] = port
                data['scc_srne']['parameter']['battery_capacity'] = battery_capacity
                data['scc_srne']['parameter']['system_voltage'] = system_voltage
                data['scc_srne']['parameter']['battery_type'] = battery_type
                data['scc_srne']['parameter']['overvoltage_threshold'] = overvoltage_threshold
                data['scc_srne']['parameter']['charging_limit_voltage'] = charging_limit_voltage
                data['scc_srne']['parameter']['equalizing_charge_voltage'] = equalizing_charge_voltage
                data['scc_srne']['parameter']['boost_charging_voltage'] = boost_charging_voltage
                data['scc_srne']['parameter']['floating_charging_voltage'] = floating_charging_voltage
                data['scc_srne']['parameter']['boost_charging_recovery_voltage'] = boost_charging_recovery_voltage
                data['scc_srne']['parameter']['overdischarge_time_delay'] = overdischarge_time_delay
                data['scc_srne']['parameter']['equalizing_charging_time'] = equalizing_charging_time
                data['scc_srne']['parameter']['boost_charging_time'] = boost_charging_time
                data['scc_srne']['parameter']['equalizing_charging_interval'] = equalizing_charging_interval
                data['scc_srne']['parameter']['temperature_comp'] = temperature_comp

                # write json file
                with open(path, 'w') as f:
                    json.dump(data, f, indent=4)
                return True
            # scc epveper
            if number_of_scc == 2:
                host = data.get('host')
                port = data.get('port')
                overvoltage_disconnect = int(
                    data.get('overvoltage_disconnect'))
                overvoltage_reconnect = int(data.get('overvoltage_reconnect'))

                # read json file
                with open(path, 'r') as f:
                    data = json.load(f)
                data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
                data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
                data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
                data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

                data['scc_epveper']['host'] = host
                data['scc_epveper']['port'] = port
                data['scc_epveper']['parameter']['overvoltage_disconnect'] = overvoltage_disconnect
                data['scc_epveper']['parameter']['overvoltage_reconnect'] = overvoltage_reconnect

                # write json file
                with open(path, 'w') as f:
                    json.dump(data, f, indent=4)
                return True
        return False
    return False
