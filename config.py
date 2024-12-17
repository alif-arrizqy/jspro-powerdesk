from api.redisconnection import red

try:
    device = red.hget('device_version', 'device_version')
except Exception:
    device = None

if device is None:
    number_of_scc = 2
    number_of_batt = 10
else:
    device = device.decode('utf-8')

    if eval(device)['scc_type'] is None:
        scc_type = None
    else:
        scc_type = eval(device)['scc_type']

    if scc_type == "scc-srne":
        number_of_scc = 3
    elif scc_type == "scc-epveper":
        number_of_scc = 2
    elif scc_type == "scc-tristar":
        number_of_scc = 2
    else:
        number_of_scc = 2
    number_of_batt = 10

slave_ids = 10
