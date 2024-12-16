import os
import json
from flask import Flask, request, render_template, jsonify, Blueprint, session, flash, redirect, url_for
from config import *
from api import core
from api.redisconnection import red
from auths import basic_auth as auth
# from functions import change_ip, bash_command, get_ip_address, update_config_mppt, update_device_version
# from validations import validate_setting_ip, validate_modbus_id
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app)
app.secret_key = '83dcdc455025cedcfe64b21e620564fb'
app.register_blueprint(core.api)
PATH = "/var/lib/sundaya/ehub-bakti"


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/scc', methods=['GET'])
def scc():
    return render_template('scc.html')


@app.route('/battery', methods=['GET'])
def battery():
    return render_template('battery.html')


@app.route('/load', methods=['GET'])
def load():
    return render_template('load.html')


@app.route('/scc-alarm', methods=['GET'])
def scc_alarm():
    return render_template('scc-alarm.html')


@app.route('/datalog', methods=['GET'])
def datalog():
    return render_template('datalog.html')


@app.route('/scc-alarm-log', methods=['GET'])
def scc_alarm_log():
    return render_template('scc-alarm-log.html')


@app.route('/setting-device', methods=['GET'])
def setting_device():
    return render_template('setting-device.html')


@app.route('/setting-scc', methods=['GET'])
def setting_scc():
    return render_template('setting-scc.html')


@app.route('/config-value-scc', methods=['GET'])
def config_value_scc():
    return render_template('config-value-scc.html')


@app.route('/redis', methods=['GET'])
def reset_redis():
    return render_template('redis.html')
