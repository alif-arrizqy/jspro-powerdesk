import os
import json
import markdown
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for, make_response
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from config import *
from helpers import *
from utils import change_ip, bash_command
from api.core import register_blueprints, register_error_handlers
from api.redisconnection import connection as red
from auths import USERS, verify_password, record_successful_login, record_failed_attempt, is_user_locked, get_user_role, audit_access, get_menu_access, can_access_page
from validations import validate_setting_ip, validate_modbus_id
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Register all API blueprints and error handlers
register_blueprints(app)
register_error_handlers(app)

cors = CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    if username in USERS:
        return User(username)
    return None

@app.route('/', methods=['GET'])
# @login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'dashboard'):
        audit_access(username, 'dashboard', 'access_denied')
        flash('You do not have permission to access the dashboard.', 'error')
        return redirect(url_for('logout'))
    
    site_name = ""
    try:
        # get current username
        username = current_user.id
        
        # get site name
        site_name = red.hget('device_config', 'site_name')
        
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'battery_type': battery_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc,
            'number_of_battery': number_of_batt,
        }
        
        # Audit page access
        audit_access(username, 'dashboard', 'view')
        
    except Exception as e:
        print(f"index() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'battery_type': battery_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc,
            'number_of_battery': number_of_batt,
        }
    return render_template('index.html', **context)


@app.route('/scc', methods=['GET'])
@login_required
def scc():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'scc_monitoring'):
        audit_access(username, 'scc_monitoring', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc
        }
        
        # Audit page access
        audit_access(username, 'scc_monitoring', 'view')
        
    except Exception as e:
        print(f"scc() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc
        }
    return render_template('scc.html', **context)


@app.route('/battery', methods=['GET'])
@login_required
def battery():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'battery_monitoring'):
        audit_access(username, 'battery_monitoring', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'battery_type': battery_type,
            'number_of_battery': number_of_batt,
            'number_of_cell': number_of_cell
        }
        
        # Audit page access
        audit_access(username, 'battery_monitoring', 'view')
        
    except Exception as e:
        print(f"battery() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'battery_type': battery_type,
            'number_of_battery': number_of_batt,
            'number_of_cell': number_of_cell
        }
    return render_template('battery.html', **context)


@app.route('/rectifier', methods=['GET'])
@login_required
def rectifier():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'rectifier_monitoring'):
        audit_access(username, 'rectifier_monitoring', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        # Load configuration data
        config_path = f'{PATH}/config_device.json'
        config = {}
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config_device.json: {e}")
            config = {
                'rectifier_config': {
                    'host': '127.0.0.1',
                    'port': 161
                }
            }
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            'config': config
            # 'ip_address': '192.168.4.44'
        }
        # Audit page access
        audit_access(username, 'rectifier_monitoring', 'view')
    
    except Exception as e:
        print(f"rectifier() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            'config': {
                'rectifier_config': {
                    'host': '127.0.0.1',
                    'port': 161
                }
            }
            # 'ip_address': '
        }
    return render_template('rectifier.html', **context)


@app.route('/datalog', methods=['GET'])
@login_required
def datalog():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'datalog'):
        audit_access(username, 'datalog', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.4.44'
        }
        
        # Audit page access
        audit_access(username, 'datalog', 'view')
        
    except Exception as e:
        print(f"datalog() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.4.3'
        }
    return render_template('datalog.html', **context)


@app.route('/scc-alarm-log', methods=['GET'])
@login_required
def scc_alarm_log():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'scc_alarm_log'):
        audit_access(username, 'scc_alarm_log', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'number_of_scc': number_of_scc,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.3.4'
        }
        
        # Audit page access
        audit_access(username, 'scc_alarm_log', 'view')
        
    except Exception as e:
        print(f"scc_alarm_log() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.3.4'
        }
    return render_template('scc-alarm-log.html', **context)

@app.route('/mqtt-service', methods=['GET'])
@login_required
def mqtt_service():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'mqtt_service'):
        audit_access(username, 'mqtt_service', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    path = f'{PATH}/config_device.json'
    with open(path, 'r') as file:
        data = json.load(file)
    
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'mqtt_config': data.get('mqtt_config', {}),
            # User passwords for service authentication
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
        
        # Audit page access
        audit_access(username, 'mqtt_service', 'view')
        
    except Exception as e:
        print(f"mqtt_service() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'mqtt_config': data.get('mqtt_config', {}),
            # User passwords for service authentication
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
    return render_template('mqtt-service.html', **context)

@app.route('/systemd-service', methods=['GET'])
@login_required
def systemd_service():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'systemd_service'):
        audit_access(username, 'systemd_service', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            # User passwords for service authentication
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
        
        # Audit page access
        audit_access(username, 'systemd_service', 'view')
        
    except Exception as e:
        print(f"systemd_service() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            # User passwords for service authentication
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
    return render_template('systemd-service.html', **context)

@app.route('/snmp-service', methods=['GET'])
@login_required
def snmp_service():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'snmp_service'):
        audit_access(username, 'snmp_service', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
        
        # Audit page access
        audit_access(username, 'snmp_service', 'view')
        
    except Exception as e:
        print(f"snmp_service() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
            'user_passwords': {
                'apt': os.getenv('APT_PASSWORD'),
                'teknisi': os.getenv('TEKNISI_PASSWORD'),
                'admin': os.getenv('ADMIN_PASSWORD')
            }
        }
    return render_template('snmp-service.html', **context)

@app.route('/power-operation', methods=['GET'])
@login_required
def power_operation():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'power_operations'):
        audit_access(username, 'power_operations', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        site_name = red.hget('device_config', 'site_name')
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1'
        }
        
        # Audit page access
        audit_access(username, 'power_operations', 'view')
        
    except Exception as e:
        print(f"power_operation() error: {e}")
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1'
        }
    return render_template('power-operation.html', **context)


@app.route('/site-information', methods=['GET'])
@login_required
def site_information():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'site_information'):
        audit_access(username, 'site_information', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    path = f'{PATH}/config_device.json'
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        with open(path, 'r') as file:
            data = json.load(file)
        
        # get site name
        site_name = red.hget('device_config', 'site_name')
        
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'site_information': data.get('site_information'),
            'device_model': data.get('device_model'),
            'device_version': data.get('device_version'),
            'ip_address': get_ip_address('eth0'),
            'ip_address_primary': get_ip_address('eth0'),
            'subnet_mask': f"/{get_subnet_mask('eth0')}",
            'gateway': get_gateway('eth0'),
            # 'ip_address': '192.168.1.1',
            # 'ip_address_primary': '192.168.1.1',
            # 'subnet_mask': '/29',
            # 'gateway': '192.168.1.1'
        }
        
        # Audit page access
        audit_access(username, 'site_information', 'view')
        
    except Exception as e:
        print(f"site_information() error: {e}")
        
        with open(path, 'r') as file:
            data = json.load(file)
        
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'site_information': data.get('site_information'),
            'device_model': data.get('device_model'),
            'device_version': data.get('device_version'),
            'ip_address': get_ip_address('eth0'),
            'ip_address_primary': get_ip_address('eth0'),
            'subnet_mask': f"/{get_subnet_mask('eth0')}",
            'gateway': get_gateway('eth0'),
            # 'ip_address': '192.168.1.1',
            # 'ip_address_primary': '192.168.1.1',
            # 'subnet_mask': '/29',
            # 'gateway': '192.168.1.1'
        }
    return render_template('site-information.html', **context)


@app.route('/setting-device', methods=['GET', 'POST'])
@login_required
def setting_device():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'device_settings'):
        audit_access(username, 'device_settings', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""

    # path config device
    path = f'{PATH}/config_device.json'
    
    form_site_information = request.form.get('site-information-form')
    form_device_model = request.form.get('device-info-form')
    form_device_version = request.form.get('device-version-form')

    if request.method == 'POST':
        data = request.form.to_dict()
        
        if form_site_information:
            response = update_site_information(path, data)            
            if response:
                flash('Site Information has been updated successfully', 'success')
                audit_access(username, 'device_settings', 'update_site_information')
                bash_command('sudo systemctl restart device_config_loader.service webapp.service')
            else:
                flash('Failed to update Site Information', 'danger')
            return redirect(url_for('setting_device'))
        
        if form_device_model:
            response = update_device_model(path, data)
            if response:
                flash('Device Info has been updated successfully', 'success')
                audit_access(username, 'device_settings', 'update_device_model')
                bash_command('sudo systemctl restart device_config_loader.service webapp.service')
            else:
                flash('Failed to update Device Info', 'danger')
            return redirect(url_for('setting_device'))
        
        if form_device_version:
            response = update_device_version(path, data)
            if response:
                flash('Device Version has been updated successfully', 'success')
                audit_access(username, 'device_settings', 'update_device_version')
                bash_command('sudo systemctl restart scc.service device_config_loader.service webapp.service')
            else:
                flash('Failed to update Device Version', 'danger')
            return redirect(url_for('setting_device'))
    
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        with open(path, 'r') as file:
            data = json.load(file)

        # get site name
        site_name = red.hget('device_config', 'site_name')

        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'site_information': data.get('site_information'),
            'device_model': data.get('device_model'),
            'device_version': data.get('device_version'),
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
        }
        
        # Audit page access
        audit_access(username, 'device_settings', 'view')
        
    except Exception as e:
        print(f"setting_device() error: {e}")
        
        with open(path, 'r') as file:
            data = json.load(file)

        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'site_information': data.get('site_information'),
            'device_model': data.get('device_model'),
            'device_version': data.get('device_version'),
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
        }
    return render_template('setting-device.html', **context)


@app.route('/setting-ip', methods=['GET', 'POST'])
@login_required
def setting_ip():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'ip_configuration'):
        audit_access(username, 'ip_configuration', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    ip_address = ""
    subnet_mask = ""
    gateway = ""
    
    # path config device
    path = f'{PATH}/config_device.json'
    
    if request.method == 'POST':
        data = request.form.to_dict()        
        is_valid = validate_setting_ip(request.form)
        if is_valid:
            try:
                # Save to config_device.json
                with open(path, 'r') as f:
                    config_data = json.load(f)
                
                # Update IP configuration section
                if 'ip_configuration' not in config_data:
                    config_data['ip_configuration'] = {}
                
                config_data['ip_configuration']['ip_address'] = data.get('ip-address', '')
                config_data['ip_configuration']['subnet_mask'] = data.get('net-mask', '')
                config_data['ip_configuration']['gateway'] = data.get('gateway', '')
                
                # Save updated configuration
                with open(path, 'w') as f:
                    json.dump(config_data, f, indent=4)
                
                audit_access(username, 'ip_configuration', 'update_ip_settings')
                
                # Apply network configuration changes
                change_ip_path = f'./commands/change_ip.py'
                type_ip_address = data.get('type-ip-address')
                ip_address = data.get('ip-address')
                subnet_mask = data.get('net-mask')
                gateway = data.get('gateway')
                
                if type_ip_address == 'ip-address' and ip_address and gateway and subnet_mask:
                    result = change_ip(change_ip_path, ip_address, gateway, subnet_mask)
                    if result:
                        flash('IP Configuration has been saved and applied successfully. System will reboot.', 'success')
                    else:
                        flash('IP Configuration saved but failed to apply to system. Please check logs.', 'warning')
                else:
                    flash('IP Configuration saved successfully', 'success')
                    
            except Exception as e:
                print(f"Error updating IP configuration: {e}")
                flash('Failed to save IP Configuration', 'danger')
                
            return redirect(url_for('setting_ip'))
        else:
            flash('Invalid IP Address format', 'danger')
            return redirect(url_for('setting_ip'))
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        # get site name
        site_name = red.hget('device_config', 'site_name')
        
        # Initialize default values
        ip_address = ""
        subnet_mask = ""
        gateway = ""
        
        # open data site
        with open(f'./data_site.json', 'r') as f:
            data_ip = json.load(f)
        
        ipaddr = get_ip_address('eth0')
        for i in data_ip:
            if i['ip'] == ipaddr:
                ip_address = i['ip']
                subnet_mask = i['subnet_mask']
                gateway = i['gateway']
                break
        
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'data_ip': data_ip,
            'scc_type': scc_type,
            'ip_address': ip_address,
            'subnet_mask': subnet_mask,
            'gateway': gateway
        }
        
        # Audit page access
        audit_access(username, 'ip_configuration', 'view')
        
    except Exception as e:
        print(f"setting_ip() error: {e}")
        
        # Initialize default values
        ip_address = ""
        subnet_mask = ""
        gateway = ""
        
        # Fallback to default data_ip
        try:
            with open(f'{PATH}/data_site.json', 'r') as f:
                data_ip = json.load(f)
        except:
            data_ip = []
            
        ipaddr = get_ip_address('eth0')
        for i in data_ip:
            if i['ip'] == ipaddr:
                ip_address = i['ip']
                subnet_mask = i['subnet_mask']
                gateway = i['gateway']
                break
        
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'data_ip': data_ip,
            'scc_type': scc_type,
            'ip_address': ip_address,
            'subnet_mask': subnet_mask,
            'gateway': gateway
        }
    return render_template('setting-ip.html', **context)


@app.route('/setting-scc', methods=['GET', 'POST'])
@login_required
def setting_scc():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'scc_settings'):
        audit_access(username, 'scc_settings', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""
    
    # path config device
    path = f'{PATH}/config_device.json'
    
    # open config device
    with open(path, 'r') as file:
        data = json.load(file)
    
    if request.method == 'POST':
        form_data = request.form.to_dict()
        scc_type_form = request.form.get('scc-type-form')
        scc_setting_id_form = request.form.get('scc-setting-id-form')
        config_relay_form = request.form.get('config-relay-form')
        config_scc_form = request.form.get('config-scc-form')
        
        if scc_type_form == 'scc-type-form':
            response = update_scc_type(path, form_data)
            if response:
                flash('SCC Type has been updated successfully', 'success')
                audit_access(username, 'scc_settings', 'update_scc_type')
                bash_command('sudo systemctl restart scc.service device_config_loader.service webapp.service')
            else:
                flash('Failed to update SCC Type', 'danger')
            return redirect(url_for('setting_scc'))
            
        if scc_setting_id_form == 'scc-setting-id-form':
            is_valid, msg = validate_modbus_id(request.form)
            if is_valid:
                if number_of_scc == 3:
                    for i in range(1, 4):
                        red.set(f'scc:{i}:id', request.form.get(f'scc-id-{i}'))
                if number_of_scc == 2:
                    for i in range(1, 3):
                        red.set(f'scc:{i}:id', request.form.get(f'scc-id-{i}'))
                bash_command('sudo systemctl restart scc.service')
                bash_command('sudo systemctl daemon-reload')
                flash('SCC ID has been updated successfully', 'success')
                audit_access(username, 'scc_settings', 'update_scc_id')
            else:
                flash('Failed to update SCC ID', 'danger')
            return redirect(url_for('setting_scc'))
            
        if config_relay_form == 'config-relay-form':
            response = update_config_cutoff_reconnect(path, form_data)
            if response:
                flash('Config Value Cut off / Reconnect has been updated successfully', 'success')
                audit_access(username, 'scc_settings', 'update_relay_config')
                os.system(f'sudo python3 {PATH}/config_scc.py')
                bash_command('sudo systemctl restart scc.service webapp.service')
            else:
                flash('Failed to update Config Value Cut off / Reconnect', 'danger')
            return redirect(url_for('setting_scc'))
            
        if config_scc_form == 'config-scc-form':
            response = update_config_scc(path, form_data)
            if response:
                flash('Config Value SCC has been updated successfully', 'success')
                audit_access(username, 'scc_settings', 'update_scc_config')
                os.system(f'sudo python3 {PATH}/config_scc.py')
                bash_command('sudo systemctl restart scc.service webapp.service')
            else:
                flash('Failed to update Config Value SCC', 'danger')
            return redirect(url_for('setting_scc'))
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        # get site name
        site_name = red.hget('device_config', 'site_name')
        
        # Audit page access
        audit_access(username, 'scc_settings', 'view')
        
    except Exception as e:
        print(f"setting_scc() error: {e}")
        site_name = 'Site Name'
    
    # get scc type
    scc_type_data = data.get('device_version').get('scc_type')
    # replace - to _
    scc_type_underscore = scc_type_data.replace('-', '_')
    
    # get scc id from redis
    if number_of_scc == 2:
        try:
            scc_id_1 = int(red.get('scc:1:id'))
            scc_id_2 = int(red.get('scc:2:id'))
        except Exception as e:
            scc_id_1 = 1
            scc_id_2 = 2
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': site_name,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.3.4',
            'scc_ids': {1: scc_id_1, 2: scc_id_2},
            'number_of_scc': number_of_scc,
            'scc_type': data.get('device_version').get('scc_type'),
            'scc_source': data.get('device_version').get('scc_source'),
            'host': data.get(f'{scc_type_underscore}').get('host'),
            'port': data.get(f'{scc_type_underscore}').get('port'),
            'scc_scan': data.get(f'{scc_type_underscore}').get('scan'),
            'config_scc': data.get(f'{scc_type_underscore}').get('parameter'),
            'config_relay': data.get('handle_relay'),
        }
    if number_of_scc == 3:
        try:
            scc_id_1 = int(red.get('scc:1:id'))
            scc_id_2 = int(red.get('scc:2:id'))
            scc_id_3 = int(red.get('scc:3:id'))
        except Exception as e:
            scc_id_1 = 1
            scc_id_2 = 2
            scc_id_3 = 3
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': site_name,
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.3.4',
            'scc_ids': {1: scc_id_1, 2: scc_id_2, 3: scc_id_3},
            'number_of_scc': number_of_scc,
            'scc_type': data.get('device_version').get('scc_type'),
            'scc_source': data.get('device_version').get('scc_source'),
            'host': data.get(f'{scc_type_underscore}').get('host'),
            'port': data.get(f'{scc_type_underscore}').get('port'),
            'scc_scan': data.get(f'{scc_type_underscore}').get('scan'),
            'config_scc': data.get(f'{scc_type_underscore}').get('parameter'),
            'config_relay': data.get('handle_relay'),
        }
    return render_template('setting-scc.html', **context)

@app.route('/api/scc-rules/<scc_type>', methods=['GET'])
@login_required
def get_scc_rules(scc_type):
    """API endpoint to get SCC configuration rules as markdown HTML"""
    try:
        # Validate SCC type
        if scc_type not in ['scc-srne', 'scc-epveper']:
            return jsonify({'error': 'Invalid SCC type'}), 400
        
        # Build file path
        rules_file = f'dist/rules-{scc_type}.md'
        
        # Check if file exists
        if not os.path.exists(rules_file):
            return jsonify({'error': 'Rules file not found'}), 404
        
        # Read the markdown file
        with open(rules_file, 'r', encoding='utf-8') as file:
            markdown_content = file.read()
        
        # Convert markdown to HTML with extensions
        md = markdown.Markdown(extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br'
        ])
        
        html_content = md.convert(markdown_content)
        
        response_data = {
            'scc_type': scc_type,
            'title': f'Configuration Rules for {scc_type.replace("-", " ").title()}',
            'content': html_content,
            'raw_content': markdown_content,
            'format': 'markdown'
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"get_scc_rules() error: {e}")
        return jsonify({'error': 'Failed to load rules'}), 500

@app.route('/setting-mqtt', methods=['GET', 'POST'])
@login_required
def setting_mqtt():
    # Check page access permission
    username = current_user.id
    if not can_access_page(username, 'mqtt_settings'):
        audit_access(username, 'mqtt_settings', 'access_denied')
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    
    site_name = ""

    # path config device
    path = f'{PATH}/config_device.json'

    form_setting_mqtt = request.form.get('setting-mqtt-form')

    if request.method == 'POST':
        data = request.form.to_dict()

        if form_setting_mqtt:
            response = update_setting_mqtt(path, data)            
            if response:
                flash('MQTT Settings have been updated successfully', 'success')
                audit_access(username, 'mqtt_settings', 'update_mqtt_settings')
                os.system(f'sudo python3 {PATH}/config_scc.py')
                bash_command('sudo systemctl restart mqtt_publish.service device_config_loader.service webapp.service')
            else:
                flash('Failed to update MQTT Settings', 'danger')
            return redirect(url_for('setting_mqtt'))
    
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        with open(path, 'r') as file:
            data = json.load(file)

        # get site name
        site_name = red.hget('device_config', 'site_name')

        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'scc_type': scc_type,
            'mqtt_config': data.get('mqtt_config'),
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
        }
        
        # Audit page access
        audit_access(username, 'mqtt_settings', 'view')
        
    except Exception as e:
        print(f"setting_mqtt() error: {e}")
        
        try:
            with open(path, 'r') as file:
                data = json.load(file)
        except:
            data = {'mqtt_config': {}}

        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'scc_type': scc_type,
            'mqtt_config': data.get('mqtt_config', {}),
            'ip_address': get_ip_address('eth0'),
            # 'ip_address': '192.168.1.1',
        }
    return render_template('setting-mqtt.html', **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if user is locked
        if is_user_locked(username):
            flash('Account is temporarily locked due to too many failed attempts. Please try again later.', 'error')
            return render_template('login.html')
        
        # Verify credentials using the secure authentication system
        if verify_password(username, password):
            user = User(username)
            login_user(user, remember=False)  # Change to remember=False to avoid persistent sessions
            session['username'] = username
            session.permanent = False  # Make session non-permanent for security
            
            # Get role-based API token from environment variables
            from auths import get_user_api_token
            api_token = get_user_api_token(username)
            if api_token:
                session['auth_token'] = api_token
            else:
                flash('API token not found for your role. Please contact administrator.', 'error')
                return redirect(url_for('login'))
            
            # Audit successful login
            audit_access(username, 'login', 'successful_login')
            
            # Get user role for logging
            user_role = get_user_role(username)
            flash(f'Welcome {username.capitalize()}! You are logged in as {user_role}.', 'success')
            
            # Handle potential 'next' parameter for redirect after login
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            return redirect(url_for('index'))
        else:
            # Record failed attempt (already handled in verify_password)
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/update-rectifier-config', methods=['POST'])
@login_required
def update_rectifier_config():
    """Update rectifier configuration"""
    try:
        # Check user permissions
        username = current_user.id
        if not can_access_page(username, 'rectifier'):
            audit_access(username, 'rectifier', 'access_denied_config_update')
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        host = data.get('host')
        port = data.get('port')
        
        if not host:
            return jsonify({
                'success': False,
                'error': 'Host is required'
            }), 400
        
        if not port or not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({
                'success': False,
                'error': 'Valid port number (1-65535) is required'
            }), 400
        
        # Load current configuration
        config_path = f'{PATH}/config_device.json'
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'error': 'Configuration file not found'
            }), 500
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': 'Invalid configuration file format'
            }), 500
        
        # Update rectifier configuration
        if 'rectifier_config' not in config_data:
            config_data['rectifier_config'] = {}
        
        config_data['rectifier_config']['host'] = host
        config_data['rectifier_config']['port'] = port
        
        # Save updated configuration
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to save configuration: {str(e)}'
            }), 500
        
        # Audit the configuration change
        audit_access(username, 'rectifier', 'update_rectifier_config', f'Host: {host}, Port: {port}')
        
        return jsonify({
            'success': True,
            'message': 'Rectifier configuration updated successfully',
            'data': {
                'host': host,
                'port': port
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/logout')
def logout():
    # Clear user session completely (no need to revoke static API tokens)
    logout_user()
    session.clear()
    
    # Clear any Flask-Login remember me cookies
    response = make_response(redirect(url_for('login')))
    response.set_cookie('remember_token', '', expires=0)
    response.set_cookie('session', '', expires=0)
    
    flash('Berhasil Logout', 'success')
    return response


# Route untuk clear session secara manual (untuk debugging)
@app.route('/clear-session')
def clear_session():
    logout_user()
    session.clear()
    flash('Session cleared successfully', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    # Clear any existing sessions on startup
    print("🔐 Starting JSPro PowerDesk Application...")
    print("🧹 Clearing any existing sessions...")
    
    # Run the Flask application
    print("🚀 Server starting on http://127.0.0.1:5000")
    print("📝 Note: First access should redirect to login page")
    app.run(debug=True, host='127.0.0.1', port=5000)
