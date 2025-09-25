import json
import logging
import os
import traceback
from config import *

# Configure logging for production use with file output
log_file = f"/var/lib/sundaya/jspro-powerdesk/logs/handle_relay_config_update.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
            elif value == 'scc-epever':
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
    elif scc_type == 'scc-epever':
        data['scc_epever']['port'] = port
        data['scc_epever']['host'] = host
        data['scc_epever']['scan'] = scan
    elif scc_type == 'scc-tristar':
        data['scc_tristar']['port'] = port
        data['scc_tristar']['host'] = host
        data['scc_tristar']['scan'] = scan

    # write json file
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    return True


def update_config_cutoff_reconnect(path, form):
    """
    Enhanced cutoff/reconnect update function with comprehensive error handling and logging
    """
    logger.info("=== Starting cutoff/reconnect configuration update ===")
    
    try:
        # Step 1: Parse and validate form data
        logger.info(f"Step 1: Parsing form data for path: {path}")
        data = {}
        for key, value in form.items():
            logger.debug(f"Form data: {key} = {value}")
            if key != 'submit':
                data[key] = value

        # Check required fields
        required_fields = ['voltage_reconnect_bts', 'voltage_cutoff_bts', 'voltage_reconnect_vsat', 'voltage_cutoff_vsat']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            logger.error(f"Missing required form fields: {missing_fields}")
            return False

        # Parse voltage values with error handling
        try:
            voltage_reconnect_bts = int(data['voltage_reconnect_bts'])
            voltage_cutoff_bts = int(data['voltage_cutoff_bts'])
            voltage_reconnect_vsat = int(data['voltage_reconnect_vsat'])
            voltage_cutoff_vsat = int(data['voltage_cutoff_vsat'])
            
            logger.info(f"Parsed voltages:")
            logger.info(f"  BTS: cutoff={voltage_cutoff_bts}mV, reconnect={voltage_reconnect_bts}mV")
            logger.info(f"  VSAT: cutoff={voltage_cutoff_vsat}mV, reconnect={voltage_reconnect_vsat}mV")
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid voltage values: {e}")
            return False

        # Step 2: Read and validate config file
        logger.info("Step 2: Reading config file")
        
        if not os.path.exists(path):
            logger.error(f"Config file does not exist: {path}")
            return False
            
        if not os.access(path, os.R_OK):
            logger.error(f"No read permission for config file: {path}")
            return False
            
        if not os.access(path, os.W_OK):
            logger.error(f"No write permission for config file: {path}")
            return False

        try:
            with open(path, 'r') as f:
                config_data = json.load(f)
            logger.info("Successfully loaded config file")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return False

        # Step 3: Validate config structure and get SCC info
        logger.info("Step 3: Validating config structure")
        
        if 'device_version' not in config_data:
            logger.warning("Missing device_version section in config")
            config_data['device_version'] = {}
            
        if 'handle_relay' not in config_data:
            logger.warning("Missing handle_relay section in config - will be created")
            config_data['handle_relay'] = {}

        scc_type = config_data.get('device_version', {}).get('scc_type', '')
        scc_type_underscore = scc_type.replace('-', '_')
        scc_parameters = config_data.get(scc_type_underscore, {}).get('parameter', {})
        
        logger.info(f"SCC Type: {scc_type}")
        if scc_parameters:
            logger.info(f"Found SCC parameters: {list(scc_parameters.keys())}")

        # Step 4: Perform comprehensive validation
        logger.info("Step 4: Performing voltage validation")
        validation_passed = True
        validation_errors = []

        # Basic validation
        if voltage_reconnect_bts <= voltage_cutoff_bts:
            validation_errors.append("BTS reconnect voltage must be higher than cutoff voltage")
        
        if voltage_reconnect_vsat <= voltage_cutoff_vsat:
            validation_errors.append("VSAT reconnect voltage must be higher than cutoff voltage")
            
        # Gap validation
        voltage_gap_bts = voltage_reconnect_bts - voltage_cutoff_bts
        voltage_gap_vsat = voltage_reconnect_vsat - voltage_cutoff_vsat
        
        if voltage_gap_bts < 50:
            validation_errors.append(f"BTS voltage gap ({voltage_gap_bts}mV) too small. Minimum: 50mV")
        
        if voltage_gap_vsat < 50:
            validation_errors.append(f"VSAT voltage gap ({voltage_gap_vsat}mV) too small. Minimum: 50mV")

        # SCC-specific validation
        if scc_type == 'scc-epever' and scc_parameters:
            float_charging = scc_parameters.get('float_charging_voltage', 0)
            if float_charging:
                if voltage_reconnect_bts > float_charging:
                    validation_errors.append(f"BTS reconnect ({voltage_reconnect_bts}V) > SCC float charging ({float_charging}V)")
                if voltage_reconnect_vsat > float_charging:
                    validation_errors.append(f"VSAT reconnect ({voltage_reconnect_vsat}V) > SCC float charging ({float_charging}V)")
                    
        elif scc_type == 'scc-srne' and scc_parameters:
            floating_charging = scc_parameters.get('floating_charging_voltage', 0)
            if floating_charging:
                floating_charging_mv = floating_charging * 40
                if voltage_reconnect_bts > floating_charging_mv:
                    validation_errors.append(f"BTS reconnect ({voltage_reconnect_bts}mV) > SCC floating charging ({floating_charging_mv}mV)")
                if voltage_reconnect_vsat > floating_charging_mv:
                    validation_errors.append(f"VSAT reconnect ({voltage_reconnect_vsat}mV) > SCC floating charging ({floating_charging_mv}mV)")

        # Check validation results
        if validation_errors:
            validation_passed = False
            logger.warning("Validation failed:")
            for error in validation_errors:
                logger.warning(f"  - {error}")
            return False

        # Step 5: Update configuration
        logger.info("Step 5: Updating configuration values")
        
        config_data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
        config_data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
        config_data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
        config_data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

        # Write main config file
        try:
            with open(path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            logger.info("Successfully updated configuration file")
            logger.info("=== Cutoff/reconnect update completed successfully ===")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write config file: {e}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error in cutoff/reconnect update: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    ip_address = form_data.get('ip-address')
    net_mask = form_data.get('net-mask')
    gateway = form_data.get('gateway')
    site = form_data.get('site')
    
    if ip_address:
        data['ip_configuration']['ip_address'] = ip_address
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


def update_setting_mqtt(path, data):
    """Update MQTT settings in config_device.json"""
    # Read json file first
    with open(path, 'r') as f:
        config_data = json.load(f)
    
    # Ensure mqtt_config section exists
    if 'mqtt_config' not in config_data:
        config_data['mqtt_config'] = {}
    
    # Update MQTT settings from data dictionary
    mqtt_settings = ['host', 'port', 'username', 'password', 'openvpn_ip', 'topic']
    for setting in mqtt_settings:
        if setting in data:
            # config_data['mqtt_config'][setting] = data[setting]
            # if port is provided, convert to int
            if setting == 'port':
                try:
                    config_data['mqtt_config'][setting] = int(data[setting])
                except ValueError:
                    continue
            else:
                config_data['mqtt_config'][setting] = data[setting]
    
    # Write json file
    with open(path, 'w') as f:
        json.dump(config_data, f, indent=4)
    return True