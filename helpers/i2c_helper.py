from smbus2 import SMBus
import json
import os

def send_i2c_message(address, message):
    bus = SMBus(1)
    try:
        bus.write_byte(address, message)
        return True
    except OSError:
        return False


def send_i2c_heartbeat(address=0x28, message=ord('H')):
    """Send I2C heartbeat with logging"""
    import json
    from datetime import datetime
    
    bus = SMBus(1)
    timestamp = datetime.now().isoformat()
    
    try:
        bus.write_byte(address, message)
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
    
    settings_file = '/var/lib/sundaya/jspro-powerdesk/dist/i2c_settings.json'
    
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
    
    settings_file = '/var/lib/sundaya/jspro-powerdesk/dist/i2c_settings.json'
    settings['last_modified'] = datetime.now().isoformat()
    
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Set appropriate permissions if possible
        try:
            os.chmod(settings_file, 0o644)
        except (PermissionError, OSError):
            pass  # Ignore permission errors
            
        print(f"I2C settings saved to: {settings_file}")
        return True
        
    except Exception as e:
        print(f"Error saving I2C settings: {e}")
        print(f"Attempted to save to: {settings_file}")
        return False


def validate_i2c_settings(settings):
    """Validate I2C settings structure and values"""
    required_fields = ['enabled', 'interval_minutes', 'i2c_address', 'message']
    
    # Check required fields
    for field in required_fields:
        if field not in settings:
            return False, f"Missing required field: {field}"
    
    # Validate data types and ranges
    try:
        # enabled should be boolean
        if not isinstance(settings['enabled'], bool):
            return False, "enabled must be boolean"
        
        # interval_minutes should be integer between 1-60
        interval = int(settings['interval_minutes'])
        if interval < 1 or interval > 60:
            return False, "interval_minutes must be between 1-60"
        
        # i2c_address should be valid hex address
        address = settings['i2c_address']
        if isinstance(address, str):
            if address.startswith('0x'):
                int(address, 16)
            else:
                int(address)
        
        # message should be single character
        message = settings['message']
        if not isinstance(message, str) or len(message) != 1:
            return False, "message must be a single character"
        
        return True, "Settings are valid"
        
    except ValueError as e:
        return False, f"Invalid value: {e}"


def get_i2c_settings_info():
    """Get information about I2C settings location and status"""
    settings_file = '/var/lib/sundaya/jspro-powerdesk/dist/i2c_settings.json'
    
    info = {
        'settings_directory': '/var/lib/sundaya/jspro-powerdesk/dist',
        'settings_file': str(settings_file),
        'file_exists': settings_file.exists(),
        'directory_writable': os.access('/var/lib/sundaya/jspro-powerdesk/dist', os.W_OK),
        'file_readable': settings_file.exists() and os.access(settings_file, os.R_OK),
        'file_writable': settings_file.exists() and os.access(settings_file, os.W_OK)
    }
    
    if settings_file.exists():
        try:
            stat = settings_file.stat()
            info['file_size'] = stat.st_size
            info['last_modified'] = stat.st_mtime
        except OSError:
            pass
    
    return info


def reset_i2c_settings():
    """Reset I2C settings to default values"""
    default_settings = {
        'enabled': True,
        'interval_minutes': 2,
        'i2c_address': '0x28',
        'message': 'H',
        'last_modified': None,
        'modified_by': 'system_reset'
    }
    
    return save_i2c_settings(default_settings)
