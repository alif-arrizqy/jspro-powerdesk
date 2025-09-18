import os
import sqlite3
import json
from datetime import datetime
from flask import jsonify, request
from . import service_bp
from auths import token_auth as auth

# MQTT Database configuration
MQTT_DB_PATH = '/var/lib/sundaya/ehub-talis/database/mqtt_logs.db'

# MQTT Log file paths
MQTT_LOG_PATHS = {
    'mqtt_all.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_all.log',
    'mqtt_errors.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_errors.log',
    'mqtt_warnings.log': '/var/lib/sundaya/ehub-talis/logs/mqtt_warnings.log'
}

@service_bp.route('/mqtt/logs', methods=['GET'])
@auth.login_required
def get_mqtt_logs():
    """
    Get MQTT logs from log files
    
    Query parameters:
    - log_type: mqtt_all.log, mqtt_errors.log, mqtt_warnings.log (default: mqtt_all.log)
    - lines: number of lines to retrieve (default: 100, max: 1000)
    - reverse: true/false - reverse order (newest first) (default: false)
    """
    try:
        # Get query parameters
        log_type = request.args.get('log_type', 'mqtt_all.log')
        lines = min(int(request.args.get('lines', 100)), 1000)
        reverse = request.args.get('reverse', 'false').lower() == 'true'
        
        # Validate log type
        if log_type not in MQTT_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {list(MQTT_LOG_PATHS.keys())}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        log_file_path = MQTT_LOG_PATHS[log_type]
        
        # Check if log file exists
        if not os.path.exists(log_file_path):
            return jsonify({
                'status': 'success',
                'data': {
                    'logs': [],
                    'total_lines': 0,
                    'log_type': log_type,
                    'message': 'Log file not found or empty'
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Read log file
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Get last N lines
            if lines > 0:
                log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            else:
                log_lines = all_lines
            
            # Apply reverse order if requested
            if reverse:
                log_lines = log_lines[::-1]
            
            # Clean up lines
            log_lines = [line.strip() for line in log_lines if line.strip()]
            
            return jsonify({
                'status': 'success',
                'data': {
                    'logs': log_lines,
                    'total_lines': len(log_lines),
                    'total_file_lines': len(all_lines),
                    'log_type': log_type,
                    'file_path': log_file_path,
                    'reverse_order': reverse,
                    'requested_lines': lines
                },
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except PermissionError:
            return jsonify({
                'status': 'error',
                'message': f'Permission denied accessing log file: {log_file_path}',
                'timestamp': datetime.now().isoformat()
            }), 403
            
        except UnicodeDecodeError as e:
            return jsonify({
                'status': 'error',
                'message': f'Unable to read log file due to encoding issues: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid parameter value: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/mqtt/logs/download', methods=['GET'])
@auth.login_required
def download_mqtt_logs():
    """
    Download MQTT logs as text file
    
    Query parameters:
    - log_type: mqtt_all.log, mqtt_errors.log, mqtt_warnings.log (default: mqtt_all.log)
    - lines: number of lines to retrieve (default: 1000, max: 5000)
    """
    try:
        from flask import Response
        
        # Get query parameters
        log_type = request.args.get('log_type', 'mqtt_all.log')
        lines = min(int(request.args.get('lines', 1000)), 5000)
        
        # Validate log type
        if log_type not in MQTT_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {list(MQTT_LOG_PATHS.keys())}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        log_file_path = MQTT_LOG_PATHS[log_type]
        
        # Check if log file exists
        if not os.path.exists(log_file_path):
            return jsonify({
                'status': 'error',
                'message': 'Log file not found',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # Read log file
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Get last N lines
            if lines > 0 and lines < len(all_lines):
                log_lines = all_lines[-lines:]
            else:
                log_lines = all_lines
            
            # Prepare content for download
            content = ''.join(log_lines)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'mqtt_{log_type.replace(".log", "")}_{timestamp}.log'
            
            return Response(
                content,
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': 'text/plain; charset=utf-8'
                }
            )
            
        except PermissionError:
            return jsonify({
                'status': 'error',
                'message': f'Permission denied accessing log file: {log_file_path}',
                'timestamp': datetime.now().isoformat()
            }), 403
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/mqtt/data', methods=['GET'])
@auth.login_required
def get_mqtt_monitoring_data():
    """
    Get MQTT monitoring data from SQLite database
    
    Query parameters:
    - limit: number of records to retrieve (default: 50, max: 500)
    - order: asc/desc (default: desc - newest first)
    - start_date: filter from date (YYYY-MM-DD format)
    - end_date: filter to date (YYYY-MM-DD format)
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 500)
        order = request.args.get('order', 'desc').lower()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Validate order parameter
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Check if database exists
        if not os.path.exists(MQTT_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'records': [],
                    'total_count': 0,
                    'message': 'MQTT database not found'
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_DB_PATH)
        cursor = conn.cursor()
        
        # Build query with optional date filtering
        query = "SELECT id, datetime, data FROM log_mqtt"
        params = []
        
        # Add date filtering if provided
        where_conditions = []
        if start_date:
            where_conditions.append("datetime >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            where_conditions.append("datetime <= ?")
            params.append(f"{end_date} 23:59:59")
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += f" ORDER BY datetime {order.upper()}, id {order.upper()}"
        query += " LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM log_mqtt"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions[:-1] if params else where_conditions)
            cursor.execute(count_query, params[:-1] if params else [])
        else:
            cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Process records
        processed_records = []
        for record in records:
            try:
                record_id, record_datetime, record_data = record
                
                # Parse JSON data
                data_dict = json.loads(record_data) if record_data else {}
                
                processed_records.append({
                    'id': record_id,
                    'datetime': record_datetime,
                    'data': data_dict
                })
            except json.JSONDecodeError:
                # If JSON parsing fails, store as raw string
                processed_records.append({
                    'id': record_id,
                    'datetime': record_datetime,
                    'data': {'raw': record_data}
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'records': processed_records,
                'total_count': total_count,
                'returned_count': len(processed_records),
                'limit': limit,
                'order': order,
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid parameter value: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/mqtt/data/latest', methods=['GET'])
@auth.login_required
def get_latest_mqtt_data():
    """
    Get latest MQTT data values for monitoring cards
    
    Returns the most recent data entry with parsed key-value pairs
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'MQTT database not found'
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_DB_PATH)
        cursor = conn.cursor()
        
        # Get the most recent record
        cursor.execute("""
            SELECT datetime, data 
            FROM log_mqtt 
            ORDER BY datetime DESC, id DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'No data found in database'
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        
        record_datetime, record_data = result
        
        # Parse JSON data
        try:
            data_dict = json.loads(record_data) if record_data else {}
            
            # Extract data array if it exists
            if 'data' in data_dict and isinstance(data_dict['data'], list):
                # Convert array of key-value pairs to flat dictionary
                latest_values = {}
                for item in data_dict['data']:
                    if isinstance(item, dict) and 'key' in item and 'val' in item:
                        latest_values[item['key']] = item['val']
                
                # Also include timestamp and site info if available
                if 'ts' in data_dict:
                    latest_values['timestamp'] = data_dict['ts']
                if 'site' in data_dict:
                    latest_values['site'] = data_dict['site']
                
            else:
                # If data is not in expected format, return as is
                latest_values = data_dict
            
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': latest_values,
                    'record_timestamp': record_datetime,
                    'total_keys': len(latest_values)
                },
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse JSON data from database',
                'timestamp': datetime.now().isoformat()
            }), 500
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/mqtt/data/stats', methods=['GET'])
@auth.login_required
def get_mqtt_data_stats():
    """
    Get MQTT data statistics
    
    Returns database statistics and summary information
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'total_records': 0,
                    'database_size': 0,
                    'first_record': None,
                    'last_record': None,
                    'message': 'MQTT database not found'
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Get database file size
        db_size = os.path.getsize(MQTT_DB_PATH)
        
        # Connect to database
        conn = sqlite3.connect(MQTT_DB_PATH)
        cursor = conn.cursor()
        
        # Get total record count
        cursor.execute("SELECT COUNT(*) FROM log_mqtt")
        total_records = cursor.fetchone()[0]
        
        # Get first record datetime
        cursor.execute("SELECT datetime FROM log_mqtt ORDER BY datetime ASC, id ASC LIMIT 1")
        first_record = cursor.fetchone()
        first_datetime = first_record[0] if first_record else None
        
        # Get last record datetime
        cursor.execute("SELECT datetime FROM log_mqtt ORDER BY datetime DESC, id DESC LIMIT 1")
        last_record = cursor.fetchone()
        last_datetime = last_record[0] if last_record else None
        
        # Get records count for today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM log_mqtt WHERE datetime >= ? AND datetime < ?", 
                      (f"{today} 00:00:00", f"{today} 23:59:59"))
        today_records = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_records': total_records,
                'today_records': today_records,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / 1024 / 1024, 2),
                'first_record_datetime': first_datetime,
                'last_record_datetime': last_datetime,
                'database_path': MQTT_DB_PATH
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@service_bp.route('/mqtt/info', methods=['GET'])
def get_mqtt_info():
    """
    Get MQTT service information and available endpoints
    """
    return jsonify({
        'status': 'success',
        'data': {
            'service': 'MQTT Monitoring API',
            'description': 'API endpoints for monitoring MQTT service logs and data',
            'endpoints': {
                'logs': {
                    'path': '/api/v1/service/mqtt/logs',
                    'method': 'GET',
                    'description': 'Get MQTT logs from log files',
                    'parameters': {
                        'log_type': 'mqtt_all.log | mqtt_errors.log | mqtt_warnings.log',
                        'lines': 'number of lines (max 1000)',
                        'reverse': 'true/false for reverse order'
                    }
                },
                'download_logs': {
                    'path': '/api/v1/service/mqtt/logs/download',
                    'method': 'GET',
                    'description': 'Download MQTT logs as file',
                    'parameters': {
                        'log_type': 'mqtt_all.log | mqtt_errors.log | mqtt_warnings.log',
                        'lines': 'number of lines (max 5000)'
                    }
                },
                'data': {
                    'path': '/api/v1/service/mqtt/data',
                    'method': 'GET',
                    'description': 'Get MQTT data from database',
                    'parameters': {
                        'limit': 'number of records (max 500)',
                        'order': 'asc/desc',
                        'start_date': 'YYYY-MM-DD',
                        'end_date': 'YYYY-MM-DD'
                    }
                },
                'latest_data': {
                    'path': '/api/v1/service/mqtt/data/latest',
                    'method': 'GET',
                    'description': 'Get latest MQTT data for monitoring'
                },
                'stats': {
                    'path': '/api/v1/service/mqtt/data/stats',
                    'method': 'GET',
                    'description': 'Get MQTT database statistics'
                },
                'info': {
                    'path': '/api/v1/service/mqtt/info',
                    'method': 'GET',
                    'description': 'Get MQTT service information'
                }
            },
            'log_files': list(MQTT_LOG_PATHS.keys()),
            'database_path': MQTT_DB_PATH
        },
        'timestamp': datetime.now().isoformat()
    }), 200
