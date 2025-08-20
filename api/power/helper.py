import os
import subprocess
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from functions import bash_command, get_disk_detail


class PowerManagementAPI:
    def __init__(self):
        self.db_path = "auto_reboot.db"
        self.log_file = "/var/lib/sundaya/jspro-powerdesk/logs/disk_auto_reboot.log"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for storing auto reboot logs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create auto_reboot_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_reboot_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    disk_usage INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create disk_alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disk_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    alert_type TEXT NOT NULL,
                    disk_usage INTEGER NOT NULL,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create power_operations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS power_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    operation TEXT NOT NULL,
                    user_name TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create auto_reboot_settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_reboot_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT NOT NULL UNIQUE,
                    setting_value TEXT NOT NULL,
                    updated_by TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default settings if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO auto_reboot_settings (setting_name, setting_value, updated_by)
                VALUES ('disk_threshold', '60', 'system')
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO auto_reboot_settings (setting_name, setting_value, updated_by)
                VALUES ('monitoring_enabled', 'true', 'system')
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO auto_reboot_settings (setting_name, setting_value, updated_by)
                VALUES ('monitoring_interval', '5', 'system')
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def get_overview(self):
        """Get system overview including disk usage, uptime, and auto reboot count"""
        try:
            # Get disk usage
            disk = get_disk_detail()
            disk_usage = {
                "free": round(disk.free / (1024**3), 1),  # Convert to GB
                "used": round(disk.used / (1024**3), 1),  # Convert to GB
                "total": round(disk.total / (1024**3), 1),  # Convert to GB
                "unit": "GB",
                "usage_percent": round((disk.used / disk.total) * 100, 1)
            }
            
            # Get system uptime
            try:
                uptime_output = bash_command(['uptime', '-p'], universal_newlines=True)
                uptime = uptime_output.strip().replace('up ', '') if uptime_output else 'unknown'
            except:
                uptime = "unknown"
            
            # Get auto reboot count (monthly)
            auto_reboot_count = self.get_monthly_auto_reboot_count()
            
            # Get last power operation
            last_operation = self.get_last_power_operation()
            
            return {
                'status_code': 200,
                'status': 'success',
                'data': {
                    'disk_usage': disk_usage,
                    'uptime': uptime,
                    'auto_reboot': auto_reboot_count,
                    'last_operation': last_operation,
                    'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
        except Exception as e:
            return {
                'status_code': 500,
                'status': 'error',
                'message': f'Error getting overview: {str(e)}'
            }
    
    def get_monthly_auto_reboot_count(self):
        """Get monthly auto reboot count"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get monthly count
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            cursor.execute('''
                SELECT COUNT(*) FROM auto_reboot_logs 
                WHERE timestamp >= ? AND action = 'auto_reboot'
            ''', (first_of_month.isoformat(),))
            
            monthly_count = cursor.fetchone()[0]
            conn.close()
            
            return monthly_count
            
        except Exception as e:
            print(f"Error getting monthly auto reboot count: {e}")
            return 0
    
    def get_last_power_operation(self):
        """Get last power operation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, operation, user_name, status FROM power_operations 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            
            last_op = cursor.fetchone()
            conn.close()
            
            if last_op:
                return {
                    'timestamp': last_op[0],
                    'operation': last_op[1],
                    'user': last_op[2],
                    'status': last_op[3]
                }
            else:
                return None
                
        except Exception as e:
            print(f"Error getting last power operation: {e}")
            return None
    
    def log_disk_alert(self, data):
        """Log disk alert to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO disk_alerts (timestamp, alert_type, disk_usage, message)
                VALUES (?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('type', 'warning'),
                data.get('disk_usage'),
                data.get('message', '')
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Disk alert logged successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def log_auto_reboot(self, data):
        """Log auto reboot event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auto_reboot_logs (timestamp, disk_usage, action, status, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('disk_usage'),
                data.get('action', 'auto_reboot'),
                data.get('status', 'initiated'),
                data.get('message', '')
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Auto reboot logged successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def log_power_operation(self, operation, user_name, status='initiated', message=''):
        """Log power operation to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO power_operations (timestamp, operation, user_name, status, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                operation,
                user_name,
                status,
                message
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Power operation logged successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_auto_reboot_settings(self):
        """Get auto reboot settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT setting_name, setting_value, updated_by, updated_at 
                FROM auto_reboot_settings
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            settings = {}
            for row in rows:
                settings[row[0]] = {
                    'value': row[1],
                    'updated_by': row[2],
                    'updated_at': row[3]
                }
            
            return {'success': True, 'data': settings}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_auto_reboot_settings(self, settings_data, user_name):
        """Update auto reboot settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate settings
            valid_settings = ['disk_threshold', 'monitoring_enabled', 'monitoring_interval']
            
            for setting_name, setting_value in settings_data.items():
                if setting_name not in valid_settings:
                    return {'success': False, 'error': f'Invalid setting: {setting_name}'}
                
                # Validate values
                if setting_name == 'disk_threshold':
                    try:
                        threshold = int(setting_value)
                        if threshold < 50 or threshold > 95:
                            return {'success': False, 'error': 'Disk threshold must be between 50-95%'}
                    except ValueError:
                        return {'success': False, 'error': 'Disk threshold must be a valid number'}
                
                elif setting_name == 'monitoring_enabled':
                    if setting_value not in ['true', 'false']:
                        return {'success': False, 'error': 'Monitoring enabled must be true or false'}
                
                elif setting_name == 'monitoring_interval':
                    try:
                        interval = int(setting_value)
                        if interval < 1 or interval > 60:
                            return {'success': False, 'error': 'Monitoring interval must be between 1-60 minutes'}
                    except ValueError:
                        return {'success': False, 'error': 'Monitoring interval must be a valid number'}
            
            # Update settings
            for setting_name, setting_value in settings_data.items():
                cursor.execute('''
                    UPDATE auto_reboot_settings 
                    SET setting_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE setting_name = ?
                ''', (str(setting_value), user_name, setting_name))
            
            conn.commit()
            
            # Log the settings change
            self.log_power_operation(
                f'settings_update', 
                user_name, 
                'completed', 
                f'Updated settings: {", ".join(settings_data.keys())}'
            )
            
            conn.close()
            
            # Update script configuration file if disk threshold changed
            if 'disk_threshold' in settings_data:
                self.update_script_config(settings_data['disk_threshold'])
            
            return {'success': True, 'message': 'Settings updated successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_script_config(self, threshold):
        """Update disk monitoring script threshold"""
        try:
            script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'disk_auto_reboot.sh')
            
            if os.path.exists(script_path):
                # Read current script
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Update threshold line
                import re
                pattern = r'THRESHOLD=\d+'
                replacement = f'THRESHOLD={threshold}'
                updated_content = re.sub(pattern, replacement, content)
                
                # Write updated script
                with open(script_path, 'w') as f:
                    f.write(updated_content)
                
                print(f"Updated script threshold to {threshold}%")
            
        except Exception as e:
            print(f"Error updating script config: {e}")
    
    def get_current_threshold(self):
        """Get current disk threshold setting"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT setting_value FROM auto_reboot_settings 
                WHERE setting_name = 'disk_threshold'
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            return int(result[0]) if result else 60
            
        except Exception as e:
            print(f"Error getting threshold: {e}")
            return 60
    
    def get_auto_reboot_stats(self):
        """Get auto reboot statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get monthly count
            monthly_count = self.get_monthly_auto_reboot_count()
            
            # Get total count
            cursor.execute('''
                SELECT COUNT(*) FROM auto_reboot_logs 
                WHERE action = 'auto_reboot'
            ''')
            
            total_count = cursor.fetchone()[0]
            
            # Get last reboot
            cursor.execute('''
                SELECT timestamp, disk_usage FROM auto_reboot_logs 
                WHERE action = 'auto_reboot'
                ORDER BY timestamp DESC LIMIT 1
            ''')
            
            last_reboot = cursor.fetchone()
            
            conn.close()
            
            result = {
                'monthly_count': monthly_count,
                'total_count': total_count,
                'last_reboot': {
                    'timestamp': last_reboot[0] if last_reboot else None,
                    'disk_usage': last_reboot[1] if last_reboot else None
                } if last_reboot else None
            }
            
            return {'success': True, 'data': result}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_auto_reboot_history(self, from_date=None, to_date=None, limit=None):
        """Get auto reboot history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT timestamp, disk_usage, action, status, message
                FROM auto_reboot_logs 
                WHERE action = 'auto_reboot'
            '''
            params = []
            
            if from_date:
                query += ' AND timestamp >= ?'
                params.append(from_date)
            
            if to_date:
                query += ' AND timestamp <= ?'
                params.append(to_date + ' 23:59:59')
            
            query += ' ORDER BY timestamp DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'timestamp': row[0],
                    'disk_usage': row[1],
                    'action': row[2],
                    'status': row[3],
                    'message': row[4] or ''
                })
            
            conn.close()
            
            return {'success': True, 'data': result}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_auto_reboot_history(self, from_date=None, to_date=None):
        """Export auto reboot history as CSV"""
        try:
            history_result = self.get_auto_reboot_history(from_date, to_date)
            
            if not history_result['success']:
                return history_result
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Timestamp', 'Disk Usage (%)', 'Action', 'Status', 'Message'])
            
            # Write data
            for record in history_result['data']:
                writer.writerow([
                    record['timestamp'],
                    record['disk_usage'],
                    record['action'],
                    record['status'],
                    record['message']
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return {'success': True, 'data': csv_content}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def execute_reboot(self, user_name):
        """Execute system reboot"""
        try:
            # Log the operation
            self.log_power_operation('reboot', user_name, 'initiated')
            
            # Execute reboot command
            subprocess.Popen(['sudo', 'shutdown', '-r', '+1', f'System reboot requested by {user_name} from web interface'])
            
            # Update operation status
            self.log_power_operation('reboot', user_name, 'completed', 'Reboot command issued successfully')
            
            return {
                'success': True,
                'message': 'Reboot command issued successfully. System will restart in 1 minute.',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.log_power_operation('reboot', user_name, 'failed', str(e))
            return {
                'success': False,
                'error': f'Failed to execute reboot command: {str(e)}'
            }
    
    def execute_shutdown(self, user_name):
        """Execute system shutdown"""
        try:
            # Log the operation
            self.log_power_operation('shutdown', user_name, 'initiated')
            
            # Execute shutdown command
            subprocess.Popen(['sudo', 'shutdown', '-h', '+1', f'System shutdown requested by {user_name} from web interface'])
            
            # Update operation status
            self.log_power_operation('shutdown', user_name, 'completed', 'Shutdown command issued successfully')
            
            return {
                'success': True,
                'message': 'Shutdown command issued successfully. System will shut down in 1 minute.',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.log_power_operation('shutdown', user_name, 'failed', str(e))
            return {
                'success': False,
                'error': f'Failed to execute shutdown command: {str(e)}'
            }
