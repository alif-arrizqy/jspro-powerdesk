from flask import Blueprint

service_bp = Blueprint('service', __name__)

from . import api_mqtt
from . import api_snmp
from . import api_snmp_rectifier
from . import api_systemd