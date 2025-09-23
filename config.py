from api.redisconnection import connection as red
import json

try:
    device = red.hget('device_config', 'device_version')
    if device is not None:
        device = json.loads(device)
    else:
        print("No device version found in Redis.")
        device = None
except Exception as e:
    print(f"Error fetching device version: {e}")
    device = None

if device is None:
    battery_type = "talis5"
    scc_type = "scc-epever"
    number_of_scc = 2
    number_of_batt = 10
    number_of_cell = 16
    slave_ids = 10
else:
    battery_type = device.get('battery_type')
    if battery_type == "talis5":
        number_of_batt = 10
        number_of_cell = 16
        slave_ids = 10
    elif battery_type == "jspro":
        number_of_batt = 16
        number_of_cell = 14
        slave_ids = 16
    elif battery_type == "mix":
        number_of_batt = 16
        number_of_cell = 16
        slave_ids = 16
    else:
        # Default fallback to talis5 configuration
        number_of_batt = 10
        number_of_cell = 16
        slave_ids = 10

    scc_type = device.get('scc_type')

    if scc_type == "scc-srne":
        number_of_scc = 3
    elif scc_type == "scc-epever":
        number_of_scc = 2
    elif scc_type == "scc-tristar":
        number_of_scc = 2
    else:
        number_of_scc = 2

# Application PATH configuration
# PATH = "/var/lib/sundaya/ehub-talis"  # Production path
PATH = "D:/sundaya/developments/ehub-developments/ehub_talis/ehub-talis"  # Development path
