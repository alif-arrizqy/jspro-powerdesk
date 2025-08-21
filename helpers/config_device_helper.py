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

    # Read the config file to get SCC type and parameters
    with open(path, 'r') as f:
        config_data = json.load(f)
    
    scc_type = config_data.get('device_version', {}).get('scc_type', '')
    scc_type_underscore = scc_type.replace('-', '_')
    
    # Get SCC parameters for validation
    scc_parameters = config_data.get(scc_type_underscore, {}).get('parameter', {})
    
    # Validate voltage values against SCC parameters based on rules
    validation_passed = True
    validation_errors = []
    
    if scc_type == 'scc-epveper':
        
        required_params = ['float_charging_voltage', 'boost_reconnect_charging_voltage']
        
        # Check if all required parameters exist
        missing_params = [param for param in required_params if param not in scc_parameters]
        if missing_params:
            validation_passed = False
            validation_errors.append(f"Missing critical SCC parameters: {', '.join(missing_params)}")
        else:
            # Validate hierarchy for EPVEPER (using available parameters)
            available_params = [
                'overvoltage_disconnect', 'charging_limit_voltage', 'overvoltage_reconnect',
                'equalize_charging_voltage', 'boost_charging_voltage', 'float_charging_voltage',
                'boost_reconnect_charging_voltage'
            ]
            
            # Check hierarchy only for parameters that exist
            existing_params = [param for param in available_params if param in scc_parameters]
            if len(existing_params) > 1:
                param_values = [scc_parameters.get(param, 0) for param in existing_params]
                for i in range(len(param_values) - 1):
                    if param_values[i] <= param_values[i + 1]:
                        validation_passed = False
                        validation_errors.append(f"Parameter hierarchy violation: {existing_params[i]} ({param_values[i]}) must be greater than {existing_params[i + 1]} ({param_values[i + 1]})")
                        break
            
            # Validate cutoff/reconnect values against SCC parameters
            float_charging = scc_parameters.get('float_charging_voltage', 0)
            boost_reconnect = scc_parameters.get('boost_reconnect_charging_voltage', 0)
            
            # Use boost_reconnect as the lower safe threshold
            min_cutoff_threshold = boost_reconnect * 0.85  # 85% of boost_reconnect as minimum safe cutoff
            
            if voltage_cutoff_bts < min_cutoff_threshold:
                validation_passed = False
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}V) is too low. Minimum recommended: {int(min_cutoff_threshold)}V")
            
            if voltage_cutoff_vsat < min_cutoff_threshold:
                validation_passed = False
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}V) is too low. Minimum recommended: {int(min_cutoff_threshold)}V")
            
            if voltage_reconnect_bts > float_charging:
                validation_passed = False
                validation_errors.append(f"BTS reconnect voltage ({voltage_reconnect_bts}V) should not be higher than SCC float charging ({float_charging}V)")
            
            if voltage_reconnect_vsat > float_charging:
                validation_passed = False
                validation_errors.append(f"VSAT reconnect voltage ({voltage_reconnect_vsat}V) should not be higher than SCC float charging ({float_charging}V)")
    
    elif scc_type == 'scc-srne':
        
        required_params = ['floating_charging_voltage', 'boost_charging_recovery_voltage']
        
        # Check if all required parameters exist
        missing_params = [param for param in required_params if param not in scc_parameters]
        if missing_params:
            validation_passed = False
            validation_errors.append(f"Missing critical SCC parameters: {', '.join(missing_params)}")
        else:
            # Validate hierarchy for SRNE (using available parameters)
            available_params = [
                'overvoltage_threshold', 'charging_limit_voltage', 'equalizing_charge_voltage',
                'boost_charging_voltage', 'floating_charging_voltage', 'boost_charging_recovery_voltage'
            ]
            
            # Check hierarchy only for parameters that exist
            existing_params = [param for param in available_params if param in scc_parameters]
            if len(existing_params) > 1:
                param_values = [scc_parameters.get(param, 0) for param in existing_params]
                for i in range(len(param_values) - 1):
                    if param_values[i] <= param_values[i + 1]:
                        validation_passed = False
                        validation_errors.append(f"Parameter hierarchy violation: {existing_params[i]} ({param_values[i]}) must be greater than {existing_params[i + 1]} ({param_values[i + 1]})")
                        break
            
            # Validate cutoff/reconnect values against SCC parameters
            floating_charging = scc_parameters.get('floating_charging_voltage', 0)
            boost_recovery = scc_parameters.get('boost_charging_recovery_voltage', 0)
            
            # Convert to voltage (SRNE uses 0.1V units, so multiply by 10 to get mV)
            floating_charging_mv = floating_charging * 10
            boost_recovery_mv = boost_recovery * 10
            
            # Use boost_recovery as the lower safe threshold
            min_cutoff_threshold = boost_recovery_mv * 0.85  # 85% of boost_recovery as minimum safe cutoff
            
            if voltage_cutoff_bts < min_cutoff_threshold:
                validation_passed = False
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}mV) is too low. Minimum recommended: {int(min_cutoff_threshold)}mV")
            
            if voltage_cutoff_vsat < min_cutoff_threshold:
                validation_passed = False
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}mV) is too low. Minimum recommended: {int(min_cutoff_threshold)}mV")
            
            if voltage_reconnect_bts > floating_charging_mv:
                validation_passed = False
                validation_errors.append(f"BTS reconnect voltage ({voltage_reconnect_bts}mV) should not be higher than SCC floating charging ({floating_charging_mv}mV)")
            
            if voltage_reconnect_vsat > floating_charging_mv:
                validation_passed = False
                validation_errors.append(f"VSAT reconnect voltage ({voltage_reconnect_vsat}mV) should not be higher than SCC floating charging ({floating_charging_mv}mV)")
    
    # If no SCC type or unsupported SCC type, fall back to basic validation
    if not scc_type or scc_type not in ['scc-epveper', 'scc-srne']:
        # Basic validation (original logic)
        bts_reconnect = round(voltage_reconnect_bts / 40) + 1
        bts_undervoltage_warning_level = bts_reconnect - 1
        bts_cutoff = round(voltage_cutoff_bts / 40)
        bts_discharging_limit_voltage = bts_cutoff - 2

        vsat_reconnect = round(voltage_reconnect_vsat / 40)
        vsat_undervoltage_warning_level = vsat_reconnect - 1
        vsat_cutoff = round(voltage_cutoff_vsat / 40)
        vsat_discharging_limit_voltage = vsat_cutoff - 2
        
        if not (vsat_reconnect > vsat_undervoltage_warning_level > vsat_cutoff > vsat_discharging_limit_voltage):
            validation_passed = False
            validation_errors.append("VSAT voltage hierarchy validation failed")
        
        if not (bts_reconnect > bts_undervoltage_warning_level > bts_cutoff > bts_discharging_limit_voltage):
            validation_passed = False
            validation_errors.append("BTS voltage hierarchy validation failed")
    
    # Additional basic validations
    if voltage_reconnect_bts <= voltage_cutoff_bts:
        validation_passed = False
        validation_errors.append("BTS reconnect voltage must be higher than cutoff voltage")
    
    if voltage_reconnect_vsat <= voltage_cutoff_vsat:
        validation_passed = False
        validation_errors.append("VSAT reconnect voltage must be higher than cutoff voltage")
        
    # Additional safety checks for reasonable voltage gaps
    voltage_gap_bts = voltage_reconnect_bts - voltage_cutoff_bts
    voltage_gap_vsat = voltage_reconnect_vsat - voltage_cutoff_vsat
    
    if voltage_gap_bts < 50:  # Minimum 50mV gap
        validation_passed = False
        validation_errors.append(f"BTS voltage gap ({voltage_gap_bts}mV) is too small. Minimum recommended: 50mV")
    
    if voltage_gap_vsat < 50:  # Minimum 50mV gap
        validation_passed = False
        validation_errors.append(f"VSAT voltage gap ({voltage_gap_vsat}mV) is too small. Minimum recommended: 50mV")
    
    # If validation passes, update the configuration
    if validation_passed:
        config_data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
        config_data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
        config_data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
        config_data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

        # Write json file
        with open(path, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    else:
        # Print validation errors for debugging
        for error in validation_errors:
            print(f"Validation Error: {error}")
        return False


def get_validation_errors_for_cutoff_reconnect(path, form):
    """
    Helper function to get detailed validation errors for cutoff/reconnect configuration
    Returns a list of validation error messages
    """
    data = {}
    for key, value in form.items():
        if key == 'submit':
            continue
        else:
            data[key] = value

    try:
        voltage_reconnect_bts = int(data.get('voltage_reconnect_bts'))
        voltage_cutoff_bts = int(data.get('voltage_cutoff_bts'))
        voltage_reconnect_vsat = int(data.get('voltage_reconnect_vsat'))
        voltage_cutoff_vsat = int(data.get('voltage_cutoff_vsat'))
    except (ValueError, TypeError):
        return ["Invalid voltage values provided"]

    # Read the config file to get SCC type and parameters
    try:
        with open(path, 'r') as f:
            config_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return ["Could not read configuration file"]
    
    scc_type = config_data.get('device_version', {}).get('scc_type', '')
    scc_type_underscore = scc_type.replace('-', '_')
    
    # Get SCC parameters for validation
    scc_parameters = config_data.get(scc_type_underscore, {}).get('parameter', {})
    
    validation_errors = []
    
    # SCC-specific validation based on actual available parameters
    if scc_type == 'scc-epveper':        
        # Check if minimum required parameters exist
        required_params = ['float_charging_voltage', 'boost_reconnect_charging_voltage']
        missing_params = [param for param in required_params if param not in scc_parameters]
        if missing_params:
            validation_errors.append(f"Missing critical SCC parameters: {', '.join(missing_params)}")
        else:
            # Use available parameters for validation
            float_charging = scc_parameters.get('float_charging_voltage', 0)
            boost_reconnect = scc_parameters.get('boost_reconnect_charging_voltage', 0)
            
            # Validate that cutoff voltages should not be higher than boost_reconnect_charging_voltage
            # since this is typically the minimum safe voltage for reconnection
            if voltage_cutoff_bts > boost_reconnect:
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}V) should not be higher than SCC boost reconnect charging ({boost_reconnect}V)")
            
            if voltage_cutoff_vsat > boost_reconnect:
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}V) should not be higher than SCC boost reconnect charging ({boost_reconnect}V)")
            
            # Validate that reconnect voltages should be reasonable compared to float charging
            if voltage_reconnect_bts > float_charging:
                validation_errors.append(f"BTS reconnect voltage ({voltage_reconnect_bts}V) should not be higher than SCC float charging ({float_charging}V)")
            
            if voltage_reconnect_vsat > float_charging:
                validation_errors.append(f"VSAT reconnect voltage ({voltage_reconnect_vsat}V) should not be higher than SCC float charging ({float_charging}V)")
                
            # Ensure reasonable gap between cutoff and reconnect relative to SCC parameters
            min_cutoff_threshold = boost_reconnect * 0.85  # 85% of boost_reconnect as minimum safe cutoff
            if voltage_cutoff_bts < min_cutoff_threshold:
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}V) is too low. Minimum recommended: {int(min_cutoff_threshold)}V")
            
            if voltage_cutoff_vsat < min_cutoff_threshold:
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}V) is too low. Minimum recommended: {int(min_cutoff_threshold)}V")
    
    elif scc_type == 'scc-srne':        
        # Check if minimum required parameters exist
        required_params = ['floating_charging_voltage', 'boost_charging_recovery_voltage']
        missing_params = [param for param in required_params if param not in scc_parameters]
        if missing_params:
            validation_errors.append(f"Missing critical SCC parameters: {', '.join(missing_params)}")
        else:
            # Use available parameters for validation
            floating_charging = scc_parameters.get('floating_charging_voltage', 0)
            boost_recovery = scc_parameters.get('boost_charging_recovery_voltage', 0)
            
            # Convert to voltage (SRNE uses 0.1V units, so multiply by 10 to get mV)
            floating_charging_mv = floating_charging * 10
            boost_recovery_mv = boost_recovery * 10
            
            # Validate that cutoff voltages should not be higher than boost_charging_recovery_voltage
            if voltage_cutoff_bts > boost_recovery_mv:
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}mV) should not be higher than SCC boost recovery ({boost_recovery_mv}mV)")
            
            if voltage_cutoff_vsat > boost_recovery_mv:
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}mV) should not be higher than SCC boost recovery ({boost_recovery_mv}mV)")
            
            # Validate that reconnect voltages should be reasonable compared to floating charging
            if voltage_reconnect_bts > floating_charging_mv:
                validation_errors.append(f"BTS reconnect voltage ({voltage_reconnect_bts}mV) should not be higher than SCC floating charging ({floating_charging_mv}mV)")
            
            if voltage_reconnect_vsat > floating_charging_mv:
                validation_errors.append(f"VSAT reconnect voltage ({voltage_reconnect_vsat}mV) should not be higher than SCC floating charging ({floating_charging_mv}mV)")
                
            # Ensure reasonable gap between cutoff and reconnect relative to SCC parameters
            min_cutoff_threshold = boost_recovery_mv * 0.85  # 85% of boost_recovery as minimum safe cutoff
            if voltage_cutoff_bts < min_cutoff_threshold:
                validation_errors.append(f"BTS cutoff voltage ({voltage_cutoff_bts}mV) is too low. Minimum recommended: {int(min_cutoff_threshold)}mV")
            
            if voltage_cutoff_vsat < min_cutoff_threshold:
                validation_errors.append(f"VSAT cutoff voltage ({voltage_cutoff_vsat}mV) is too low. Minimum recommended: {int(min_cutoff_threshold)}mV")
    
    # Basic validation for any SCC type
    if voltage_reconnect_bts <= voltage_cutoff_bts:
        validation_errors.append("BTS reconnect voltage must be higher than cutoff voltage")
    
    if voltage_reconnect_vsat <= voltage_cutoff_vsat:
        validation_errors.append("VSAT reconnect voltage must be higher than cutoff voltage")
        
    # Additional safety checks
    voltage_gap_bts = voltage_reconnect_bts - voltage_cutoff_bts
    voltage_gap_vsat = voltage_reconnect_vsat - voltage_cutoff_vsat
    
    if voltage_gap_bts < 50:  # Minimum 50mV gap
        validation_errors.append(f"BTS voltage gap ({voltage_gap_bts}mV) is too small. Minimum recommended: 50mV")
    
    if voltage_gap_vsat < 50:  # Minimum 50mV gap
        validation_errors.append(f"VSAT voltage gap ({voltage_gap_vsat}mV) is too small. Minimum recommended: 50mV")
    
    return validation_errors


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
