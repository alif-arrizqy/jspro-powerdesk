import re
from config import number_of_scc

def validate_ip_address(ip_address):
    pat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return True if pat.match(ip_address) else False

def validate_subnet_mask(subnet):
    pat = re.compile('^\A/\d{1,2}$')
    return True if pat.match(subnet) else False

def validate_setting_ip(form):    
    # ip primary
    if form.get('type-ip-address') == 'ip-primary':
        ip_address = validate_ip_address(form.get('ip-address-primary'))
        subnet_mask = validate_subnet_mask(form.get('net-mask'))
        gateway = validate_ip_address(form.get('gateway'))
    
    # ip secondary
    if form.get('type-ip-address') == 'ip-secondary':
        ip_address = validate_ip_address(form.get('ip-address-secondary'))
        subnet_mask = validate_subnet_mask(form.get('net-mask'))
        gateway = validate_ip_address(form.get('gateway'))

    if ip_address:
        if subnet_mask:
            if gateway:
                return True, 'Success'
            return False, 'Gateway Salah'
        else:
            return False, 'Subnet Salah'
    else:
        return False, 'IP Address salah'

def validate_modbus_id(form):
    if number_of_scc == 3:
        scc1_id = int(form.get('scc-id-1'))
        scc2_id = int(form.get('scc-id-2'))
        scc3_id = int(form.get('scc-id-3'))
        if scc1_id > 250:
            return False, 'scc 1 id tdk boleh lebih dr 250'
        if scc2_id > 250:
            return False, 'scc 2 id tdk boleh lebih dr 250'
        if scc3_id > 250:
            return False, 'scc 3 id tdk boleh lebih dr 250'
        if scc1_id != scc2_id:
            if scc2_id != scc3_id:
                if scc3_id != scc1_id:
                    return True, "success"
                else:
                    return False, 'id tdk boleh sama'
            else:
                return False, 'id tdk boleh sama'
        else:
            return False, 'id tdk boleh sama'
    if number_of_scc == 2:
        scc1_id = int(form.get('scc-id-1'))
        scc2_id = int(form.get('scc-id-2'))
        if scc1_id != scc2_id:
            return True, "success"
        else:
            return False, 'id tdk boleh sama'
