
import subprocess
from subprocess import Popen
import sys
import os

PATH = '/var/lib/sundaya/jspro-powerdesk/commands'
def change_ip(ip,gw,snmp_ip):
	p = Popen(["sudo","python3",PATH,ip,gw,snmp_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	output, errors = p.communicate()
	# return output
	if 'Success' in output:
		return True
	else:
		return False
