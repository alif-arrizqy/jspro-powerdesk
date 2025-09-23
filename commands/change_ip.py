from jinja2 import Environment, FileSystemLoader
import sys
import os

# Update paths to correct locations
SRC_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'settingtemplates')
DEST_PATH_DHCPCD = '/etc/dhcpcd.conf'
DEST_PATH_SNMP = '/etc/snmp/snmpd.conf'

def dhcpcd_conf(ip, gw, subnet):
    """Generate dhcpcd.conf file with static IP configuration"""
    try:
        file_loader = FileSystemLoader(searchpath=SRC_PATH)
        env = Environment(loader=file_loader)
        template = env.get_template('dhcpcd.j2')
        output = template.render(static_ip=ip, gateway=gw, subnet_mask=subnet)
        
        with open(DEST_PATH_DHCPCD, "w") as log:
            log.write(output)
        
        return True
    except Exception as e:
        print(f"Error writing dhcpcd.conf: {e}")
        return False

if __name__ == '__main__':
    try:
        if len(sys.argv) < 4:
            print('Usage: python3 change_ip.py <ip> <gateway> <subnet>')
            sys.exit(1)
        
        ip = sys.argv[1]
        gateway = sys.argv[2] 
        subnet = sys.argv[3]
        
        # Generate configuration files
        dhcp_success = dhcpcd_conf(ip, gateway, subnet)
        
        if dhcp_success:
            print('Success')
            # Restart networking instead of full reboot for testing
            # os.system('sudo systemctl restart dhcpcd')
            # For production, use reboot
            os.system('sudo reboot now')
        else:
            print('Fail')
            
    except Exception as e:
        print(f'Fail: {e}')