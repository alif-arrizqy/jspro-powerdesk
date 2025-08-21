import subprocess
import subprocess
from subprocess import Popen
from config import *

def change_ip(path, ip, gw, snmp_ip):
    p = Popen(["sudo", "python3", path, ip, gw, snmp_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, errors = p.communicate()
    return output


def bash_command(command, universal_newlines=False, shell=False):
    if isinstance(command, str):
        sep_command = command.split(' ')
    else:
        sep_command = command
    p = Popen(sep_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=universal_newlines, shell=shell)
    output, errors = p.communicate()
    if isinstance(output, bytes):
        return str(output)[2:-1]
    else:
        return output
