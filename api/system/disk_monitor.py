"""
Enhanced API endpoints for disk monitoring and auto reboot functionality
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import jsonify, request
import subprocess
import csv
import io

class DiskMonitorAPI:
    def __init__(self):
        self.db_path = "/var/log/auto_reboot.db"
        self.log_file = "/var/log/disk_auto_reboot.log"
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
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def get_disk_usage(self):
        """Get current disk usage percentage"""
        try:
            result = subprocess.run(['df', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    fields = lines[1].split()
                    if len(fields) >= 5:
                        usage_str = fields[4].replace('%', '')
                        usage = int(usage_str)
                        return {
                            'success': True,
                            'data': {
                                'usage': usage,
                                'used': fields[2],
                                'available': fields[3],
                                'total': fields[1],
                                'mount_point': fields[5] if len(fields) > 5 else '/'
                            }
                        }
            
            return {'success': False, 'error': 'Unable to get disk usage'}
            
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
    
    def get_auto_reboot_stats(self):
        """Get auto reboot statistics"""
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

# Global instance
disk_monitor_api = DiskMonitorAPI()

def handle_disk_usage():
    """API endpoint: GET /api/system/disk-usage"""
    return jsonify(disk_monitor_api.get_disk_usage())

def handle_auto_reboot_log():
    """API endpoint: POST /api/system/auto-reboot-log"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    return jsonify(disk_monitor_api.log_auto_reboot(data))

def handle_disk_alert():
    """API endpoint: POST /api/system/disk-alert"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    return jsonify(disk_monitor_api.log_disk_alert(data))

def handle_auto_reboot_stats():
    """API endpoint: GET /api/system/auto-reboot-stats"""
    return jsonify(disk_monitor_api.get_auto_reboot_stats())

def handle_auto_reboot_history():
    """API endpoint: GET /api/system/auto-reboot-history"""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    limit = request.args.get('limit', type=int)
    
    return jsonify(disk_monitor_api.get_auto_reboot_history(from_date, to_date, limit))

def handle_auto_reboot_history_export():
    """API endpoint: GET /api/system/auto-reboot-history/export"""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    result = disk_monitor_api.export_auto_reboot_history(from_date, to_date)
    
    if result['success']:
        from flask import Response
        return Response(
            result['data'],
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=auto_reboot_history_{from_date or "all"}_{to_date or "all"}.csv'
            }
        )
    else:
        return jsonify(result), 500
