"""
Logger API for JSPro PowerDesk
Handles historical data logs
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import json
import os
import sys
from functools import wraps
from ..redisconnection import connection as red
from .helper import *
from helpers.system_resources_helper import get_disk_detail
from config import PATH, scc_type

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from security_middleware import api_session_required
except ImportError:
    # Fallback decorator if security middleware is not available
    def api_session_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function

# Create blueprint
logger_bp = Blueprint('logger', __name__)

# ============== Configuration & Helper Functions ===========================

# Log type mapping configuration
LOG_TYPE_CONFIG = {
    'battery': {
        'redis_stream': 'stream:battery',
        'sqlite_table': 'loggers_battery',
        'description': 'Battery monitoring logs'
    },
    'scc': {
        'redis_stream': 'stream:scc',
        'sqlite_table': 'loggers_scc',
        'description': 'Energy/SCC monitoring logs'
    },
    'bakti_mqtt': {
        'redis_stream': None,  # No Redis stream for bakti_mqtt
        'sqlite_table': 'loggers_bakti_mqtt',
        'description': 'Bakti MQTT publisher logs'
    }
}

def get_site_info():
    """Get site information from Redis"""
    try:
        # Get raw data from Redis
        site_information_raw = red.hget('device_config', 'site_information')
        ip_configuration_raw = red.hget('device_config', 'ip_configuration')
        
        # Default values
        site_id = 'UNKNOWN'
        site_name = 'UNKNOWN SITE'
        ip_address = '0.0.0.0'
        
        # Parse site information
        if site_information_raw:
            try:
                if isinstance(site_information_raw, bytes):
                    site_information_raw = site_information_raw.decode('utf-8')
                site_information = json.loads(site_information_raw)
                site_id = site_information.get('site_id', 'UNKNOWN')
                site_name = site_information.get('site_name', 'UNKNOWN SITE')
            except (json.JSONDecodeError, AttributeError) as e:
                pass  # Keep default values
        
        # Parse IP configuration
        if ip_configuration_raw:
            try:
                if isinstance(ip_configuration_raw, bytes):
                    ip_configuration_raw = ip_configuration_raw.decode('utf-8')
                ip_configuration = json.loads(ip_configuration_raw)
                ip_address = ip_configuration.get('ip_address', '0.0.0.0')
            except (json.JSONDecodeError, AttributeError) as e:
                pass  # Keep default value
        
        return {
            'site_id': site_id,
            'site_name': site_name,
            'ip_address': ip_address
        }
    except Exception as e:
        # Fallback jika Redis tidak tersedia atau error lainnya
        return {
            'site_id': 'UNKNOWN',
            'site_name': 'UNKNOWN SITE',
            'ip_address': '0.0.0.0'
        }

def validate_log_type(log_type):
    """Validate if log_type is supported"""
    return log_type in LOG_TYPE_CONFIG

def get_stream_name(log_type):
    """Get Redis stream name for log type"""
    if not validate_log_type(log_type):
        return None
    return LOG_TYPE_CONFIG[log_type]['redis_stream']

def get_table_name(log_type):
    """Get SQLite table name for log type"""
    if not validate_log_type(log_type):
        return None
    return LOG_TYPE_CONFIG[log_type]['sqlite_table']

def get_redis_stream_size(stream_name):
    """Get Redis stream size in KB"""
    try:
        # Get memory usage of the key
        memory_bytes = red.memory_usage(stream_name)
        if memory_bytes:
            return round(memory_bytes / 1024, 2)  # Convert to KB
        return 0
    except Exception:
        return 0

def get_redis_stream_stats(stream_name):
    """Get Redis stream statistics"""
    try:
        # Get stream info
        stream_info = red.xinfo_stream(stream_name)
        total_records = stream_info['length']
        
        # Get first and last timestamps
        first_timestamp = None
        last_timestamp = None
        
        if total_records > 0:
            # Get first entry
            first_entry = red.xrange(stream_name, count=1)
            if first_entry:
                first_fields = dict(first_entry[0][1])
                ts_field = first_fields.get(b'timestamp') or first_fields.get('timestamp', '')
                if isinstance(ts_field, bytes):
                    ts_field = ts_field.decode('utf-8')
                first_timestamp = ts_field
            
            # Get last entry
            last_entry = red.xrevrange(stream_name, count=1)
            if last_entry:
                last_fields = dict(last_entry[0][1])
                ts_field = last_fields.get(b'timestamp') or last_fields.get('timestamp', '')
                if isinstance(ts_field, bytes):
                    ts_field = ts_field.decode('utf-8')
                last_timestamp = ts_field
        
        return {
            'total_records': total_records,
            'key_size': get_redis_stream_size(stream_name),
            'key_size_unit': 'KB',
            'first_timestamp': first_timestamp,
            'last_timestamp': last_timestamp
        }
    except Exception:
        return {
            'total_records': 0,
            'key_size': 0,
            'key_size_unit': 'KB',
            'first_timestamp': None,
            'last_timestamp': None
        }

def get_sqlite_table_stats(table_name, db_path=None):
    """Get SQLite table statistics
    
    Parameters:
    - table_name: Name of the table
    - db_path: Optional database path. If None, uses default SQLITE_DB_PATH
    """
    try:
        conn = get_sqlite_connection(db_path)
        if not conn:
            return {
                'total_records': 0,
                'first_timestamp': None,
                'last_timestamp': None
            }
        
        # Get total records
        cursor = conn.execute(f"SELECT COUNT(*) as total FROM {table_name}")
        total_records = cursor.fetchone()['total']
        
        # Get first and last timestamps
        first_timestamp = None
        last_timestamp = None
        
        if total_records > 0:
            # Get first timestamp
            cursor = conn.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp ASC LIMIT 1")
            first_row = cursor.fetchone()
            if first_row:
                first_timestamp = first_row['timestamp']
            
            # Get last timestamp
            cursor = conn.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
            last_row = cursor.fetchone()
            if last_row:
                last_timestamp = last_row['timestamp']
        
        conn.close()
        
        return {
            'total_records': total_records,
            'first_timestamp': first_timestamp,
            'last_timestamp': last_timestamp
        }
    except Exception:
        return {
            'total_records': 0,
            'first_timestamp': None,
            'last_timestamp': None
        }

def format_response_data(data):
    """
    Format response data to ensure proper types (arrays vs numeric)
    Handles JSON string arrays and converts them to proper arrays
    
    Args:
        data: Response data to format
        
    Returns:
        dict: Formatted data with proper types
    """
    import json
    
    if isinstance(data, dict):
        formatted = {}
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                # Keep arrays as arrays
                formatted[key] = list(value)
            elif isinstance(value, str):
                # Check if string is a JSON array
                if value.strip().startswith('[') and value.strip().endswith(']'):
                    try:
                        # Parse JSON array string to actual array
                        parsed_array = json.loads(value)
                        if isinstance(parsed_array, list):
                            formatted[key] = parsed_array
                        else:
                            formatted[key] = value
                    except (json.JSONDecodeError, ValueError):
                        # If JSON parsing fails, check if it's a numeric string
                        if value.replace('.', '').replace('-', '').isdigit():
                            if '.' in value:
                                try:
                                    formatted[key] = float(value)
                                except ValueError:
                                    formatted[key] = value
                            else:
                                try:
                                    formatted[key] = int(value)
                                except ValueError:
                                    formatted[key] = value
                        else:
                            formatted[key] = value
                # Check if string is a numeric value
                elif value.replace('.', '').replace('-', '').isdigit():
                    if '.' in value:
                        try:
                            formatted[key] = float(value)
                        except ValueError:
                            formatted[key] = value
                    else:
                        try:
                            formatted[key] = int(value)
                        except ValueError:
                            formatted[key] = value
                else:
                    formatted[key] = value
            elif isinstance(value, dict):
                # Recursively format nested dictionaries
                formatted[key] = format_response_data(value)
            elif isinstance(value, list):
                # Recursively format list items
                formatted[key] = [format_response_data(item) if isinstance(item, dict) else item for item in value]
            else:
                formatted[key] = value
        return formatted
    else:
        return data

# ============== Storage Overview Endpoint ===========================

@logger_bp.route('/data/overview', methods=['GET'])
@api_session_required
def get_storage_overview():
    """
    Get comprehensive storage overview and statistics
    Returns detailed statistics for Redis streams and SQLite tables
    """
    try:
        overview_data = {
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "storage_overview": {
                "disk_usage": {
                    "used": 0.0,
                    "free": 0.0,
                    "total": 0.0,
                    "unit": "GB",
                    "usage_percentage": 0.0
                },
                "redis": {
                    "size": 0.0,
                    "unit": "MB"
                },
                "sqlite": {
                    "size": 0.0,
                    "unit": "MB"
                }
            },
            "data_statistics": {
                "redis": {},
                "sqlite": {}
            }
        }

        # Get disk usage
        try:
            disk = get_disk_detail()
            used_gb = round(disk.used / (1024**3), 1)
            free_gb = round(disk.free / (1024**3), 1)
            total_gb = round(disk.total / (1024**3), 1)
            usage_percentage = round((disk.used / disk.total) * 100, 2) if disk.total > 0 else 0
            
            overview_data["storage_overview"]["disk_usage"] = {
                "used": used_gb,
                "free": free_gb,
                "total": total_gb,
                "unit": "GB",
                "usage_percentage": usage_percentage
            }
        except Exception:
            pass

        # Get Redis statistics
        if red:
            try:
                # Get Redis total memory usage
                redis_info = red.info('memory')
                redis_used_memory = redis_info.get('used_memory', 0)
                redis_storage_mb = round(redis_used_memory / (1024 * 1024), 2)
                overview_data["storage_overview"]["redis"]["size"] = redis_storage_mb
                
                # Get statistics for each Redis stream
                redis_stats = {}
                for log_type, config in LOG_TYPE_CONFIG.items():
                    stream_name = config['redis_stream']
                    if stream_name:  # Only if Redis stream exists
                        try:
                            redis_stats[stream_name] = get_redis_stream_stats(stream_name)
                        except Exception:
                            pass
                
                overview_data["data_statistics"]["redis"] = redis_stats
            except Exception:
                pass

        # Get SQLite statistics
        try:
            # Get SQLite database file size (sum of all databases)
            sqlite_db_path = f'{PATH}/database/data_storage.db'
            sqlite_total_size = 0
            if os.path.exists(sqlite_db_path):
                sqlite_total_size += os.path.getsize(sqlite_db_path)
            
            # Add bakti_mqtt.db size if it exists
            if os.path.exists(SQLITE_DB_PATH_BAKTI_MQTT):
                sqlite_total_size += os.path.getsize(SQLITE_DB_PATH_BAKTI_MQTT)
            
            sqlite_storage_mb = round(sqlite_total_size / (1024 * 1024), 2)
            overview_data["storage_overview"]["sqlite"]["size"] = sqlite_storage_mb
            
            # Get statistics for each SQLite table
            sqlite_stats = {}
            for log_type, config in LOG_TYPE_CONFIG.items():
                table_name = config['sqlite_table']
                if table_name:
                    try:
                        # Use bakti_mqtt.db for bakti_mqtt log type
                        db_path = SQLITE_DB_PATH_BAKTI_MQTT if log_type == 'bakti_mqtt' else None
                        sqlite_stats[table_name] = get_sqlite_table_stats(table_name, db_path)
                    except Exception:
                        pass
            
            overview_data["data_statistics"]["sqlite"] = sqlite_stats
        except Exception:
            pass

        return jsonify({
            "status": "success",
            "status_code": 200,
            "data": overview_data
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "status_code": 500,
            "message": "Failed to get storage overview",
            "error": str(e)
        }), 500


# ============== Unified Logs Endpoints ===========================

def get_redis_logs_handler(log_type, limit, offset, start_date, end_date):
    """
    Handler function for getting logs from Redis stream
    Returns formatted response with site_info, page_info, and data
    """
    try:
        stream_name = get_stream_name(log_type)
        if not stream_name:
            return {
                'status': 'error',
                'status_code': 400,
                'message': f'Redis stream not available for log_type: {log_type}'
            }
        
        # Validate dates
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            return {
                'status': 'error',
                'status_code': 400,
                'message': 'Invalid start_date format'
            }
        
        if end_date and end_dt is False:
            return {
                'status': 'error',
                'status_code': 400,
                'message': 'Invalid end_date format'
            }
        
        # Convert datetime to Redis timestamp format
        redis_start_ts = convert_to_redis_timestamp_format(start_dt) if start_dt else None
        redis_end_ts = convert_to_redis_timestamp_format(end_dt) if end_dt else None
        
        # Process Redis stream
        stream_result = process_redis_stream(stream_name, start_dt, end_dt, redis_start_ts, redis_end_ts, False, {})
        all_records = stream_result['records']
        
        # Sort by timestamp (newest first)
        if all_records:
            all_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Paginate results
        paginated_data = paginate_data(all_records, limit, offset)
        
        # Format response data
        formatted_records = [format_response_data(record) for record in paginated_data['records']]
        
        # Get stream statistics
        stream_stats = get_redis_stream_stats(stream_name)
        
        return {
            'status': 'success',
            'status_code': 200,
            'site_info': get_site_info(),
            'page_info': paginated_data['page_info'],
            'data': {
                'statistics': stream_stats,
                'logs': formatted_records
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'status_code': 500,
            'message': f'Failed to retrieve Redis logs: {str(e)}'
        }


def get_sqlite_logs_handler(log_type, limit, offset, start_date, end_date):
    """
    Handler function for getting logs from SQLite table
    Returns formatted response with site_info, page_info, and data
    """
    try:
        table_name = get_table_name(log_type)
        if not table_name:
            return {
                'status': 'error',
                'status_code': 400,
                'message': f'SQLite table not available for log_type: {log_type}'
            }
        
        # Use bakti_mqtt.db for bakti_mqtt log type
        db_path = SQLITE_DB_PATH_BAKTI_MQTT if log_type == 'bakti_mqtt' else None
        conn = get_sqlite_connection(db_path)
        if not conn:
            return {
                'status': 'error',
                'status_code': 503,
                'message': 'SQLite database unavailable'
            }
        
        # Validate dates
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            conn.close()
            return {
                'status': 'error',
                'status_code': 400,
                'message': 'Invalid start_date format'
            }
        
        if end_date and end_dt is False:
            conn.close()
            return {
                'status': 'error',
                'status_code': 400,
                'message': 'Invalid end_date format'
            }
        
        # Process SQLite data
        result = process_sqlite_data(conn, start_dt, end_dt, table_name, limit, offset, False)
        
        conn.close()
        
        if "error" in result:
            return {
                'status': 'error',
                'status_code': 500,
                'message': f'Failed to retrieve SQLite logs: {result["error"]}'
            }
        
        # Format response data
        formatted_records = [format_response_data(record) for record in result["records"]]
        
        # Paginate results
        paginated_data = paginate_data(result["records"], limit, offset)
        
        # Get table statistics (use same db_path)
        table_stats = get_sqlite_table_stats(table_name, db_path)
        
        return {
            'status': 'success',
            'status_code': 200,
            'site_info': get_site_info(),
            'page_info': paginated_data['page_info'],
            'data': {
                'statistics': table_stats,
                'logs': formatted_records
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'status_code': 500,
            'message': f'Failed to retrieve SQLite logs: {str(e)}'
        }


@logger_bp.route('/data/logs/<log_type>', methods=['GET'])
@api_session_required
def get_unified_logs(log_type):
    """
    Unified endpoint for getting logs from Redis or SQLite
    
    Path parameters:
    - log_type: 'battery' | 'scc' | 'bakti_mqtt'
    
    Query parameters:
    - source: 'redis' | 'sqlite' (default: 'redis' for battery/scc, 'sqlite' for bakti_mqtt)
    - limit: Maximum records (default: 1000, max: 10000)
    - offset: Records to skip (default: 0)
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)
    """
    try:
        # Validate log_type
        if not validate_log_type(log_type):
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": f"Invalid log_type. Valid types: {', '.join(LOG_TYPE_CONFIG.keys())}"
            }), 400
        
        # Parse query parameters
        source = request.args.get('source', 'redis' if log_type != 'bakti_mqtt' else 'sqlite')
        limit = min(int(request.args.get('limit', 1000)), 10000)
        offset = int(request.args.get('offset', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Route to appropriate handler
        if source == 'redis':
            result = get_redis_logs_handler(log_type, limit, offset, start_date, end_date)
        elif source == 'sqlite':
            result = get_sqlite_logs_handler(log_type, limit, offset, start_date, end_date)
        else:
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Invalid source. Must be 'redis' or 'sqlite'"
            }), 400
        
        status_code = result.pop('status_code', 200)
        return jsonify(result), status_code
        
    except ValueError as e:
        return jsonify({
            "status": "error",
            "status_code": 400,
            "message": "Invalid parameter value",
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "status_code": 500,
            "message": "Failed to retrieve logs",
            "error": str(e)
        }), 500


@logger_bp.route('/data/logs/<log_type>/<timestamp>', methods=['DELETE'])
@api_session_required
def delete_logs_by_timestamp(log_type, timestamp):
    """
    Delete logs by timestamp from Redis or SQLite
    
    Path parameters:
    - log_type: 'battery' | 'scc' | 'bakti_mqtt'
    - timestamp: Timestamp to delete
    
    Query parameters:
    - source: 'redis' | 'sqlite' (required)
    - match_type: 'exact' | 'prefix' (default: 'exact')
    """
    try:
        # Validate log_type
        if not validate_log_type(log_type):
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": f"Invalid log_type. Valid types: {', '.join(LOG_TYPE_CONFIG.keys())}"
            }), 400
        
        # Get query parameters
        source = request.args.get('source')
        match_type = request.args.get('match_type', 'exact').lower()
        
        # Validate source
        if not source or source not in ['redis', 'sqlite']:
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Parameter 'source' is required. Must be 'redis' or 'sqlite'"
            }), 400
        
        # Validate match_type
        if match_type not in ['exact', 'prefix']:
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Invalid match_type. Must be 'exact' or 'prefix'"
            }), 400
        
        # Validate timestamp format
        if not timestamp or len(timestamp) < 8:
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Invalid timestamp format. Timestamp too short."
            }), 400
        
        # Handle Redis deletion
        if source == 'redis':
            stream_name = get_stream_name(log_type)
            if not stream_name:
                return jsonify({
                    "status": "error",
                    "status_code": 400,
                    "message": f"Redis stream not available for log_type: {log_type}"
                }), 400
            
            if not red:
                return jsonify({
                    "status": "error",
                    "status_code": 503,
                    "message": "Redis service unavailable"
                }), 503
            
            # Delete from Redis stream
            result = delete_entries_by_timestamp_section(red, timestamp, match_type, [stream_name], False)
            
            if "error" in result:
                return jsonify({
                    "status": "error",
                    "status_code": 500,
                    "message": "Failed to delete Redis stream data by timestamp",
                    "error": result["error"]
                }), 500
            
            if not result.get("timestamp_exists", False):
                return jsonify({
                    "status": "error",
                    "status_code": 404,
                    "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in Redis stream ({stream_name})",
                    "data": {
                        "streams_deleted": result.get("streams_deleted", {}),
                        "total_deleted": 0,
                        "timestamp_exists": False
                    }
                }), 404
            
            return jsonify({
                "status": "success",
                "status_code": 200,
                "message": f"Successfully deleted {result['total_deleted']} entries with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}' from stream ({stream_name})",
                "data": {
                    "streams_deleted": result.get("streams_deleted", {}),
                    "total_deleted": result["total_deleted"],
                    "timestamp_exists": result["timestamp_exists"]
                }
            }), 200
        
        # Handle SQLite deletion
        elif source == 'sqlite':
            table_name = get_table_name(log_type)
            if not table_name:
                return jsonify({
                    "status": "error",
                    "status_code": 400,
                    "message": f"SQLite table not available for log_type: {log_type}"
                }), 400
            
            # Use bakti_mqtt.db for bakti_mqtt log type
            db_path = SQLITE_DB_PATH_BAKTI_MQTT if log_type == 'bakti_mqtt' else None
            conn = get_sqlite_connection(db_path)
            if not conn:
                return jsonify({
                    "status": "error",
                    "status_code": 503,
                    "message": "SQLite database unavailable"
                }), 503
            
            # Delete from SQLite
            result = delete_sqlite_by_timestamp(conn, timestamp, table_name, match_type, False)
            conn.close()
            
            if "error" in result:
                return jsonify({
                    "status": "error",
                    "status_code": 500,
                    "message": "Failed to delete SQLite data by timestamp",
                    "error": result["error"]
                }), 500
            
            if not result.get("timestamp_exists", False):
                return jsonify({
                    "status": "error",
                    "status_code": 404,
                    "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in table '{table_name}'",
                    "data": {
                        "deleted_count": 0,
                        "timestamp_exists": False,
                        "table_name": table_name
                    }
                }), 404
            
            return jsonify({
                "status": "success",
                "status_code": 200,
                "message": f"Successfully deleted {result['deleted_count']} records with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}' from table '{table_name}'",
                "data": {
                    "deleted_count": result["deleted_count"],
                    "timestamp_exists": result["timestamp_exists"],
                    "table_name": table_name
                }
            }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "status_code": 500,
            "message": "Failed to delete logs by timestamp",
            "error": str(e)
        }), 500


@logger_bp.route('/data/logs/<log_type>', methods=['DELETE'])
@api_session_required
def delete_all_logs(log_type):
    """
    Bulk delete all logs from Redis or SQLite
    
    Path parameters:
    - log_type: 'battery' | 'scc' | 'bakti_mqtt'
    
    Query parameters:
    - source: 'redis' | 'sqlite' (required)
    - confirm: Must be 'yes' to confirm deletion (required)
    """
    try:
        # Validate log_type
        if not validate_log_type(log_type):
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": f"Invalid log_type. Valid types: {', '.join(LOG_TYPE_CONFIG.keys())}"
            }), 400
        
        # Get query parameters
        source = request.args.get('source')
        confirm = request.args.get('confirm', '').lower()
        
        # Validate source
        if not source or source not in ['redis', 'sqlite']:
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Parameter 'source' is required. Must be 'redis' or 'sqlite'"
            }), 400
        
        # Require confirmation
        if confirm != 'yes':
            return jsonify({
                "status": "error",
                "status_code": 400,
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all data."
            }), 400
        
        # Handle Redis bulk deletion
        if source == 'redis':
            stream_name = get_stream_name(log_type)
            if not stream_name:
                return jsonify({
                    "status": "error",
                    "status_code": 400,
                    "message": f"Redis stream not available for log_type: {log_type}"
                }), 400
            
            if not red:
                return jsonify({
                    "status": "error",
                    "status_code": 503,
                    "message": "Redis service unavailable"
                }), 503
            
            try:
                # Check if stream exists and get its length
                stream_info = red.xinfo_stream(stream_name)
                stream_length = stream_info['length']
                
                # Delete the entire stream
                deleted = red.delete(stream_name)
                total_deleted = stream_length if deleted else 0
                
                return jsonify({
                    "status": "success",
                    "status_code": 200,
                    "message": f"Successfully deleted {total_deleted} entries from Redis stream ({stream_name})",
                    "data": {
                        "stream_name": stream_name,
                        "total_deleted": total_deleted
                    }
                }), 200
            except Exception as e:
                # Stream doesn't exist or error
                return jsonify({
                    "status": "success",
                    "status_code": 200,
                    "message": f"Redis stream ({stream_name}) is already empty or doesn't exist",
                    "data": {
                        "stream_name": stream_name,
                        "total_deleted": 0
                    }
                }), 200
        
        # Handle SQLite bulk deletion
        elif source == 'sqlite':
            table_name = get_table_name(log_type)
            if not table_name:
                return jsonify({
                    "status": "error",
                    "status_code": 400,
                    "message": f"SQLite table not available for log_type: {log_type}"
                }), 400
            
            # Use bakti_mqtt.db for bakti_mqtt log type
            db_path = SQLITE_DB_PATH_BAKTI_MQTT if log_type == 'bakti_mqtt' else None
            conn = get_sqlite_connection(db_path)
            if not conn:
                return jsonify({
                    "status": "error",
                    "status_code": 503,
                    "message": "SQLite database unavailable"
                }), 503
            
            try:
                # Get count before deletion
                cursor = conn.execute(f"SELECT COUNT(*) as total FROM {table_name}")
                total_before = cursor.fetchone()['total']
                
                if total_before == 0:
                    conn.close()
                    return jsonify({
                        "status": "success",
                        "status_code": 200,
                        "message": f"Table '{table_name}' is already empty",
                        "data": {
                            "table_name": table_name,
                            "deleted_count": 0
                        }
                    }), 200
                
                # Delete all records
                cursor = conn.execute(f"DELETE FROM {table_name}")
                conn.commit()
                deleted_count = cursor.rowcount
                conn.close()
                
                return jsonify({
                    "status": "success",
                    "status_code": 200,
                    "message": f"Successfully deleted all {deleted_count} records from table '{table_name}'",
                    "data": {
                        "table_name": table_name,
                        "deleted_count": deleted_count,
                        "records_before_deletion": total_before
                    }
                }), 200
            except Exception as e:
                conn.close()
                return jsonify({
                    "status": "error",
                    "status_code": 500,
                    "message": f"Failed to delete all data from table '{table_name}'",
                    "error": str(e)
                }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "status_code": 500,
            "message": "Failed to delete all logs",
            "error": str(e)
        }), 500


# ============== SCC Alarm Log Endpoints ===========================

@logger_bp.route('/scc-alarm/overview', methods=['GET'])
@api_session_required
def get_scc_alarm_overview():
    """Get SCC alarm log overview from Redis Stream"""
    try:
        total_alarms = 0
        active_alarms = 0
        last_alarm_time = None
        alarm_types = {}
        severity_count = {
            'critical': 0,
            'warning': 0,
            'normal': 0
        }
        
        # Get alarm count and statistics from Redis Stream
        if red:
            try:
                # Check if stream exists
                stream_info = red.xinfo_stream('stream:scc-logs')
                total_alarms = stream_info['length']
                
                # Get recent entries to analyze patterns (last 100 entries)
                recent_entries = red.xrevrange('stream:scc-logs', '+', '-', count=100)
                
                for entry_id, fields in recent_entries:
                    try:
                        # Parse timestamp from entry ID (handle both bytes and string formats)
                        if isinstance(entry_id, bytes):
                            entry_id_str = entry_id.decode('utf-8')
                        else:
                            entry_id_str = str(entry_id)
                        
                        # Extract timestamp from Redis Stream ID format (timestamp-sequence)
                        try:
                            timestamp_ms = int(entry_id_str.split('-')[0])
                            entry_time = datetime.fromtimestamp(timestamp_ms / 1000)
                            
                            # Track the latest alarm time
                            if not last_alarm_time or entry_time > last_alarm_time:
                                last_alarm_time = entry_time
                        except (ValueError, IndexError):
                            # If timestamp parsing fails, skip this entry
                            continue
                        
                        # Parse alarm data if available (handle both bytes and string formats)
                        data_field = fields.get('data')
                        
                        if data_field:
                            import json
                            # Handle both decoded string and bytes format
                            if isinstance(data_field, bytes):
                                alarm_data = json.loads(data_field.decode())
                            else:
                                alarm_data = json.loads(data_field)
                            
                            # Count different alarm types and severities based on SCC type
                            for scc_id, scc_data in alarm_data.items():
                                if isinstance(scc_data, dict) and 'alarm' in scc_data:
                                    alarm_obj = scc_data['alarm']
                                    
                                    if alarm_obj:
                                        has_active_alarm = False
                                        
                                        # Process based on SCC type
                                        if scc_type == 'scc-srne':
                                            # Handle SRNE format: check fault values for 1
                                            if 'fault' in alarm_obj and isinstance(alarm_obj['fault'], dict):
                                                for fault_type, fault_value in alarm_obj['fault'].items():
                                                    # Count all fault types
                                                    if fault_type not in alarm_types:
                                                        alarm_types[fault_type] = 0
                                                    
                                                    # Check if alarm is active (value = 1)
                                                    if fault_value == 1:
                                                        alarm_types[fault_type] += 1
                                                        has_active_alarm = True
                                                        # All SRNE faults are critical
                                                        severity_count['critical'] += 1
                                                    else:
                                                        # Count normal status
                                                        severity_count['normal'] += 1
                                        
                                        elif scc_type == 'scc-epever':
                                            # Handle EPEVER format: nested categories with status values
                                            for category, category_alarms in alarm_obj.items():
                                                if isinstance(category_alarms, dict):
                                                    # Process each alarm within the category
                                                    for alarm_type, alarm_status in category_alarms.items():
                                                        # Count alarm types with category prefix
                                                        full_alarm_type = f"{category}.{alarm_type}"
                                                        if full_alarm_type not in alarm_types:
                                                            alarm_types[full_alarm_type] = 0
                                                        
                                                        # Always count for total statistics
                                                        alarm_types[full_alarm_type] += 1
                                                        
                                                        # Check if this is an active alarm (not 'normal' or 'running')
                                                        # Include 'standby' and 'light_load' as informational states
                                                        if alarm_status not in ['normal', 'running']:
                                                            has_active_alarm = True
                                                            
                                                            # Categorize by severity based on alarm status
                                                            if alarm_status in ['critical', 'fault', 'overvoltage', 'undervoltage', 'short_circuit', 'overload', 'high_voltage', 'wrong', 'overtemp', 'overdischarge', 'stop_discharging', 'discharge_short']:
                                                                severity_count['critical'] += 1
                                                            elif alarm_status in ['warning', 'no_charging', 'unrecognized', 'abnormal', 'low_voltage', 'lowtemp', 'light_load', 'boost', 'standby']:
                                                                severity_count['warning'] += 1
                                                            else:
                                                                severity_count['warning'] += 1  # Default to warning for unknown non-normal status
                                                        else:
                                                            # Count normal status
                                                            severity_count['normal'] += 1
                                        
                                        # Only count as active alarm if there are non-normal statuses
                                        if has_active_alarm:
                                            active_alarms += 1
                                                
                    except Exception as e:
                        continue
                        
            except Exception:
                # Stream doesn't exist yet
                total_alarms = 0

        overview_data = {
            "scc_type": scc_type,
            "total_alarms": total_alarms,
            "active_alarms": active_alarms,
            "last_alarm_time": last_alarm_time.strftime("%Y-%m-%d %H:%M:%S") if last_alarm_time else None,
            "alarm_statistics": {
                "severity_breakdown": severity_count,
                "top_alarm_types": dict(sorted(alarm_types.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": overview_data
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to get SCC alarm overview",
            "error": str(e)
        }), 500


@logger_bp.route('/scc-alarm', methods=['GET'])
@api_session_required
def download_scc_alarms():
    """
    Download all SCC alarm logs from Redis Stream
    Query parameters:
    - limit: Maximum records to download (default: 1000, max: 5000)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Parse query parameters
        limit = min(int(request.args.get('limit', 1000)), 5000)

        # Get all SCC logs from Redis Stream
        try:
            entries = red.xrevrange('stream:scc-logs', count=limit)
        except Exception:
            # Stream doesn't exist
            entries = []

        all_logs = []
        for entry_id, fields in entries:
            try:
                # Decode entry data (handle both bytes and string formats)
                timestamp_field = fields.get('timestamp') or fields.get(b'timestamp', b'')
                timestamp = timestamp_field.decode('utf-8') if isinstance(timestamp_field, bytes) else str(timestamp_field) if timestamp_field else ''
                # using timestamp from entry ID for accuracy
                if isinstance(entry_id, bytes):
                    entry_id_str = entry_id.decode('utf-8')
                else:
                    entry_id_str = str(entry_id)
                try:
                    timestamp_ms = int(entry_id_str.split('-')[0])
                    entry_time = datetime.fromtimestamp(timestamp_ms / 1000)
                    human_readable_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, IndexError):
                    print('fallback timestamp')
                    human_readable_time = timestamp  # Fallback to stored timestamp if parsing fails
                
                data_field = fields.get('data') or fields.get(b'data', b'')
                data_json = data_field.decode('utf-8') if isinstance(data_field, bytes) else str(data_field) if data_field else ''
                
                # Parse SCC data
                import json
                scc_data = json.loads(data_json) if data_json else {}
                
                # Format log entry
                log_entry = {
                    'timestamp': human_readable_time,
                    'scc_data': scc_data
                }
                
                all_logs.append(log_entry)
                
            except Exception as e:
                continue

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "logs": all_logs,
                "total_logs": len(all_logs),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to download SCC alarm logs",
            "error": str(e)
        }), 500


@logger_bp.route('/scc-alarm', methods=['DELETE'])
@api_session_required
def clear_scc_alarms():
    """
    Clear all SCC alarm logs from Redis Stream
    
    Query parameters:
    - confirm: Must be 'yes' to confirm deletion (required)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Get query parameters
        confirm = request.args.get('confirm', '').lower()
        
        # Require confirmation for safety
        if confirm != 'yes':
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Deletion requires confirmation. Add '?confirm=yes' to proceed."
            }), 400

        # Get count before deletion
        deleted_count = 0
        try:
            stream_info = red.xinfo_stream('stream:scc-logs')
            deleted_count = stream_info['length']
            # Delete the entire stream
            red.delete('stream:scc-logs')
        except Exception:
            # Stream doesn't exist
            deleted_count = 0

        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": f"Successfully cleared {deleted_count} SCC alarm logs",
            "data": {
                "deleted_count": deleted_count,
                "stream_name": "stream:scc-logs",
                "cleared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to clear SCC alarm logs",
            "error": str(e)
        }), 500
