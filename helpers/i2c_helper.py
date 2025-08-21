# from smbus2 import SMBus
import json

# i2c 
def send_i2c_message(address, message):
    # bus = SMBus(1)
    try:
        # bus.write_byte(address, message)
        return True
    except OSError:
        return False


def send_i2c_heartbeat(address=0x28, message=ord('H')):
    """Send I2C heartbeat with logging"""
    import json
    from datetime import datetime
    
    # bus = SMBus(1)
    timestamp = datetime.now().isoformat()
    
    try:
        # bus.write_byte(address, message)
        result = {
            'success': True,
            'timestamp': timestamp,
            'address': hex(address),
            'message': chr(message),
            'error': None
        }
        # Log successful communication
        log_i2c_communication(result)
        return result
    except OSError as e:
        result = {
            'success': False,
            'timestamp': timestamp,
            'address': hex(address),
            'message': chr(message),
            'error': str(e)
        }
        # Log failed communication
        log_i2c_communication(result)
        return result


def log_i2c_communication(result):
    """Log I2C communication results to file"""
    import json
    from datetime import datetime
    
    log_file = '/var/lib/sundaya/jspro-powerdesk/logs/i2c_communication.log'
    
    try:
        log_entry = {
            'timestamp': result['timestamp'],
            'success': result['success'],
            'address': result['address'],
            'message': result['message'],
            'error': result['error']
        }
        
        # Read existing logs
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []
        
        # Add new log entry
        logs.append(log_entry)
        
        # Keep only last 1000 entries
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        # Write back to file
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging I2C communication: {e}")


def get_i2c_logs(limit=50):
    """Get I2C communication logs"""
    import json
    
    log_file = '/var/lib/sundaya/jspro-powerdesk/logs/i2c_communication.log'
    
    try:
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        # Return latest logs
        return logs[-limit:] if len(logs) > limit else logs
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_i2c_settings():
    """Get I2C monitoring settings"""
    import json
    
    settings_file = 'i2c_settings.json'
    default_settings = {
        'enabled': True,
        'interval_minutes': 2,
        'i2c_address': '0x28',
        'message': 'H',
        'last_modified': None,
        'modified_by': None
    }
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        return settings
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default settings file
        save_i2c_settings(default_settings)
        return default_settings


def save_i2c_settings(settings):
    """Save I2C monitoring settings"""
    import json
    from datetime import datetime
    
    settings_file = 'i2c_settings.json'
    settings['last_modified'] = datetime.now().isoformat()
    
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving I2C settings: {e}")
        return False
