from flask import Blueprint

power_bp = Blueprint('power', __name__)

from . import api_power