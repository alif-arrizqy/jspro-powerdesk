from utils import bash_command

# IP Address
def get_ip_address(interface):
    command = [f"ifconfig {interface} | grep 'inet ' | awk '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    ipaddress = output.replace("\n", "")
    return ipaddress


def get_subnet_mask(interface):
    """Get subnet mask from interface and return in format /XX"""
    command = [f"ip -o -f inet addr show {interface} | awk '/scope global/ {{print $4}}' | awk -F'/' '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    subnet_mask = output.strip()
    
    # Normalize subnet_mask to always have format /XX
    if not subnet_mask:
        return ""
    
    # Convert to string and strip whitespace
    subnet_mask = str(subnet_mask).strip()
    
    # If already starts with '/', return as is
    if subnet_mask.startswith('/'):
        return subnet_mask
    
    # If it's just a number, add '/' prefix
    if subnet_mask.isdigit():
        return f"/{subnet_mask}"
    
    # If it doesn't start with '/', try to extract number
    # Remove any leading non-digit characters
    digits = ''.join(filter(str.isdigit, subnet_mask))
    if digits:
        return f"/{digits}"
    
    # If we can't normalize it, return as is (will fail validation later)
    return subnet_mask


def get_gateway(interface):
    command = [f"ip route show dev {interface} | awk '/default/ {{print $3}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    gateway = output.replace("\n", "")
    return gateway