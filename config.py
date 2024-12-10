from api.redisconnection import red

try:
    device = red.hget('device_version', 'device_version')
except Exception:
    device = None

if device is None:
    number_of_mppt = 3
    number_of_batt = 16
else:
    device = device.decode('utf-8')

    if eval(device)['mppt_type'] is None:
        mppt_type = None
    else:
        mppt_type = eval(device)['mppt_type']

    if mppt_type == "mppt-srne":
        number_of_mppt = 3
    elif mppt_type == "mppt-epveper":
        number_of_mppt = 2
    else:
        number_of_mppt = 2
    number_of_batt = 16

slave_ids = 10
