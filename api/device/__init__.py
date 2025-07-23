from flask import Blueprint

device_bp = Blueprint('device', __name__)

from . import api_device
