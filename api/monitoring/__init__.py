from flask import Blueprint

monitoring_bp = Blueprint('monitoring', __name__)

from . import api_monitoring
