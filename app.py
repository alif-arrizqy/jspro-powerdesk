import os
import json
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from config import *
from functions import *
from api import core
from api.redisconnection import connection as red
from auths import users
from validations import validate_setting_ip, validate_modbus_id

app = Flask(__name__)
app.secret_key = '83dcdc455025cedcfe64b21e620564fb'
app.register_blueprint(core.api)

cors = CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

# PATH = "/var/lib/sundaya/ehub-talis"
PATH = "E:/sundaya/developments/EhubTalis/ehub-talis"

@login_manager.user_loader
def load_user(username):
    if username in users:
        return User(username)
    return None

@app.route('/', methods=['GET'])
# @login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    site_name = ""
    username = ""
    try:
        # get current username
        username = current_user.id
        
        # get site name
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
        }
    except Exception as e:
        print(f"index() error: {e}")
        context = {
            'username': username,
            'site_name': 'Sitea Name',
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
        }
    return render_template('index.html', **context)


@app.route('/scc', methods=['GET'])
@login_required
def scc():
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc
        }
    except Exception as e:
        print(f"scc() error: {e}")
        context = {
            'username': username,
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
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
            'number_of_battery': number_of_batt,
            'number_of_cell': number_of_cell
        }
    except Exception as e:
        print(f"battery() error: {e}")
        context = {
            'username': username,
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
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.4.44'
        }
    except Exception as e:
        print(f"datalog() error: {e}")
        context = {
            'username': username,
            'site_name': 'Site Name',
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.4.3'
        }
    return render_template('datalog.html', **context)


@app.route('/scc-alarm-log', methods=['GET'])
@login_required
def scc_alarm_log():
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4'
        }
    except Exception as e:
        print(f"scc_alarm_log() error: {e}")
        context = {
            'username': username,
            'site_name': 'Site Name',
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4'
        }
    return render_template('scc-alarm-log.html', **context)

@app.route('/power-operation', methods=['GET'])
@login_required
def power_operation():
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        site_name = red.hget('site_name', 'site_name')
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
        }
    except Exception as e:
        print(f"power_operation() error: {e}")
        context = {
            'username': username,
            'site_name': 'Site Name',
            'scc_type': scc_type,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1'
        }
    return render_template('power-operation.html', **context)


@app.route('/site-information', methods=['GET'])
@login_required
def site_information():
    site_name = ""
    path = f'{PATH}/config_device.json'
    try:
        # username login
        username = current_user.id
        
        with open(path, 'r') as file:
            data = json.load(file)
        
        # get site name
        site_name = red.hget('site_name', 'site_name')
        
        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            'site_location': data.get('site_location'),
            'device_info': data.get('device_model'),
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
    except Exception as e:
        print(f"site_information() error: {e}")
        
        with open(path, 'r') as file:
            data = json.load(file)
        
        context = {
            'username': username,
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
    site_name = ""
    # username login
    username = current_user.id

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
            else:
                flash('Failed to update Site Location', 'danger')
            return redirect(url_for('setting_device'))
        
        if form_device_model:
            response = update_device_model(path, data)
            if response:
                flash('Device Info has been updated successfully', 'success')
            else:
                flash('Failed to update Device Info', 'danger')
            return redirect(url_for('setting_device'))
    
    try:
        with open(path, 'r') as file:
            data = json.load(file)

        # get site name
        site_name = red.hget('site_name', 'site_name')

        context = {
            'username': username,
            'site_name': site_name,
            'scc_type': scc_type,
            'site_information': data.get('site_information'),
            'device_model': data.get('device_model'),
            'device_version': data.get('device_version'),
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.1.1',
        }
    except Exception as e:
        print(f"setting_device() error: {e}")
        
        with open(path, 'r') as file:
            data = json.load(file)

        context = {
            'username': username,
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
    site_name = ""
    # username login
    username = current_user.id
    
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
            else:
                flash('Failed to change IP Address', 'danger')
            return redirect(url_for('setting_ip'))
        else:
            flash('Invalid IP Address', 'danger')
            return redirect(url_for('setting_ip'))
    try:
        # get site name
        site_name = red.hget('site_name', 'site_name')
        
        # open data site
        with open('./data_site.json', 'r') as f:
            data_ip = json.load(f)
        
        context = {
            'username': username,
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
    except Exception as e:
        print(f"setting_ip() error: {e}")
        
        context = {
            'username': username,
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
    site_name = ""
    # username login
    username = current_user.id
    
    # path config device
    path = f'{PATH}/config_device.json'
    
    # open config device
    with open(path, 'r') as file:
        data = json.load(file)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        scc_type_form = request.form.get('scc-type-form')
        scc_setting_id_form = request.form.get('scc-setting-id-form')
        
        if scc_type_form == 'scc-type-form':
            response = update_scc_type(path, data)
            if response:
                flash('SCC Type has been updated successfully', 'success')
                bash_command('sudo systemctl restart mppt device_version.service webapp.service')
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
                bash_command('sudo systemctl restart mppt device_version.service webapp.service')
                bash_command('sudo systemctl daemon-reload')
                flash('SCC ID has been updated successfully', 'success')
            else:
                flash('Failed to update SCC ID', 'danger')
            return redirect(url_for('setting_scc'))
    try:
        # get site name
        site_name = red.hget('site_name', 'site_name')
    except Exception as e:
        print(f"setting_scc() error: {e}")
        site_name = 'Site Name'
    
    # get scc type
    scc_type = data.get('device_version').get('scc_type')
    # replace - to _
    scc_type = scc_type.replace('-', '_')
    
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
            'site_name': site_name,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4',
            'scc_ids': {1: scc_id_1, 2: scc_id_2},
            'number_of_scc': number_of_scc,
            'scc_type': data.get('device_version').get('scc_type'),
            'scc_source': data.get('device_version').get('scc_source'),
            'host': data.get(f'{scc_type}').get('host'),
            'port': data.get(f'{scc_type}').get('port'),
            'scc_scan': data.get(f'{scc_type}').get('scan'),
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
            'site_name': site_name,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.3.4',
            'scc_ids': {1: scc_id_1, 2: scc_id_2, 3: scc_id_3},
            'number_of_scc': number_of_scc,
            'scc_type': data.get('device_version').get('scc_type'),
            'scc_source': data.get('device_version').get('scc_source'),
            'host': data.get(f'{scc_type}').get('host'),
            'port': data.get(f'{scc_type}').get('port'),
            'scc_scan': data.get(f'{scc_type}').get('scan'),
        }
    return render_template('setting-scc.html', **context)

@app.route('/config-value-scc', methods=['GET', 'POST'])
@login_required
def config_value_scc():
    site_name = ""
    # username login
    username = current_user.id

    # path config device
    path = f'{PATH}/config_device.json'

    # open config device
    with open(path, 'r') as file:
        data = json.load(file)

    if request.method == 'POST':
        data = request.form.to_dict()
        config_relay = data.get('config-relay-form')
        config_scc = data.get('config-scc-form')
        
        if config_relay == 'config-relay-form':
            response = update_config_cutoff_reconnect(path, data)
            if response:
                flash('Config Value Cut off / Reconnect has been updated successfully', 'success')
                os.system(f'sudo python3 {PATH}/config_mppt.py')
                bash_command('sudo systemctl restart mppt')
            else:
                flash('Failed to update Config Value Cut off / Reconnect', 'danger')
            return redirect(url_for('config_value_scc'))
        if config_scc == 'config-scc-form':
            response = update_config_scc(path, data)
            if response:
                flash('Config Value SCC has been updated successfully', 'success')
                os.system(f'sudo python3 {PATH}/config_mppt.py')
                bash_command('sudo systemctl restart mppt')
            else:
                flash('Failed to update Config Value SCC', 'danger')
            return redirect(url_for('config_value_scc'))
    try:
        # get site name
        site_name = red.hget('site_name', 'site_name')
    except Exception as e:
        print(f"config_value_scc() error: {e}")
        site_name = 'Site Name'
    
    # get scc type
    scc_type = data.get('device_version').get('scc_type')
    # replace - to _
    scc_type = scc_type.replace('-', '_')
    
    context = {
        'username': username,
        'site_name': site_name,
        # 'ip_address': get_ip_address('eth0'),
        'ip_address': '192.168.3.4',
        'scc_type': scc_type,
        'config_scc': data.get(f'{scc_type}').get('parameter'),
        'config_relay': data.get('handle_relay'),
    }
    
    return render_template('config-value-scc.html', **context)

@app.route('/disk-storage', methods=['GET'])
@login_required
def disk_storage():
    site_name = ""
    try:
        # username login
        username = current_user.id
        
        # get site name
        site_name = red.hget('site_name', 'site_name')
        
        context = {
            'username': username,
            'site_name': site_name,
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.34.1'
        }
    except Exception as e:
        print(f"disk_storage() error: {e}")
        context = {
            'username': username,
            'site_name': 'Site Name',
            # 'ip_address': get_ip_address('eth0'),
            'ip_address': '192.168.34.3'
        }
    return render_template('disk-storage.html', **context)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and password == users[username]['password']:
            user = User(username)
            login_user(user)
            session['username'] = username
            flash('Kamu Telah Login Sebagai', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash('Berhasil Logout', 'success')
    return redirect(url_for('login'))
