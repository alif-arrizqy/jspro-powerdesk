import psutil
import shutil
from gpiozero import CPUTemperature

# System monitoring
def get_cpu_usage():
    """Get CPU Usage Percentage"""
    return psutil.cpu_percent(interval=2) 


def get_memory_usage():
    """Get memory usage percentage"""
    memory = psutil.virtual_memory()
    return memory.percent


def get_temperature():
    """Get CPU temperature"""
    try:
        cpu_temp = CPUTemperature()
        temperature = round(cpu_temp.temperature, 1)
    except:
        temperature = 25.0
    return temperature


def get_disk_detail():
    disk = shutil.disk_usage('/')
    return disk
