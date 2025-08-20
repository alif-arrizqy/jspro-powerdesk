from smbus2 import SMBus
import psutil
import shutil
import subprocess
import json
import subprocess
from gpiozero import CPUTemperature
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


def send_i2c_message(address, message):
    bus = SMBus(1)
    try:
        bus.write_byte(address, message)
        return True
    except OSError:
        return False

def send_i2c_heartbeat(address=0x28, message=ord('H')):
    """Send I2C heartbeat with logging"""
    import json
    from datetime import datetime
    
    bus = SMBus(1)
    timestamp = datetime.now().isoformat()
    
    try:
        bus.write_byte(address, message)
        result = {
            'success': True,
            'timestamp': timestamp,
            'address': hex(address),
            'message': chr(message),
            'error': None
        }
        # Log successful communication
        log_i2c_communication(result)
        return result
    except OSError as e:
        result = {
            'success': False,
            'timestamp': timestamp,
            'address': hex(address),
            'message': chr(message),
            'error': str(e)
        }
        # Log failed communication
        log_i2c_communication(result)
        return result

def log_i2c_communication(result):
    """Log I2C communication results to file"""
    import json
    from datetime import datetime
    
    log_file = '/var/lib/sundaya/jspro-powerdesk/logs/i2c_communication.log'
    
    try:
        log_entry = {
            'timestamp': result['timestamp'],
            'success': result['success'],
            'address': result['address'],
            'message': result['message'],
            'error': result['error']
        }
        
        # Read existing logs
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []
        
        # Add new log entry
        logs.append(log_entry)
        
        # Keep only last 1000 entries
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        # Write back to file
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging I2C communication: {e}")

def get_i2c_logs(limit=50):
    """Get I2C communication logs"""
    import json
    
    log_file = '/var/lib/sundaya/jspro-powerdesk/logs/i2c_communication.log'
    
    try:
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        # Return latest logs
        return logs[-limit:] if len(logs) > limit else logs
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_i2c_settings():
    """Get I2C monitoring settings"""
    import json
    
    settings_file = 'i2c_settings.json'
    default_settings = {
        'enabled': True,
        'interval_minutes': 2,
        'i2c_address': '0x28',
        'message': 'H',
        'last_modified': None,
        'modified_by': None
    }
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        return settings
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default settings file
        save_i2c_settings(default_settings)
        return default_settings

def save_i2c_settings(settings):
    """Save I2C monitoring settings"""
    import json
    from datetime import datetime
    
    settings_file = 'i2c_settings.json'
    settings['last_modified'] = datetime.now().isoformat()
    
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving I2C settings: {e}")
        return False


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


def get_cpu_usage():
    """Get CPU Usage Percentage"""
    return psutil.cpu_percent(interval=2) 


def get_memory_usage():
    """Get memory usage percentage"""
    memory = psutil.virtual_memory()
    return memory.percent


def get_temperature():
    """Get CPU temperature"""
    try:
        cpu_temp = CPUTemperature()
        temperature = round(cpu_temp.temperature, 1)
    except:
        temperature = 25.0
    return temperature


def get_disk_detail():
    disk = shutil.disk_usage('/')
    return disk


def update_site_information(path, form):
    data = {}
    for key, value in form.items():
        data[key] = value

    site_id = data.get('site-id')
    site_name = data.get('site-name')
    address = data.get('address')

    # open json file
    with open(path, 'r') as f:
        json_data = json.load(f)

    json_data['site_information']['site_id'] = site_id
    json_data['site_information']['site_name'] = site_name
    json_data['site_information']['address'] = address

    #  write to json file
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)
    return True


def update_device_model(path, form):
    data = {}
    for key, value in form.items():
        data[key] = value

    model = data.get('model')
    part_number = data.get('part-number')
    serial_number = data.get('serial-number')
    software_version = data.get('software-version')
    hardware_version = data.get('hardware-version')

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


def update_device_version(path, form):
    data = {}
    for key, value in form.items():
        data[key] = value

    ehub_version = data.get('ehub-version')
    panel2_type = data.get('panel2-type')
    site_type = data.get('site-type')
    scc_type = data.get('scc-type')
    scc_source = data.get('scc-source')
    battery_type = data.get('battery-type')
    usb_type = data.get('usb-type')

    # open json file
    with open(path, 'r') as f:
        json_data = json.load(f)

    json_data['device_version']['ehub_version'] = ehub_version
    json_data['device_version']['panel2_type'] = panel2_type
    json_data['device_version']['site_type'] = site_type
    json_data['device_version']['scc_type'] = scc_type
    json_data['device_version']['scc_source'] = scc_source
    json_data['device_version']['battery_type'] = battery_type
    json_data['device_version']['usb_type'] = usb_type

    # write to json file
    with open(path, 'w') as f:
        json.dump(json_data, f, indent=4)
    return True


def update_scc_type(path, form):
    data = {}
    for key, value in form.items():
        # validate value
        if key == 'scc-type':
            if value == 'scc-srne':
                data[key] = value
            elif value == 'scc-epveper':
                data[key] = value
            elif value == 'scc-tristar':
                data[key] = value
            else:
                return False
        elif key == 'scc-source':
            if value == 'tcp':
                data[key] = value
            elif value == 'serial':
                data[key] = value
            elif value == 'usb':
                data[key] = value
            else:
                return False
        elif key == 'scc-port':
            data[key] = value
        elif key == 'scc-host':
            data[key] = value
        elif key == 'scc-scan':
            data[key] = value

    scc_type = data.get('scc-type')
    scc_source = data.get('scc-source')
    
    port = data.get('scc-port')
    host = data.get('scc-host')
    scan = data.get('scc-scan')

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


def update_config_cutoff_reconnect(path, form):
    data = {}
    for key, value in form.items():
        print(key, value)
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
    bts_cutoff = round(voltage_cutoff_bts / 40)
    bts_discharging_limit_voltage = bts_cutoff - 2

    vsat_reconnect = round(voltage_reconnect_vsat / 40)
    vsat_undervoltage_warning_level = vsat_reconnect - 1
    vsat_cutoff = round(voltage_cutoff_vsat / 40)
    vsat_discharging_limit_voltage = vsat_cutoff - 2
    
    if vsat_reconnect > vsat_undervoltage_warning_level > vsat_cutoff > vsat_discharging_limit_voltage:
        if bts_reconnect > bts_undervoltage_warning_level > bts_cutoff > bts_discharging_limit_voltage:
            # open json file
            with open(path, 'r') as f:
                data = json.load(f)
            
            data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
            data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
            data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
            data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

            # write json file
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        
        return False
    return False

def update_config_scc(path, form):
    form_data = {}
    for key, value in form.items():
        if key == 'submit' or key == 'config-scc-form':
            continue
        else:
            form_data[key] = value

    # Read json file first
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Get scc type from device_version
    scc_type = data.get('device_version', {}).get('scc_type', '')
    scc_type_underscore = scc_type.replace('-', '_')
    
    # Update parameters based on scc type
    if scc_type_underscore in data:
        if 'parameter' not in data[scc_type_underscore]:
            data[scc_type_underscore]['parameter'] = {}
        
        # Update all parameters from form
        for key, value in form_data.items():
            try:
                # Try to convert to int if possible
                if value.isdigit():
                    data[scc_type_underscore]['parameter'][key] = int(value)
                else:
                    data[scc_type_underscore]['parameter'][key] = value
            except:
                data[scc_type_underscore]['parameter'][key] = value
        
        # Write json file
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    
    return False


def update_ip_configuration(path, form):
    """Update IP configuration in config_device.json"""
    form_data = {}
    for key, value in form.items():
        form_data[key] = value

    # Read json file first
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Ensure ip_configuration section exists
    if 'ip_configuration' not in data:
        data['ip_configuration'] = {}
    
    # Update IP configuration from form
    ip_address_primary = form_data.get('ip-address-primary')
    net_mask = form_data.get('net-mask')
    gateway = form_data.get('gateway')
    site = form_data.get('site')
    
    if ip_address_primary:
        data['ip_configuration']['ip_address_primary'] = ip_address_primary
    if net_mask:
        data['ip_configuration']['subnet_mask'] = net_mask
    if gateway:
        data['ip_configuration']['gateway'] = gateway
    if site:
        data['ip_configuration']['site'] = site
    
    # Write json file
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    return True
