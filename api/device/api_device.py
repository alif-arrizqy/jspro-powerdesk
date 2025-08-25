import json
import platform
import os
import subprocess
from datetime import datetime
from flask import jsonify, request
from . import device_bp
from ..redisconnection import connection as red
from auths import token_auth as auth
from utils import bash_command
from helpers.system_resources_helper import get_cpu_usage, get_memory_usage, get_temperature, get_disk_detail
from redis.exceptions import RedisError

@device_bp.route('/system-resources', methods=['GET'])
@auth.login_required
def get_system_resources():
    """Get system resources including CPU, memory, temperature, and disk usage"""
    try:
        # Get CPU usage
        cpu_usage = get_cpu_usage()
        cpu_dict = {
            "value": float(cpu_usage),
            "unit": "%"
        }

        # Get memory usage
        memory_usage = get_memory_usage()
        memory_dict = {
            "value": float(memory_usage),
            "unit": "%"
        }
        
        # Get temperature using the fixed function
        temperature = get_temperature()
        temperature_dict = {
            "value": round(temperature, 1),
            "unit": "°C"
        }
        
        # Get disk usage
        disk = get_disk_detail()
        disk_usage = {
            "free": round(disk.free / (1024**3), 1),  # Convert to GB
            "used": round(disk.used / (1024**3), 1),  # Convert to GB
            "total": round(disk.total / (1024**3), 1),  # Convert to GB
            "unit": "GB"
        }
        
        response_data = {
            "cpu_usage": cpu_dict,
            "memory_usage": memory_dict,
            "temperature": temperature_dict,
            "disk_usage": disk_usage,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting system resources: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error",
            "data": None
        }), 500


@device_bp.route('/information', methods=['GET'])
@auth.login_required
def get_device_information():
    """Get device information including site information, device version, and device model"""
    try:
        device_data = red.hgetall("device_config")
        if not device_data:
            return jsonify({
                "status_code": 404,
                "message": "Device configuration not found",
                "data": None
            }), 404
        
        # Parse JSON strings to objects
        site_information = {}
        device_version = {}
        device_model = {}
        
        try:
            site_info_str = device_data.get("site_information", "{}")
            if isinstance(site_info_str, str):
                site_information = json.loads(site_info_str)
            else:
                site_information = site_info_str or {}
        except (json.JSONDecodeError, TypeError):
            site_information = {
                "site_id": "PAP9999",
                "site_name": "Site Name",
                "address": "Jl. Bakti No. 1"
            }
        
        try:
            device_version_str = device_data.get("device_version", "{}")
            if isinstance(device_version_str, str):
                device_version = json.loads(device_version_str)
            else:
                device_version = device_version_str or {}
        except (json.JSONDecodeError, TypeError):
            device_version = {
                "ehub_version": "new",
                "panel2_type": "new",
                "site_type": "bakti",
                "scc_type": "scc-epveper",
                "scc_id": [2, 1],
                "scc_source": "serial",
                "battery_type": "talis5"
            }
        
        try:
            device_model_str = device_data.get("device_model", "{}")
            if isinstance(device_model_str, str):
                device_model = json.loads(device_model_str)
            else:
                device_model = device_model_str or {}
        except (json.JSONDecodeError, TypeError):
            device_model = {
                "model": "JSPro MPPT",
                "part_number": "JP-MPPT-40A",
                "serial_number": "SN123456789",
                "software_version": "2.0.0",
                "hardware_version": "2.0.0"
            }
        
        response_data = {
            "site_information": site_information,
            "device_version": device_version,
            "device_model": device_model,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        print(f"Error getting device information: {e}")
        return jsonify({
            "status_code": 500,
            "message": "Internal server error",
            "data": None
        }), 500
