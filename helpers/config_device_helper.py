import json
from config import *

# ehub-talis/config_device.json
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
