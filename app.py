import os
import json
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for
from config import *
from api import core
from api.redisconnection import red
from auths import basic_auth as auth
from functions import change_ip, bash_command, get_ip_address, update_config_mppt, update_device_version
from validations import validate_setting_ip, validate_modbus_id
from flask_cors import CORS

app = Flask(__name__)
cors =CORS(app)
app.secret_key = '83dcdc455025cedcfe64b21e620564fb'
app.register_blueprint(core.api)
PATH = "/var/lib/sundaya/ehub-bakti"

@app.route('/', methods=('GET', 'POST',))
def index():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            "num_of_mppt": number_of_mppt,
            "num_of_batt": number_of_batt,
            "slave_ids": slave_ids,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            "num_of_mppt": number_of_mppt,
            "num_of_batt": number_of_batt,
            "slave_ids": slave_ids,
        }
    if request.method == "POST":
        red.set('site_name', request.form.get('site_name'))
        return redirect(url_for('index'))
    return render_template('dashboard.html', **context)

@app.route('/mppt/')
def mppt():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context= {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_mppt': number_of_mppt,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_mppt': number_of_mppt,
        }
    return render_template('mppt.html', **context)

@app.route('/load')
def load():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context= {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
        }
    return render_template('load.html', **context)

@app.route('/loggers/')
def loggers():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
        }
    except Exception:
        context= {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
        }
    return render_template('loggers.html', **context)

@app.route('/mppt-alarm')
def mppt_alarm():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_mppt': number_of_mppt,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_mppt': number_of_mppt,
        }
    return render_template('mppt-alarm.html', **context)

@app.route('/pms/')
def pms():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_batt': number_of_batt,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'num_of_batt': number_of_batt,
        }
    return render_template('pms.html', **context)

@app.route('/talis/')
def talis():
    site_name = ""
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'slave_ids': slave_ids,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'slave_ids': slave_ids,
        }
    return render_template('talis.html', **context)

@app.route('/setting-ip', methods=('GET','POST'))
@auth.login_required
def setting_ip():
    site_name = ""
    ip_address = ""
    subnet_mask = ""
    gateway = ""
    
    # read json
    with open('./data_site.json', 'r') as f:
        data_site = json.load(f)
    
    # check setting ip
    ipaddr = get_ip_address('eth0')
    for i in data_site:
        if i['ip'] == ipaddr:
            ip_address = i['ip']
            subnet_mask = i['subnet_mask']
            gateway = i['gateway']
    
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1].replace(' ', '_')

        context = {
            "site_name": site_name,
            "data": data_site,
            "ip_address": ip_address,
            "subnet_mask": subnet_mask,
            "gateway": gateway,
        }
    except Exception:
        context = {
            "site_name": site_name,
            "data": data_site,
            "ip_address": ip_address,
            "subnet_mask": subnet_mask,
            "gateway": gateway,
        }
    
    if request.method == 'POST':
        file_path = '/var/lib/sundaya/joulestore-web-app/commands/change_ip.py'
        form_is_valid, msg = validate_setting_ip(request.form)
        if form_is_valid:
            ip_address = request.form.get('ip_address')
            subnet_mask = request.form.get('subnet_mask')
            gateway = request.form.get('gateway')
            if request.form.get('site') != 'IP CUSTOM':
                red.set('site_name', request.form.get('site'))

            status = change_ip(file_path, ip_address, gateway, subnet_mask)
            flash(status, category='green')
            return redirect(url_for('setting_ip'))
        else:
            flash(msg, category='red')
            return redirect(url_for('setting_ip'))
    return render_template('setting-ip.html', **context)

@app.route('/device-version', methods=('GET', 'POST'))
@auth.login_required
def device_version():
    site_name = ""
    if red.get('site_name') is not None:
        site_name = str(red.get('site_name'))[2:-1]
    
    if request.method == 'POST':
        path = f'{PATH}/config_device.json'
        is_valid = update_device_version(path, request.form)
        if is_valid:
            flash('Update device type success', category='green')
            if request.form.get('mppt_type') == 'mppt-srne':
                os.system('sudo python3 /var/lib/sundaya/ehub-bakti/device_version.py')
                os.system('sudo systemctl restart webapp mppt device_version.service')
            elif request.form.get('mppt_type') == 'mppt-epveper':
                os.system('sudo python3 /var/lib/sundaya/ehub-bakti/device_version.py')
                os.system('sudo systemctl restart webapp mppt device_version.service')
            return redirect(url_for('device_version'))
        else:
            flash('Update device type failed, cek lagi input datanya', category='red')
            return redirect(url_for('device_version'))
    else:
        path = f'{PATH}/config_device.json'
        # read json file
        with open(path, 'r') as f:
            data = json.load(f)
        context = {
            'site_name': site_name,
            "ip_address": get_ip_address('eth0'),
            'config_device': data.get('device_version'),
            'num_of_mppt': number_of_mppt,
        }
        return render_template('device_version.html', **context)

@app.route('/config-mppt', methods=('GET', 'POST'))
@auth.login_required
def mppt_config():
    site_name = ""
    if red.get('site_name') is not None:
        site_name = str(red.get('site_name'))[2:-1]
    
    if request.method == 'POST':
        path = f'{PATH}/config_device.json'
        is_valid = update_config_mppt(path, request.form)
        if is_valid:
            flash('Update config mppt success', category='green')
            os.system('sudo python3 /var/lib/sundaya/ehub-bakti/config_mppt.py')
            if request.form.get('port') == '/dev/ttyS0' or request.form.get('port') == '/dev/ttyUSB0':
                os.system('sudo systemctl restart mppt')
        else:
            flash('Update config mppt failed, please check parameter handle relay', category='red')
        return redirect(url_for('mppt_config'))
    else:
        # read config mppt
        path = f'{PATH}/config_device.json'
        # read json file
        with open(path, 'r') as f:
            data = json.load(f)
        context = {
            'site_name': site_name,
            "ip_address": get_ip_address('eth0'),
            'config_mppt': data,
            'num_of_mppt': number_of_mppt,
        }
        return render_template('config-mppt.html', **context)

@app.route('/setting-mppt', methods=('GET', 'POST'))
@auth.login_required
def setting_mppt():
    site_name = ""
    if red.get('site_name') is not None:
        site_name = str(red.get('site_name'))[2:-1]

    if request.method == 'POST':
        is_valid, msg = validate_modbus_id(request.form)
        if is_valid:
            if number_of_mppt == 3:
                red.set('mppt:1:id', request.form.get('mppt1_id'))
                red.set('mppt:2:id', request.form.get('mppt2_id'))
                red.set('mppt:3:id', request.form.get('mppt3_id'))
            if number_of_mppt == 2:
                red.set('mppt:1:id', request.form.get('mppt1_id'))
                red.set('mppt:2:id', request.form.get('mppt2_id'))
            bash_command('sudo systemctl daemon-reload')
            bash_command('sudo systemctl restart mppt')
            bash_command('sudo systemctl restart store_log_data')
            flash(msg, category='green')
        else:
            flash(msg, category='red')

    if number_of_mppt == 3:
        try: 
            mppt1_id = int(red.get('mppt:1:id'))
            mppt2_id = int(red.get('mppt:2:id'))
            mppt3_id = int(red.get('mppt:3:id'))
        except TypeError:
            mppt1_id = 1
            mppt2_id = 2
            mppt3_id = 3
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'mppts_id' : {1:mppt1_id,2:mppt2_id,3:mppt3_id},
            'num_of_mppt': number_of_mppt
        }
    
    if number_of_mppt == 2:
        try:
            mppt1_id = int(red.get('mppt:1:id'))
            mppt2_id = int(red.get('mppt:2:id'))
        except TypeError:
            mppt1_id = 2
            mppt2_id = 1
        context = {
            "site_name": site_name,
            "ip_address": get_ip_address('eth0'),
            'mppts_id' : {1:mppt1_id,2:mppt2_id},
            'num_of_mppt': number_of_mppt
        }
    
    return render_template('setting-mppt.html', **context)
