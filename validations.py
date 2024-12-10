import re
from config import number_of_mppt

def validate_ip_address(ip_address):
    pat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return True if pat.match(ip_address) else False

def validate_subnet_mask(subnet):
    pat = re.compile('^\A/\d{1,2}$')
    return True if pat.match(subnet) else False

def validate_setting_ip(form):
    if form.get('ip_address') is not None:
        ip_address = validate_ip_address(form.get('ip_address'))
        subnet_mask = validate_subnet_mask(form.get('subnet_mask'))
        gateway = validate_ip_address(form.get('gateway'))
    else:
        ip_address = validate_ip_address(form.get('ip_address_custom'))
        subnet_mask = validate_subnet_mask(form.get('subnet_mask_custom'))
        gateway = validate_ip_address(form.get('gateway_custom'))

    if ip_address:
        if subnet_mask:
            if gateway:
                return True, 'Success'
            return False, 'gateway salah'
        else:
            return False, 'subnet salah'
    else:
        return False, 'ip_address salah'

def validate_modbus_id(form):
    if number_of_mppt == 3:
        mppt1_id = int(form.get('mppt1_id'))
        mppt2_id = int(form.get('mppt2_id'))
        mppt3_id = int(form.get('mppt3_id'))
        if mppt1_id > 247:
            return False, 'mppt 1 id tdk boleh lebih dr 247'
        if mppt2_id > 247:
            return False, 'mppt 2 id tdk boleh lebih dr 247'
        if mppt3_id > 247:
            return False, 'mppt 3 id tdk boleh lebih dr 247'
        if mppt1_id != mppt2_id:
            if mppt2_id != mppt3_id:
                if mppt3_id != mppt1_id:
                    return True, "success"
                else:
                    return False, 'id tdk boleh sama'
            else:
                return False, 'id tdk boleh sama'
        else:
            return False, 'id tdk boleh sama'
    if number_of_mppt == 2:
        mppt1_id = int(form.get('mppt1_id'))
        mppt2_id = int(form.get('mppt2_id'))
        if mppt1_id != mppt2_id:
            return True, "success"
        else:
            return False, 'id tdk boleh sama'
