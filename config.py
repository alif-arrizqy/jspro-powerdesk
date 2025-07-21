from api.redisconnection import connection as red
import json

try:
    device = red.hget('device_config', 'device_version')
    if device is not None:
        device = json.loads(device)
    else:
        device = None
except Exception as e:
    print(f"Error fetching device version: {e}")
    device = None

if device is None:
    number_of_scc = 2
    number_of_batt = 10
    number_of_cell = 16
else:
    scc_type = device.get('scc_type')

    if scc_type == "scc-srne":
        number_of_scc = 3
    elif scc_type == "scc-epveper":
        number_of_scc = 2
    elif scc_type == "scc-tristar":
        number_of_scc = 2
    else:
        number_of_scc = 2

    number_of_batt = 10
    number_of_cell = 16

slave_ids = 10
