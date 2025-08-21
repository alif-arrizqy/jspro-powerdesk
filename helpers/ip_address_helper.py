from utils import bash_command

# IP Address
def get_ip_address(interface):
    command = [f"ifconfig {interface} | grep 'inet ' | awk '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    ipaddress = output.replace("\n", "")
    return ipaddress


def get_subnet_mask(interface):
    command = [f"ip -o -f inet addr show {interface} | awk '/scope global/ {{print $4}}' | awk -F'/' '{{print $2}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    subnet_mask = output.strip()
    return subnet_mask


def get_gateway(interface):
    command = [f"ip route show dev {interface} | awk '/default/ {{print $3}}'"]
    output = bash_command(command=command, universal_newlines=True, shell=True)
    gateway = output.replace("\n", "")
    return gateway