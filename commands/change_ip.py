from jinja2 import Environment, FileSystemLoader
import sys
import os

SRC_PATH = '/var/lib/sundaya/jspro-powerdesk/templates/settingtemplates'
DEST_PATH_DHCPCD = '/etc/dhcpcd.conf'
DEST_PATH_SNMP = '/etc/snmp/snmpd.conf'

def dhcpcd_conf(ip,gw,subnet):
	file_loader = FileSystemLoader(searchpath=SRC_PATH)
	env = Environment(loader=file_loader)
	template = env.get_template('dhcpcd.j2')
	output = template.render(static_ip=ip,gateway=gw,subnet_mask=subnet)
	log = open(DEST_PATH_DHCPCD,"w")
	log.write(output)
	log.close()

# def snmpd_conf(ip):
# 	file_loader = FileSystemLoader(searchpath=PATH)
# 	env = Environment(loader=file_loader)
# 	template = env.get_template('snmpd.j2')
# 	output = template.render(static_ip=ip)
# 	log = open(f'{PATH}/snmpd.conf',"w")
# 	log.write(output)
# 	log.close()

if __name__ == '__main__':
	try:
		dhcpcd_conf(sys.argv[1],sys.argv[2],sys.argv[3])
		# snmpd_conf(sys.argv[1])
		print('Success')
		os.system('sudo reboot now')
	except:
		print('Fail')