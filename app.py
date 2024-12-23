import os
import json
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for
from config import *
from api import core
from api.redisconnection import red
from auths import basic_auth as auth
from functions import change_ip, bash_command, get_ip_address, update_config_mppt, update_device_version
# from validations import validate_setting_ip, validate_modbus_id
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app)
app.secret_key = '83dcdc455025cedcfe64b21e620564fb'
app.register_blueprint(core.api)
PATH = "/var/lib/sundaya/ehub-bakti"


@app.route('/', methods=['GET'])
def index():
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            'site_name': site_name,
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
        }
    except Exception as e:
        context = {
            'site_name': 'Ehub Talis',
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'number_of_scc': number_of_scc
        }
    return render_template('index.html', **context)


@app.route('/scc', methods=['GET'])
def scc():
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            'site_name': site_name,
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc
        }
    except Exception as e:
        context = {
            'site_name': 'Ehub Talis',
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'scc_type': scc_type,
            'number_of_scc': number_of_scc
        }
    return render_template('scc.html', **context)


@app.route('/battery', methods=['GET'])
def battery():
    try:
        if red.get('site_name') is not None:
            site_name = str(red.get('site_name'))[2:-1]
        context = {
            'site_name': site_name,
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'number_of_battery': number_of_batt
        }
    except Exception as e:
        context = {
            'site_name': 'Ehub Talis',
            # 'ip_address': get_ip_address(),
            'ip_address': '192.168.1.1',
            'number_of_battery': number_of_batt
        }
    return render_template('battery.html', **context)


@app.route('/datalog', methods=['GET'])
def datalog():
    return render_template('datalog.html')


@app.route('/scc-alarm-log', methods=['GET'])
def scc_alarm_log():
    return render_template('scc-alarm-log.html')


@app.route('/site-information', methods=['GET'])
def site_information():
    return render_template('site-information.html')


@app.route('/setting-device', methods=['GET'])
def setting_device():
    return render_template('setting-device.html')


@app.route('/setting-scc', methods=['GET'])
def setting_scc():
    return render_template('setting-scc.html')


@app.route('/config-value-scc', methods=['GET'])
def config_value_scc():
    return render_template('config-value-scc.html')


@app.route('/disk-storage', methods=['GET'])
def disk_storage():
    return render_template('disk-storage.html')
