import os
import sqlite3
import json
from datetime import datetime
from flask import jsonify, request, Response
from . import service_bp
from auths import token_auth as auth
from config import PATH

# ============================================================================
# MQTT BAKTI Configuration
# ============================================================================
# Database: mqtt_logs.db, Table: mqtt_bakti_summary
MQTT_BAKTI_DB_PATH = f'{PATH}/database/mqtt_logs.db'

# Log file paths for MQTT Bakti
MQTT_BAKTI_LOG_PATHS = {
    'mqtt_bakti_all.log': f'{PATH}/logs/mqtt_bakti_all.log',
    'mqtt_bakti_errors.log': f'{PATH}/logs/mqtt_bakti_errors.log',
    'mqtt_bakti_warnings.log': f'{PATH}/logs/mqtt_bakti_warnings.log'
}

# ============================================================================
# MQTT SUNDAYA (Loggers) Configuration
# ============================================================================
# Database: data_storage.db, Tables: mqtt_energy_summary, mqtt_battery_summary
MQTT_SUNDAYA_DB_PATH = f'{PATH}/database/data_storage.db'

# Log file paths for MQTT Sundaya
MQTT_SUNDAYA_LOG_PATHS = {
    'mqtt_sundaya_info.log': f'{PATH}/logs/mqtt_sundaya_info.log',
    'mqtt_sundaya_error.log': f'{PATH}/logs/mqtt_sundaya_error.log'
}

# Helper: convert YYYY-MM-DD to DB timestamp format used in tables (YYYYMMDDThhmmss)
def _date_to_db_ts_start(date_str):
    """Convert a YYYY-MM-DD date to DB timestamp start (YYYYMMDDT000000).

    Returns None if input is falsy or malformed.
    """
    if not date_str:
        return None
    try:
        # remove dashes and append start-of-day
        return date_str.replace('-', '') + 'T000000'
    except Exception:
        return None


def _date_to_db_ts_end(date_str):
    """Convert a YYYY-MM-DD date to DB timestamp end (YYYYMMDDT235959).

    Returns None if input is falsy or malformed.
    """
    if not date_str:
        return None
    try:
        return date_str.replace('-', '') + 'T235959'
    except Exception:
        return None


# ============================================================================
# MQTT BAKTI ENDPOINTS
# ============================================================================

@service_bp.route('/mqtt-bakti/logs', methods=['GET'])
@auth.login_required
def get_mqtt_bakti_logs():
    """
    Get MQTT Bakti logs from log files
    
    Query parameters:
    - log_type: mqtt_bakti_all.log, mqtt_bakti_errors.log, mqtt_bakti_warnings.log (default: mqtt_bakti_all.log)
    - lines: number of lines to retrieve (default: 100, max: 1000)
    - reverse: true/false - reverse order (newest first) (default: false)
    """
    try:
        # Get query parameters
        log_type = request.args.get('log_type', 'mqtt_bakti_all.log')
        lines = min(int(request.args.get('lines', 100)), 1000)
        reverse = request.args.get('reverse', 'false').lower() == 'true'
        
        # Validate log type
        if log_type not in MQTT_BAKTI_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {list(MQTT_BAKTI_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        log_file_path = MQTT_BAKTI_LOG_PATHS[log_type]
        
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
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
            
        except PermissionError:
            return jsonify({
                'status': 'error',
                'message': f'Permission denied accessing log file: {log_file_path}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 403
            
        except UnicodeDecodeError as e:
            return jsonify({
                'status': 'error',
                'message': f'Unable to read log file due to encoding issues: {str(e)}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid parameter value: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/logs/download', methods=['GET'])
@auth.login_required
def download_mqtt_bakti_logs():
    """
    Download MQTT Bakti logs as text file
    
    Query parameters:
    - log_type: mqtt_bakti_all.log, mqtt_bakti_errors.log, mqtt_bakti_warnings.log (default: mqtt_bakti_all.log)
    - lines: number of lines to retrieve (default: 1000, max: 5000)
    """
    try:
        # Get query parameters
        log_type = request.args.get('log_type', 'mqtt_bakti_all.log')
        lines = min(int(request.args.get('lines', 1000)), 5000)
        
        # Validate log type
        if log_type not in MQTT_BAKTI_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {list(MQTT_BAKTI_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        log_file_path = MQTT_BAKTI_LOG_PATHS[log_type]
        
        # Check if log file exists
        if not os.path.exists(log_file_path):
            return jsonify({
                'status': 'error',
                'message': 'Log file not found',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 403
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/logs/clear', methods=['DELETE'])
@auth.login_required
def clear_mqtt_bakti_logs():
    """
    Clear MQTT Bakti log files
    
    Parameters:
    - log_type: mqtt_bakti_all.log | mqtt_bakti_errors.log | mqtt_bakti_warnings.log (default: clears all)
    """
    try:
        log_type = request.args.get('log_type', None)
        
        # Validate log type if provided
        if log_type and log_type not in MQTT_BAKTI_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {", ".join(MQTT_BAKTI_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        cleared_files = []
        errors = []
        
        # Determine which files to clear
        files_to_clear = {log_type: MQTT_BAKTI_LOG_PATHS[log_type]} if log_type else MQTT_BAKTI_LOG_PATHS
        
        for log_name, log_path in files_to_clear.items():
            try:
                if os.path.exists(log_path):
                    # Clear the file by opening in write mode and closing immediately
                    with open(log_path, 'w', encoding='utf-8') as f:
                        pass
                    cleared_files.append(log_name)
                else:
                    errors.append(f'{log_name}: File not found')
            except Exception as e:
                errors.append(f'{log_name}: {str(e)}')
        
        return jsonify({
            'status': 'success' if cleared_files else 'error',
            'data': {
                'cleared_files': cleared_files,
                'errors': errors
            },
            'message': f'Successfully cleared {len(cleared_files)} log file(s)' if cleared_files else 'No files were cleared',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear log files: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/summary', methods=['GET'])
@auth.login_required
def get_mqtt_bakti_summary():
    """
    Get MQTT Bakti summary data from mqtt_bakti_summary table
    
    Query parameters:
    - limit: number of records to retrieve (default: 50, max: 500)
    - order: asc/desc (default: desc - newest first)
    - start_date: filter from date (YYYY-MM-DD format)
    - end_date: filter to date (YYYY-MM-DD format)
    - mqtt_status: filter by status (sent/pending/failed)
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 500)
        order = request.args.get('order', 'desc').lower()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        mqtt_status = request.args.get('mqtt_status')
        
        # Validate order parameter
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Check if database exists
        if not os.path.exists(MQTT_BAKTI_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'records': [],
                    'total_count': 0,
                    'message': 'MQTT Bakti database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_BAKTI_DB_PATH)
        cursor = conn.cursor()
        
        # Build query with optional filtering
        query = "SELECT id, timestamp, processed_time, data_summary, mqtt_status, broker_response, retry_count FROM mqtt_bakti_summary"
        params = []
        
        # Add filtering if provided
        where_conditions = []
        if start_date:
                where_conditions.append("timestamp >= ?")
                params.append(start_date)
        if end_date:
                where_conditions.append("timestamp <= ?")
                params.append(end_date)
        if mqtt_status:
            where_conditions.append("mqtt_status = ?")
            params.append(mqtt_status)
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += f" ORDER BY timestamp {order.upper()}, id {order.upper()}"
        query += " LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM mqtt_bakti_summary"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions)
            cursor.execute(count_query, params[:-1])
        else:
            cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Process records
        processed_records = []
        for record in records:
            try:
                rec_id, rec_timestamp, rec_processed_time, rec_data_summary, rec_mqtt_status, rec_broker_response, rec_retry_count = record
                
                # Parse JSON data
                data_dict = json.loads(rec_data_summary) if rec_data_summary else {}
                
                processed_records.append({
                    'id': rec_id,
                    'timestamp': rec_timestamp,
                    'processed_time': rec_processed_time,
                    'data_summary': data_dict,
                    'mqtt_status': rec_mqtt_status,
                    'broker_response': rec_broker_response,
                    'retry_count': rec_retry_count
                })
            except json.JSONDecodeError:
                # If JSON parsing fails, store as raw string
                processed_records.append({
                    'id': rec_id,
                    'timestamp': rec_timestamp,
                    'processed_time': rec_processed_time,
                    'data_summary': {'raw': rec_data_summary},
                    'mqtt_status': rec_mqtt_status,
                    'broker_response': rec_broker_response,
                    'retry_count': rec_retry_count
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
                    'end_date': end_date,
                    'mqtt_status': mqtt_status
                }
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid parameter value: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/summary/latest', methods=['GET'])
@auth.login_required
def get_latest_mqtt_bakti_summary():
    """
    Get latest MQTT Bakti summary data for monitoring
    
    Returns the most recent summary entry
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_BAKTI_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'MQTT Bakti database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_BAKTI_DB_PATH)
        cursor = conn.cursor()
        
        # Get the most recent record
        cursor.execute("""
            SELECT timestamp, data_summary, mqtt_status, broker_response
            FROM mqtt_bakti_summary 
            ORDER BY timestamp DESC, id DESC 
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
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        record_timestamp, record_data_summary, record_mqtt_status, record_broker_response = result
        
        # Parse JSON data
        try:
            data_dict = json.loads(record_data_summary) if record_data_summary else {}
            
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
                    'mqtt_status': record_mqtt_status,
                    'broker_response': record_broker_response,
                    'total_keys': len(latest_values)
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse JSON data from database',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 500
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/stats', methods=['GET'])
@auth.login_required
def get_mqtt_bakti_stats():
    """
    Get MQTT Bakti statistics
    
    Returns database statistics and summary information
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_BAKTI_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'total_records': 0,
                    'database_size': 0,
                    'first_record': None,
                    'last_record': None,
                    'message': 'MQTT Bakti database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Get database file size
        db_size = os.path.getsize(MQTT_BAKTI_DB_PATH)
        
        # Connect to database
        conn = sqlite3.connect(MQTT_BAKTI_DB_PATH)
        cursor = conn.cursor()
        
        # Get total record count
        cursor.execute("SELECT COUNT(*) FROM mqtt_bakti_summary")
        total_records = cursor.fetchone()[0]
        
        # Get status counts
        cursor.execute("SELECT mqtt_status, COUNT(*) FROM mqtt_bakti_summary GROUP BY mqtt_status")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get message status counts
        cursor.execute("SELECT COUNT(*) FROM mqtt_bakti_summary WHERE mqtt_status = 'sent'")
        total_msg_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mqtt_bakti_summary WHERE mqtt_status = 'pending'")
        total_msg_pending = cursor.fetchone()[0]
        
        # Get first record timestamp
        cursor.execute("SELECT timestamp FROM mqtt_bakti_summary ORDER BY timestamp ASC, id ASC LIMIT 1")
        first_record = cursor.fetchone()
        first_timestamp = first_record[0] if first_record else None
        
        # Get last record timestamp
        cursor.execute("SELECT timestamp FROM mqtt_bakti_summary ORDER BY timestamp DESC, id DESC LIMIT 1")
        last_record = cursor.fetchone()
        last_timestamp = last_record[0] if last_record else None
        
        # Get records count for today (convert to DB timestamp format)
        today = datetime.now().strftime('%Y-%m-%d')
        today_start = _date_to_db_ts_start(today)
        today_end = _date_to_db_ts_end(today)
        cursor.execute("SELECT COUNT(*) FROM mqtt_bakti_summary WHERE timestamp >= ? AND timestamp <= ?", (today_start, today_end))
        today_records = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_records': total_records,
                'today_records': today_records,
                'status_counts': status_counts,
                'total_msg_sent': total_msg_sent,
                'total_msg_pending': total_msg_pending,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / 1024 / 1024, 2),
                'first_record_timestamp': first_timestamp,
                'last_record_timestamp': last_timestamp
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-bakti/info', methods=['GET'])
def get_mqtt_bakti_info():
    """
    Get MQTT Bakti service information and available endpoints
    """
    return jsonify({
        'status': 'success',
        'data': {
            'service': 'MQTT Bakti Monitoring API',
            'description': 'API endpoints for monitoring MQTT Bakti service logs and data (ehub_broker)',
            'endpoints': {
                'logs': {
                    'path': '/api/v1/service/mqtt-bakti/logs',
                    'method': 'GET',
                    'description': 'Get MQTT Bakti logs from log files',
                    'parameters': {
                        'log_type': 'mqtt_bakti_all.log | mqtt_bakti_errors.log | mqtt_bakti_warnings.log',
                        'lines': 'number of lines (max 1000)',
                        'reverse': 'true/false for reverse order'
                    }
                },
                'download_logs': {
                    'path': '/api/v1/service/mqtt-bakti/logs/download',
                    'method': 'GET',
                    'description': 'Download MQTT Bakti logs as file',
                    'parameters': {
                        'log_type': 'mqtt_bakti_all.log | mqtt_bakti_errors.log | mqtt_bakti_warnings.log',
                        'lines': 'number of lines (max 5000)'
                    }
                },
                'summary': {
                    'path': '/api/v1/service/mqtt-bakti/summary',
                    'method': 'GET',
                    'description': 'Get MQTT Bakti summary data from database',
                    'parameters': {
                        'limit': 'number of records (max 500)',
                        'order': 'asc/desc',
                        'start_date': 'YYYY-MM-DD',
                        'end_date': 'YYYY-MM-DD',
                        'mqtt_status': 'success/failed/pending'
                    }
                },
                'latest_summary': {
                    'path': '/api/v1/service/mqtt-bakti/summary/latest',
                    'method': 'GET',
                    'description': 'Get latest MQTT Bakti summary for monitoring'
                },
                'stats': {
                    'path': '/api/v1/service/mqtt-bakti/stats',
                    'method': 'GET',
                    'description': 'Get MQTT Bakti database statistics'
                },
                'info': {
                    'path': '/api/v1/service/mqtt-bakti/info',
                    'method': 'GET',
                    'description': 'Get MQTT Bakti service information'
                }
            },
            'log_files': list(MQTT_BAKTI_LOG_PATHS.keys()),
            'database_path': MQTT_BAKTI_DB_PATH,
            'table_name': 'mqtt_bakti_summary',
            'broker': 'ehub_broker'
        },
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200


# ================== MQTT SUNDAYA ENDPOINTS ==================

@service_bp.route('/mqtt-sundaya/logs', methods=['GET'])
@auth.login_required
def get_mqtt_sundaya_logs():
    """
    Get MQTT Sundaya logs from log files
    
    Parameters:
    - log_type: mqtt_sundaya_info.log | mqtt_sundaya_error.log (default: mqtt_sundaya_info.log)
    - lines: number of lines to return (default: 64, max: 1600)
    - reverse: true/false to reverse order (default: true - newest first)
    """
    try:
        # Get parameters
        log_type = request.args.get('log_type', 'mqtt_sundaya_info.log')
        lines = int(request.args.get('lines', 64))
        reverse = request.args.get('reverse', 'true').lower() == 'true'
        
        # Validate log type
        if log_type not in MQTT_SUNDAYA_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {", ".join(MQTT_SUNDAYA_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        # Limit lines
        if lines > 1600:
            lines = 1600
        elif lines < 16:
            lines = 16
        
        # Get log file path
        log_path = MQTT_SUNDAYA_LOG_PATHS[log_type]
        
        # Check if log file exists
        if not os.path.exists(log_path):
            return jsonify({
                'status': 'success',
                'data': {
                    'logs': [],
                    'total_lines': 0,
                    'log_type': log_type,
                    'message': 'Log file not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Read log file
        with open(log_path, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # Get last N lines
        log_lines = log_lines[-lines:]
        
        # Reverse if requested (default is newest first)
        if reverse:
            log_lines = log_lines[::-1]
        
        # Remove newlines
        log_lines = [line.rstrip('\n') for line in log_lines]
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': log_lines,
                'total_lines': len(log_lines),
                'log_type': log_type,
                'reversed': reverse
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to read log file: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/logs/clear', methods=['DELETE'])
@auth.login_required
def clear_mqtt_sundaya_logs():
    """
    Clear MQTT Sundaya log files
    
    Parameters:
    - log_type: mqtt_sundaya_info.log | mqtt_sundaya_error.log (default: clears all)
    """
    try:
        log_type = request.args.get('log_type', None)
        
        # Validate log type if provided
        if log_type and log_type not in MQTT_SUNDAYA_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {", ".join(MQTT_SUNDAYA_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        cleared_files = []
        errors = []
        
        # Determine which files to clear
        files_to_clear = {log_type: MQTT_SUNDAYA_LOG_PATHS[log_type]} if log_type else MQTT_SUNDAYA_LOG_PATHS
        
        for log_name, log_path in files_to_clear.items():
            try:
                if os.path.exists(log_path):
                    # Clear the file by opening in write mode and closing immediately
                    with open(log_path, 'w', encoding='utf-8') as f:
                        pass
                    cleared_files.append(log_name)
                else:
                    errors.append(f'{log_name}: File not found')
            except Exception as e:
                errors.append(f'{log_name}: {str(e)}')
        
        return jsonify({
            'status': 'success' if cleared_files else 'error',
            'data': {
                'cleared_files': cleared_files,
                'errors': errors
            },
            'message': f'Successfully cleared {len(cleared_files)} log file(s)' if cleared_files else 'No files were cleared',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear log files: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/logs/download', methods=['GET'])
@auth.login_required
def download_mqtt_sundaya_logs():
    """
    Download MQTT Sundaya logs as file
    
    Parameters:
    - log_type: mqtt_sundaya_info.log | mqtt_sundaya_errors.log | mqtt_sundaya_warnings.log (default: mqtt_sundaya_info.log)
    - lines: number of lines to include (default: all, max: 16000)
    """
    try:
        # Get parameters
        log_type = request.args.get('log_type', 'mqtt_sundaya_info.log')
        lines = request.args.get('lines', None)
        
        # Validate log type
        if log_type not in MQTT_SUNDAYA_LOG_PATHS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid log type. Available types: {", ".join(MQTT_SUNDAYA_LOG_PATHS.keys())}',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        # Get log file path
        log_path = MQTT_SUNDAYA_LOG_PATHS[log_type]
        
        # Check if log file exists
        if not os.path.exists(log_path):
            return jsonify({
                'status': 'error',
                'message': 'Log file not found',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 404
        
        # Read log file
        with open(log_path, 'r', encoding='utf-8') as f:
            if lines:
                lines_int = int(lines)
                if lines_int > 16000:
                    lines_int = 16000
                log_content = ''.join(f.readlines()[-lines_int:])
            else:
                log_content = f.read()
        
        # Create response
        response = Response(log_content, mimetype='text/plain')
        response.headers['Content-Disposition'] = f'attachment; filename={log_type}'
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to download log file: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/energy/summary', methods=['GET'])
@auth.login_required
def get_mqtt_energy_summary():
    """
    Get MQTT energy summary data from database
    
    Parameters:
    - limit: number of records to return (default: 100, max: 500)
    - order: asc/desc order by timestamp (default: desc)
    - start_date: filter records from this date (format: YYYY-MM-DD)
    - end_date: filter records until this date (format: YYYY-MM-DD)
    """
    try:
        # Get parameters
        limit = int(request.args.get('limit', 100))
        order = request.args.get('order', 'desc').lower()
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        # Validate and limit parameters
        if limit > 500:
            limit = 500
        elif limit < 1:
            limit = 1
            
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Check if database exists
        if not os.path.exists(MQTT_SUNDAYA_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'records': [],
                    'total': 0,
                    'message': 'MQTT Sundaya database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_SUNDAYA_DB_PATH)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT id, timestamp, data_summary, mqtt_status, retry_count, last_retry_time FROM mqtt_energy_summary WHERE 1=1"
        params = []
        
        if start_date:
            ts_start = _date_to_db_ts_start(start_date)
            if ts_start:
                query += " AND timestamp >= ?"
                params.append(ts_start)
        
        if end_date:
            ts_end = _date_to_db_ts_end(end_date)
            if ts_end:
                query += " AND timestamp <= ?"
                params.append(ts_end)
        
        query += f" ORDER BY timestamp {order.upper()}, id {order.upper()} LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        records = []
        for row in results:
            (record_id,
             record_timestamp,
             record_data_summary,
             record_mqtt_status,
             record_retry_count,
             record_last_retry_time) = row
            try:
                data_dict = json.loads(record_data_summary) if record_data_summary else {}
            except json.JSONDecodeError:
                data_dict = {'raw': record_data_summary}
            
            records.append({
                'id': record_id,
                'record_timestamp': record_timestamp,
                'data': data_dict,
                'mqtt_status': record_mqtt_status,
                'retry_count': record_retry_count,
                'last_retry_time': record_last_retry_time
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'records': records,
                'total_records': len(records),
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/battery/summary', methods=['GET'])
@auth.login_required
def get_mqtt_battery_summary():
    """
    Get MQTT battery summary data from database
    
    Parameters:
    - limit: number of records to return (default: 100, max: 500)
    - order: asc/desc order by timestamp (default: desc)
    - start_date: filter records from this date (format: YYYY-MM-DD)
    - end_date: filter records until this date (format: YYYY-MM-DD)
    
    Returns structured battery data: timestamp, battery_type, pcb_code, slave_id, voltage, current
    """
    try:
        # Get parameters
        limit = int(request.args.get('limit', 100))
        order = request.args.get('order', 'desc').lower()
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        # Validate and limit parameters
        if limit > 500:
            limit = 500
        elif limit < 1:
            limit = 1
            
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Check if database exists
        if not os.path.exists(MQTT_SUNDAYA_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'records': [],
                    'total': 0,
                    'message': 'MQTT Sundaya database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_SUNDAYA_DB_PATH)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT id, timestamp, data_summary FROM mqtt_battery_summary WHERE 1=1"
        params = []
        
        if start_date:
            ts_start = _date_to_db_ts_start(start_date)
            if ts_start:
                query += " AND timestamp >= ?"
                params.append(ts_start)
        
        if end_date:
            ts_end = _date_to_db_ts_end(end_date)
            if ts_end:
                query += " AND timestamp <= ?"
                params.append(ts_end)
        
        query += f" ORDER BY timestamp {order.upper()}, id {order.upper()} LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        records = []
        for row in results:
            record_id, record_timestamp, record_data = row
            try:
                data_dict = json.loads(record_data) if record_data else {}
            except json.JSONDecodeError:
                data_dict = {'raw': record_data}
            
            records.append({
                'id': record_id,
                'data': data_dict
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'records': records,
                'total': len(records),
                'limit': limit,
                'order': order
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/energy/latest', methods=['GET'])
@auth.login_required
def get_latest_mqtt_energy():
    """
    Get latest MQTT energy data for monitoring
    
    Returns the most recent energy record with formatted data
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_SUNDAYA_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'MQTT Sundaya database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_SUNDAYA_DB_PATH)
        cursor = conn.cursor()
        
        # Get latest record
        cursor.execute("SELECT timestamp, data_summary FROM mqtt_energy_summary ORDER BY timestamp DESC, id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'No energy data found in database'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        record_timestamp, record_data = result
        
        # Parse JSON data
        try:
            data_dict = json.loads(record_data) if record_data else {}
            
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': data_dict,
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse JSON data from database',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 500
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/battery/latest', methods=['GET'])
@auth.login_required
def get_latest_mqtt_battery():
    """
    Get latest MQTT battery data for monitoring
    
    Returns the most recent battery record with formatted data
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_SUNDAYA_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'MQTT Sundaya database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Connect to database
        conn = sqlite3.connect(MQTT_SUNDAYA_DB_PATH)
        cursor = conn.cursor()
        
        # Get latest record
        cursor.execute("SELECT timestamp, data_summary FROM mqtt_battery_summary ORDER BY timestamp DESC, id DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': {},
                    'timestamp': None,
                    'message': 'No battery data found in database'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        record_timestamp, record_data = result
        
        # Parse JSON data
        try:
            data_dict = json.loads(record_data) if record_data else {}
            
            return jsonify({
                'status': 'success',
                'data': {
                    'latest_data': data_dict,
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse JSON data from database',
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 500
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/stats', methods=['GET'])
@auth.login_required
def get_mqtt_sundaya_stats():
    """
    Get MQTT Sundaya statistics
    
    Returns database statistics for both energy and battery tables
    """
    try:
        # Check if database exists
        if not os.path.exists(MQTT_SUNDAYA_DB_PATH):
            return jsonify({
                'status': 'success',
                'data': {
                    'total_records': 0,
                    'database_size': 0,
                    'message': 'MQTT Sundaya database not found'
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 200
        
        # Get database file size
        db_size = os.path.getsize(MQTT_SUNDAYA_DB_PATH)
        
        # Connect to database
        conn = sqlite3.connect(MQTT_SUNDAYA_DB_PATH)
        cursor = conn.cursor()
        
        # Get energy stats
        cursor.execute("SELECT COUNT(*) FROM mqtt_energy_summary")
        energy_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT timestamp FROM mqtt_energy_summary ORDER BY timestamp ASC, id ASC LIMIT 1")
        energy_first = cursor.fetchone()
        energy_first_timestamp = energy_first[0] if energy_first else None
        
        cursor.execute("SELECT timestamp FROM mqtt_energy_summary ORDER BY timestamp DESC, id DESC LIMIT 1")
        energy_last = cursor.fetchone()
        energy_last_timestamp = energy_last[0] if energy_last else None
        
        # Get energy message status counts
        cursor.execute("SELECT COUNT(*) FROM mqtt_energy_summary WHERE mqtt_status = 'sent'")
        energy_msg_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mqtt_energy_summary WHERE mqtt_status = 'pending'")
        energy_msg_pending = cursor.fetchone()[0]
        
        # Get battery stats
        cursor.execute("SELECT COUNT(*) FROM mqtt_battery_summary")
        battery_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT timestamp FROM mqtt_battery_summary ORDER BY timestamp ASC, id ASC LIMIT 1")
        battery_first = cursor.fetchone()
        battery_first_timestamp = battery_first[0] if battery_first else None
        
        cursor.execute("SELECT timestamp FROM mqtt_battery_summary ORDER BY timestamp DESC, id DESC LIMIT 1")
        battery_last = cursor.fetchone()
        battery_last_timestamp = battery_last[0] if battery_last else None
        
        # Get battery message status counts
        cursor.execute("SELECT COUNT(*) FROM mqtt_battery_summary WHERE mqtt_status = 'sent'")
        battery_msg_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mqtt_battery_summary WHERE mqtt_status = 'pending'")
        battery_msg_pending = cursor.fetchone()[0]
        
        # Get today's records (convert to DB timestamp format)
        today = datetime.now().strftime('%Y-%m-%d')
        today_start = _date_to_db_ts_start(today)
        today_end = _date_to_db_ts_end(today)
        cursor.execute("SELECT COUNT(*) FROM mqtt_energy_summary WHERE timestamp >= ? AND timestamp <= ?", 
                      (today_start, today_end))
        energy_today = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mqtt_battery_summary WHERE timestamp >= ? AND timestamp <= ?", 
                      (today_start, today_end))
        battery_today = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_records': energy_total + battery_total,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / 1024 / 1024, 2),
                'energy': {
                    'total_records': energy_total,
                    'today_records': energy_today,
                    'first_record_timestamp': energy_first_timestamp,
                    'last_record_timestamp': energy_last_timestamp,
                    'total_msg_sent': energy_msg_sent,
                    'total_msg_pending': energy_msg_pending
                },
                'battery': {
                    'total_records': battery_total,
                    'today_records': battery_today,
                    'first_record_timestamp': battery_first_timestamp,
                    'last_record_timestamp': battery_last_timestamp,
                    'total_msg_sent': battery_msg_sent,
                    'total_msg_pending': battery_msg_pending
                }
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except sqlite3.Error as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@service_bp.route('/mqtt-sundaya/info', methods=['GET'])
def get_mqtt_sundaya_info():
    """
    Get MQTT Sundaya service information and available endpoints
    """
    return jsonify({
        'status': 'success',
        'data': {
            'service': 'MQTT Sundaya Loggers Monitoring API',
            'description': 'API endpoints for monitoring MQTT Sundaya service logs and data (sundaya_broker)',
            'endpoints': {
                'logs': {
                    'path': '/api/v1/service/mqtt-sundaya/logs',
                    'method': 'GET',
                    'description': 'Get MQTT Sundaya logs from log files',
                    'parameters': {
                        'log_type': 'mqtt_sundaya_all.log | mqtt_sundaya_errors.log | mqtt_sundaya_warnings.log',
                        'lines': 'number of lines (max 1000)',
                        'reverse': 'true/false for reverse order'
                    }
                },
                'download_logs': {
                    'path': '/api/v1/service/mqtt-sundaya/logs/download',
                    'method': 'GET',
                    'description': 'Download MQTT Sundaya logs as file',
                    'parameters': {
                        'log_type': 'mqtt_sundaya_all.log | mqtt_sundaya_errors.log | mqtt_sundaya_warnings.log',
                        'lines': 'number of lines (max 5000)'
                    }
                },
                'energy_summary': {
                    'path': '/api/v1/service/mqtt-sundaya/energy/summary',
                    'method': 'GET',
                    'description': 'Get MQTT energy summary data from database',
                    'parameters': {
                        'limit': 'number of records (max 500)',
                        'order': 'asc/desc',
                        'start_date': 'YYYY-MM-DD',
                        'end_date': 'YYYY-MM-DD'
                    }
                },
                'battery_summary': {
                    'path': '/api/v1/service/mqtt-sundaya/battery/summary',
                    'method': 'GET',
                    'description': 'Get MQTT battery summary data from database',
                    'parameters': {
                        'limit': 'number of records (max 500)',
                        'order': 'asc/desc',
                        'start_date': 'YYYY-MM-DD',
                        'end_date': 'YYYY-MM-DD'
                    }
                },
                'latest_energy': {
                    'path': '/api/v1/service/mqtt-sundaya/energy/latest',
                    'method': 'GET',
                    'description': 'Get latest MQTT energy data for monitoring'
                },
                'latest_battery': {
                    'path': '/api/v1/service/mqtt-sundaya/battery/latest',
                    'method': 'GET',
                    'description': 'Get latest MQTT battery data for monitoring'
                },
                'stats': {
                    'path': '/api/v1/service/mqtt-sundaya/stats',
                    'method': 'GET',
                    'description': 'Get MQTT Sundaya database statistics'
                },
                'info': {
                    'path': '/api/v1/service/mqtt-sundaya/info',
                    'method': 'GET',
                    'description': 'Get MQTT Sundaya service information'
                }
            },
            'log_files': list(MQTT_SUNDAYA_LOG_PATHS.keys()),
            'database_path': MQTT_SUNDAYA_DB_PATH,
            'tables': ['mqtt_energy_summary', 'mqtt_battery_summary'],
            'broker': 'sundaya_broker'
        },
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200


