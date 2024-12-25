import shutil
import subprocess
import json
from subprocess import Popen
from config import *


def change_ip(PATH,ip,gw,snmp_ip):
	p = Popen(["sudo","python3",PATH,ip,gw,snmp_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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

def get_free_ram():
    command= ["free -h | grep Mi"]
    output = bash_command(command, universal_newlines=True, shell=True)
    line = output[:output.find('\nSwap')][62:].replace(" ", "")
    free_ram = line[line.find('Mi')+2:].replace("Mi", "")
    return free_ram

def get_disk_detail():
    disk = shutil.disk_usage('/')
    return disk

def update_device_version(path, form):
	data = {}
	for key, value in form.items():
		# validate value
		if key == 'ehub_version':
			if value == 'new':
				data[key] = value
			else:
				return False
		elif key == 'panel2_type':
			if value == 'old':
				data[key] = value
			elif value == 'new':
				data[key] = value
			else:
				return False
		elif key == 'site_type':
			if value == 'tvd_bakti':
				data[key] = value
			elif value == 'bakti':
				data[key] = value
			else:
				return False
		elif key == 'mppt_type':
			if value == 'mppt-srne':
				data[key] = value
			elif value == 'mppt-epveper':
				data[key] = value
			else:
				return False
		elif key == 'battery_type':
			if value == 'jspro':
				data[key] = value
			elif value == 'talis5':
				data[key] = value
			elif value == 'hybrid':
				data[key] = value
			else:
				return False
		elif key == 'mppt_source':
			if value == 'tcp':
				data[key] = value
			elif value == 'serial':
				data[key] = value
			elif value == 'usb':
				data[key] = value
			else:
				return False

	ehub_version = data.get('ehub_version')
	panel2_type = data.get('panel2_type')
	site_type = data.get('site_type')
	mppt_type = data.get('mppt_type')
	battery_type = data.get('battery_type')
	mppt_source = data.get('mppt_source')

	# read json file
	with open(path, 'r') as f:
		data = json.load(f)
	data['device_version']['ehub_version'] = ehub_version
	data['device_version']['panel2_type'] = panel2_type
	data['device_version']['site_type'] = site_type
	data['device_version']['mppt_type'] = mppt_type
	data['device_version']['mppt_source'] = mppt_source
	data['device_version']['battery_type'] = battery_type

	# write json file
	with open(path, 'w') as f:
		json.dump(data, f, indent=4)
	return True

def update_config_mppt(path, form):
	data = {}
	for key, value in form.items():
		if key == 'submit':
			continue
		else:
			data[key] = value
	
	voltage_reconnect_bts = int(data.get('voltage_reconnect_bts'))
	voltage_cutoff_bts = int(data.get('voltage_cutoff_bts'))
	voltage_reconnect_vsat = int(data.get('voltage_reconnect_vsat'))
	voltage_cutoff_vsat = int(data.get('voltage_cutoff_vsat'))

	# validate
	bts_reconnect = round(voltage_reconnect_bts / 40) + 1
	bts_undervoltage_warning_level = bts_reconnect - 1
	# bts_overdischarge_voltage = bts_reconnect - 2
	bts_cutoff = round(voltage_cutoff_bts / 40)
	bts_discharging_limit_voltage = bts_cutoff - 2

	vsat_reconnect = round(voltage_reconnect_vsat / 40)
	vsat_undervoltage_warning_level = vsat_reconnect - 1
	# vsat_overdischarge_voltage = vsat_reconnect - 2
	vsat_cutoff = round(voltage_cutoff_vsat / 40)
	vsat_discharging_limit_voltage = vsat_cutoff - 2

	if vsat_reconnect > vsat_undervoltage_warning_level > vsat_cutoff > vsat_discharging_limit_voltage:
		if bts_reconnect > bts_undervoltage_warning_level > bts_cutoff > bts_discharging_limit_voltage:
			# mppt srne
			if number_of_mppt == 3:
				host = data.get('host')
				port = data.get('port')
				battery_capacity = int(data.get('battery_capacity'))
				system_voltage = int(data.get('system_voltage'))
				battery_type = int(data.get('battery_type'))
				overvoltage_threshold = int(data.get('overvoltage_threshold'))
				charging_limit_voltage = int(data.get('charging_limit_voltage'))
				equalizing_charge_voltage = int(data.get('equalizing_charge_voltage'))
				boost_charging_voltage = int(data.get('boost_charging_voltage'))
				floating_charging_voltage = int(data.get('floating_charging_voltage'))
				boost_charging_recovery_voltage = int(data.get('boost_charging_recovery_voltage'))
				overdischarge_time_delay = int(data.get('overdischarge_time_delay'))
				equalizing_charging_time = int(data.get('equalizing_charging_time'))
				boost_charging_time = int(data.get('boost_charging_time'))
				equalizing_charging_interval = int(data.get('equalizing_charging_interval'))
				temperature_comp = int(data.get('temperature_comp'))

				# read json file
				with open(path, 'r') as f:
					data = json.load(f)
				data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
				data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
				data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
				data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat
				
				data['mppt_srne']['host'] = host
				data['mppt_srne']['port'] = port
				data['mppt_srne']['parameter']['battery_capacity'] = battery_capacity
				data['mppt_srne']['parameter']['system_voltage'] = system_voltage
				data['mppt_srne']['parameter']['battery_type'] = battery_type
				data['mppt_srne']['parameter']['overvoltage_threshold'] = overvoltage_threshold
				data['mppt_srne']['parameter']['charging_limit_voltage'] = charging_limit_voltage
				data['mppt_srne']['parameter']['equalizing_charge_voltage'] = equalizing_charge_voltage
				data['mppt_srne']['parameter']['boost_charging_voltage'] = boost_charging_voltage
				data['mppt_srne']['parameter']['floating_charging_voltage'] = floating_charging_voltage
				data['mppt_srne']['parameter']['boost_charging_recovery_voltage'] = boost_charging_recovery_voltage
				data['mppt_srne']['parameter']['overdischarge_time_delay'] = overdischarge_time_delay
				data['mppt_srne']['parameter']['equalizing_charging_time'] = equalizing_charging_time
				data['mppt_srne']['parameter']['boost_charging_time'] = boost_charging_time
				data['mppt_srne']['parameter']['equalizing_charging_interval'] = equalizing_charging_interval
				data['mppt_srne']['parameter']['temperature_comp'] = temperature_comp
				
				# write json file
				with open(path, 'w') as f:
					json.dump(data, f, indent=4)
				return True
			# mppt epveper
			if number_of_mppt == 2:
				host = data.get('host')
				port = data.get('port')
				overvoltage_disconnect = int(data.get('overvoltage_disconnect'))
				overvoltage_reconnect = int(data.get('overvoltage_reconnect'))

				# read json file
				with open(path, 'r') as f:
					data = json.load(f)
				data['handle_relay']['voltage_reconnect_bts'] = voltage_reconnect_bts
				data['handle_relay']['voltage_cutoff_bts'] = voltage_cutoff_bts
				data['handle_relay']['voltage_reconnect_vsat'] = voltage_reconnect_vsat
				data['handle_relay']['voltage_cutoff_vsat'] = voltage_cutoff_vsat

				data['mppt_epveper']['host'] = host
				data['mppt_epveper']['port'] = port
				data['mppt_epveper']['parameter']['overvoltage_disconnect'] = overvoltage_disconnect
				data['mppt_epveper']['parameter']['overvoltage_reconnect'] = overvoltage_reconnect

				# write json file
				with open(path, 'w') as f:
					json.dump(data, f, indent=4)
				return True
		return False
	return False
