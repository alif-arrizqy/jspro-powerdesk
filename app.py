import os
import json
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from config import *
from functions import *
from api.core import register_blueprints, register_error_handlers
from api.redisconnection import connection as red
from auths import USERS, verify_password, record_successful_login, record_failed_attempt, is_user_locked, get_user_role, audit_access, get_menu_access, can_access_page
from validations import validate_setting_ip, validate_modbus_id
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# app.secret_key = '7yBkBOPs92u9HZQeyqlmyNVKv8_RTd3hQoziImBnsME'
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

# PATH = "/var/lib/sundaya/ehub-talis"
PATH = "D:/sundaya/developments/ehub-developments/ehub_talis/ehub-talis"

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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_battery': number_of_batt,
            'number_of_cell': number_of_cell
        }
    return render_template('battery.html', **context)


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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.4.44'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.4.3'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'mqtt_config': data.get('mqtt_config', {})
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'mqtt_config': data.get('mqtt_config', {})
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
        }
    return render_template('systemd-service.html', **context)

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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
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
            # 'ip_address': get_ip_address('eth0'),
            # 'ip_address_primary': get_ip_address('eth0'),
            # 'ip_address_secondary': get_ip_address('eth1'),
            # 'subnet_mask': f'/{get_subnet_mask('eth0')}',
            # 'gateway': get_gateway('eth0'),
            'ip_address': '192.168.1.1',
            'ip_address_primary': '192.168.1.1',
            'ip_address_secondary': '192.168.1.2',
            'subnet_mask': '/29',
            'gateway': '192.168.1.1'
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
            # 'ip_address': get_ip_address('eth0'),
            # 'ip_address_primary': get_ip_address('eth0'),
            # 'ip_address_secondary': get_ip_address('eth1'),
            # 'subnet_mask': f'/{get_subnet_mask('eth0')}',
            # 'gateway': get_gateway('eth0'),
            'ip_address': '192.168.1.1',
            'ip_address_primary': '192.168.1.1',
            'ip_address_secondary': '192.168.1.2',
            'subnet_mask': '/29',
            'gateway': '192.168.1.1'
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
    
    form_site_location = request.form.get('site-location-form')
    form_device_model = request.form.get('device-info-form')

    if request.method == 'POST':
        data = request.form.to_dict()
        
        if form_site_location:
            response = update_site_location(path, data)
            # add site name to redis
            red.hset('site_name', 'site_name', data.get('site-name'))
            
            if response:
                flash('Site Location has been updated successfully', 'success')
                audit_access(username, 'device_settings', 'update_site_location')
            else:
                flash('Failed to update Site Location', 'danger')
            return redirect(url_for('setting_device'))
        
        if form_device_model:
            response = update_device_model(path, data)
            if response:
                flash('Device Info has been updated successfully', 'success')
                audit_access(username, 'device_settings', 'update_device_model')
            else:
                flash('Failed to update Device Info', 'danger')
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
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
    
    if request.method == 'POST':
        path = './commands/change_ip.py'
        
        data = request.form.to_dict()        
        is_valid = validate_setting_ip(request.form)
        if is_valid:
            type_ip_address = data.get('type-ip-address')
            ip_address_primary = data.get('ip-address-primary')
            ip_address_secondary = data.get('ip-address-secondary')
            subnet_mask = data.get('net-mask')
            gateway = data.get('gateway')
            
            if type_ip_address == 'ip-primary':
                status = change_ip(path, ip_address_primary, gateway, subnet_mask)
            if type_ip_address == 'ip-secondary':
                status = change_ip(path, ip_address_secondary, gateway, subnet_mask)
            
            if status:
                flash('IP Address has been changed successfully', 'success')
                audit_access(username, 'ip_configuration', 'update_ip_settings')
            else:
                flash('Failed to change IP Address', 'danger')
            return redirect(url_for('setting_ip'))
        else:
            flash('Invalid IP Address', 'danger')
            return redirect(url_for('setting_ip'))
    try:
        # Get user role and menu access
        user_role = get_user_role(username)
        menu_access = get_menu_access(username)
        
        # get site name
        site_name = red.hget('device_config', 'site_name')
        
        # open data site
        with open('./data_site.json', 'r') as f:
            data_ip = json.load(f)
        
        context = {
            'username': username,
            'user_role': user_role,
            'menu_access': menu_access,
            'site_name': site_name,
            'data_ip': data_ip,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            # 'ip_address_primary': get_ip_address('eth0'),
            # 'ip_address_secondary': get_ip_address('eth1'),
            # 'subnet_mask': f'/{get_subnet_mask('eth0')}',
            # 'gateway': get_gateway('eth0'),
            'ip_address': '192.168.1.1',
            'ip_address_primary': '192.168.1.1',
            'ip_address_secondary': '192.168.1.2',
            'subnet_mask': '/29',
            'gateway': '192.168.1.1'
        }
        
        # Audit page access
        audit_access(username, 'ip_configuration', 'view')
        
    except Exception as e:
        print(f"setting_ip() error: {e}")
        
        context = {
            'username': username,
            'user_role': get_user_role(username),
            'menu_access': get_menu_access(username),
            'site_name': 'Site Name',
            'data_ip': data_ip,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            # 'ip_address_primary': get_ip_address('eth0'),
            # 'ip_address_secondary': get_ip_address('eth1'),
            # 'subnet_mask': f'/{get_subnet_mask('eth0')}',
            # 'gateway': get_gateway('eth0'),
            'ip_address': '192.168.1.1',
            'ip_address_primary': '192.168.1.1',
            'ip_address_secondary': '192.168.1.2',
            'subnet_mask': '/29',
            'gateway': '192.168.1.1'
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
                bash_command('sudo systemctl restart scc device_config_loader.service webapp.service')
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
                bash_command('sudo systemctl restart scc device_config_loader.service webapp.service')
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
                bash_command('sudo systemctl restart scc')
            else:
                flash('Failed to update Config Value Cut off / Reconnect', 'danger')
            return redirect(url_for('setting_scc'))
            
        if config_scc_form == 'config-scc-form':
            response = update_config_scc(path, form_data)
            if response:
                flash('Config Value SCC has been updated successfully', 'success')
                audit_access(username, 'scc_settings', 'update_scc_config')
                os.system(f'sudo python3 {PATH}/config_scc.py')
                bash_command('sudo systemctl restart scc')
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4',
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
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4',
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


@app.route('/login', methods=['GET', 'POST'])
def login():
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
            login_user(user)
            session['username'] = username
            
            # Audit successful login
            audit_access(username, 'login', 'successful_login')
            
            # Get user role for logging
            user_role = get_user_role(username)
            flash(f'Welcome {username.capitalize()}! You are logged in as {user_role}.', 'success')
            
            return redirect(url_for('index'))
        else:
            # Record failed attempt (already handled in verify_password)
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash('Berhasil Logout', 'success')
    return redirect(url_for('login'))
