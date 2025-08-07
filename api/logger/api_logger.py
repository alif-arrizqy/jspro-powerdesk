"""
Logger API Blueprint for JSPro PowerDesk
Handles historical data logs from Redis and SQLite storage
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import json
import os
import sys
import shutil
from functools import wraps
from ..redisconnection import connection as red
from .helper import *
from functions import get_disk_detail
from config import PATH

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

# ============== Redis Data Endpoints ===========================

@logger_bp.route('/data/redis', methods=['GET'])
@api_session_required
def get_redis_data():
    """
    Get historical data from Redis with filtering options
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)  
    - limit: Maximum records (default: 55)
    - offset: Records to skip (default: 0)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable",
                "error": "Cannot connect to Redis database"
            }), 503

        # Parse query parameters with smart defaults
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Smart limit handling: smaller default when no date filter to prevent memory issues
        default_limit = 55 if (start_date or end_date) else 22
        limit = min(int(request.args.get('limit', default_limit)), 11000)  # Max 11000 records
        offset = int(request.args.get('offset', 0))
        debug_mode = request.args.get('debug', 'false').lower() == 'true'

        # Validate dates first
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid start_date format",
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400
            
        if end_date and end_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error", 
                "message": "Invalid end_date format",
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400

        # Convert datetime to Redis timestamp format for comparison
        redis_start_ts = convert_to_redis_timestamp_format(start_dt) if start_dt else None
        redis_end_ts = convert_to_redis_timestamp_format(end_dt) if end_dt else None

        # Minimal debug info collection (only when needed)
        debug_info = {
            "redis_connection": "OK",
            "processing_steps": [] if debug_mode else None,
            "raw_data_found": {},
            "filter_results": {}
        }

        # Only collect detailed debug info if debug mode is enabled
        if debug_mode:
            filtering_method = "redis_level_xrange_filtering" if (start_dt or end_dt) else "recent_data_limit_1000"
            debug_info.update({
                "streams_checked": [],
                "final_counts": {},
                "redis_query_params": {
                    "original_start_date": start_date,
                    "original_end_date": end_date,
                    "parsed_start_dt": str(start_dt) if start_dt else None,
                    "parsed_end_dt": str(end_dt) if end_dt else None,
                    "redis_start_ts": redis_start_ts,
                    "redis_end_ts": redis_end_ts,
                    "filtering_method": filtering_method,
                    "optimization": "Redis XRANGE with time-based Stream IDs for maximum performance"
                }
            })

        # Get data from Redis Streams using highly optimized processing
        if debug_mode:
            debug_info["streams_checked"] = ['stream:bms', 'stream:energy']
            debug_info["processing_steps"].append("Using Redis-level filtering for optimal performance")
        
        # Process both streams efficiently with Redis-level filtering
        bms_result = process_redis_stream('stream:bms', start_dt, end_dt, redis_start_ts, redis_end_ts, debug_mode, debug_info)
        energy_result = process_redis_stream('stream:energy', start_dt, end_dt, redis_start_ts, redis_end_ts, debug_mode, debug_info)
        
        # Combine results (much smaller datasets now)
        all_records = bms_result['records'] + energy_result['records']
        
        # Update debug info efficiently
        debug_info["raw_data_found"] = {
            "bms": bms_result['raw_count'],
            "energy": energy_result['raw_count']
        }
        
        debug_info["filter_results"] = {
            "bms": {
                "raw_count": bms_result['raw_count'],
                "processed_count": bms_result['processed_count'],
                "filtered_count": bms_result['filtered_count']
            },
            "energy": {
                "raw_count": energy_result['raw_count'],
                "processed_count": energy_result['processed_count'],
                "filtered_count": energy_result['filtered_count']
            }
        }

        # Efficient sorting and pagination
        if all_records:
            # Sort by timestamp (newest first) - only if we have records
            all_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Update final counts only if debug mode
        if debug_mode:
            debug_info["final_counts"] = {
                "total_records_before_pagination": len(all_records),
                "pagination": {"limit": limit, "offset": offset}
            }

        # Paginate results efficiently
        paginated_data = paginate_data(all_records, limit, offset)

        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": paginated_data['records'],
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Add helpful message when no records found but filtering was applied
        if len(all_records) == 0 and (start_dt or end_dt):
            message_parts = []
            total_raw_count = debug_info["raw_data_found"]["bms"] + debug_info["raw_data_found"]["energy"]
            
            if total_raw_count == 0:
                message_parts.append("No data found in the specified date range.")
            else:
                message_parts.append(f"No records match the date filter. Redis returned {total_raw_count} entries but none passed validation.")
            
            response_data["message"] = " ".join(message_parts)
            
            # Add data range info in debug mode - optimized to only run when needed
            if debug_mode:
                range_info = {}
                
                # Only get range info if no records were found
                for stream_name, stream_key in [('bms', 'stream:bms'), ('energy', 'stream:energy')]:
                    try:
                        # Get first and last efficiently
                        first_entry = red.xrange(stream_key, count=1)
                        if first_entry:
                            last_entry = red.xrevrange(stream_key, count=1)
                            if last_entry:
                                first_ts = dict(first_entry[0][1]).get(b'timestamp', b'').decode('utf-8') if isinstance(dict(first_entry[0][1]).get(b'timestamp', b''), bytes) else dict(first_entry[0][1]).get('timestamp', '')
                                last_ts = dict(last_entry[0][1]).get(b'timestamp', b'').decode('utf-8') if isinstance(dict(last_entry[0][1]).get(b'timestamp', b''), bytes) else dict(last_entry[0][1]).get('timestamp', '')
                                range_info[f"{stream_name}_data_range"] = {
                                    "first_timestamp": first_ts,
                                    "last_timestamp": last_ts
                                }
                    except Exception:
                        continue
                
                if range_info:
                    response_data["data"]["available_data_ranges"] = range_info
        
        # Add debug info only if requested (reduces response size)
        if debug_mode and debug_info:
            response_data["debug_info"] = debug_info

        return jsonify(response_data), 200

    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to retrieve Redis data",
            "error": str(e)
        }
        
        # Only add debug info in debug mode and if it exists
        if debug_mode and 'debug_info' in locals():
            error_response["debug_info"] = debug_info
            
        return jsonify(error_response), 500


@logger_bp.route('/data/redis/<timestamp>', methods=['DELETE'])
@api_session_required
def delete_redis_by_ts(timestamp):
    """
    Delete Redis stream data by timestamp with validation
    Supports both exact timestamp match and prefix match
    
    Parameters:
    - timestamp: Timestamp to delete (exact match or prefix)
    
    Query parameters:
    - match_type: 'exact' (default) or 'prefix'
    - debug: Enable debug mode (true/false)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error", 
                "message": "Redis service unavailable"
            }), 503

        # Get query parameters
        match_type = request.args.get('match_type', 'exact').lower()
        debug_mode = request.args.get('debug', 'false').lower() == 'true'
        
        # Validate match_type
        if match_type not in ['exact', 'prefix']:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid match_type. Must be 'exact' or 'prefix'"
            }), 400

        # Validate timestamp format (basic validation)
        if not timestamp or len(timestamp) < 8:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid timestamp format. Timestamp too short."
            }), 400

        # Delete from both streams using optimized helper function
        result = delete_entries_by_timestamp(red, timestamp, match_type, debug_mode)
        
        # Check if there was an error
        if "error" in result:
            return jsonify({
                "status_code": 500,
                "status": "error",
                "message": "Failed to delete Redis stream data by timestamp",
                "error": result["error"]
            }), 500
        
        # Check if timestamp exists - return error if not found
        if not result.get("timestamp_exists", False):
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in Redis streams",
                "data": {
                    "bms_deleted": 0,
                    "energy_deleted": 0,
                    "total_deleted": 0,
                    "timestamp_exists": False
                }
            }), 404
        
        # Success response when timestamp found and deleted
        return jsonify({
            "status_code": 200,
            "status": "success", 
            "message": f"Successfully deleted {result['total_deleted']} entries with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}'",
            "data": {
                "bms_deleted": result["bms_deleted"],
                "energy_deleted": result["energy_deleted"],
                "total_deleted": result["total_deleted"],
                "timestamp_exists": result["timestamp_exists"],
                "debug_info": result.get("debug_info") if debug_mode else None
            }
        }), 200

    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete Redis stream data by timestamp",
            "error": str(e)
        }
        
        return jsonify(error_response), 500


@logger_bp.route('/data/redis', methods=['DELETE'])
@api_session_required
def delete_all_redis_data():
    """
    Delete all Redis stream data (both BMS and Energy streams)
    
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
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all Redis data."
            }), 400

        # Delete entire streams using DEL command
        bms_deleted = 0
        energy_deleted = 0
        
        try:
            # Check if streams exist and get their length before deletion
            bms_info = red.xinfo_stream('stream:bms')
            bms_length = bms_info['length']
            bms_deleted = red.delete('stream:bms')
            if bms_deleted:
                bms_deleted = bms_length
        except Exception:
            pass
            
        try:
            energy_info = red.xinfo_stream('stream:energy')
            energy_length = energy_info['length']
            energy_deleted = red.delete('stream:energy')
            if energy_deleted:
                energy_deleted = energy_length
        except Exception:
            pass
        
        total_deleted = bms_deleted + energy_deleted
        
        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": "All Redis stream data deleted successfully",
            "data": {
                "bms_entries_deleted": bms_deleted,
                "energy_entries_deleted": energy_deleted,
                "total_deleted": total_deleted
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete Redis stream data",
            "error": str(e)
        }), 500


# ============== SQLite Data Endpoints ===========================

@logger_bp.route('/data/sqlite', methods=['GET'])
@api_session_required
def get_sqlite_data():
    """
    Get historical data from SQLite with optimized filtering options
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)
    - limit: Maximum records (default: 100, max: 1000)
    - offset: Records to skip (default: 0)
    - table: Specific table name (default: 'bms_data')
    - debug: Enable debug mode (true/false)
    """
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        # Parse query parameters with validation
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        table_name = request.args.get('table', 'bms_data')
        debug_mode = request.args.get('debug', 'false').lower() == 'true'

        # Validate dates first
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid start_date format",
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400
            
        if end_date and end_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid end_date format", 
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400

        # Validate table name (basic SQL injection prevention)
        if not table_name.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid table name format"
            }), 400

        # Process SQLite data using optimized helper function
        result = process_sqlite_data(conn, start_dt, end_dt, table_name, limit, offset, debug_mode)
        conn.close()

        # Check for errors
        if "error" in result:
            return jsonify({
                "status_code": 500,
                "status": "error", 
                "message": "Failed to retrieve SQLite data",
                "error": result["error"]
            }), 500

        # Build successful response with dynamic pagination
        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": result["records"],
                "total_records": result["total_records"],
                "page_info": result["page_info"],
                "processed_count": result["processed_count"],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Add debug info if requested
        if debug_mode and result.get("debug_info"):
            response_data["debug_info"] = result["debug_info"]

        # Add helpful message when no records found
        if result["total_records"] == 0:
            if start_dt or end_dt:
                response_data["message"] = "No records found in the specified date range."
            else:
                response_data["message"] = "No records found in the table."

        return jsonify(response_data), 200
    except sqlite3.Error as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "SQLite database error",
            "error": str(e)
        }), 500
    except ValueError as e:
        return jsonify({
            "status_code": 400,
            "status": "error",
            "message": "Invalid parameter value",
            "error": str(e)
        }), 400
    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to retrieve SQLite data",
            "error": str(e)
        }
        
        return jsonify(error_response), 500


@logger_bp.route('/data/sqlite/<timestamp>', methods=['DELETE'])
@api_session_required
def delete_sqlite_data_by_timestamp(timestamp):
    """
    Delete SQLite data by timestamp with validation
    Supports both exact timestamp match and prefix match
    
    Parameters:
    - timestamp: Timestamp to delete (exact match or prefix)
    
    Query parameters:
    - match_type: 'exact' (default) or 'prefix'
    - table: Target table name (default: 'bms_data')
    - debug: Enable debug mode (true/false)
    """
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        # Get query parameters
        match_type = request.args.get('match_type', 'exact').lower()
        table_name = request.args.get('table', 'bms_data')
        debug_mode = request.args.get('debug', 'false').lower() == 'true'
        
        # Validate match_type
        if match_type not in ['exact', 'prefix']:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid match_type. Must be 'exact' or 'prefix'"
            }), 400

        # Validate table name (SQL injection prevention)
        if not table_name.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid table name format"
            }), 400

        # Validate timestamp format (basic validation)
        if not timestamp or len(timestamp) < 8:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid timestamp format. Timestamp too short."
            }), 400

        # Delete data using optimized helper function
        result = delete_sqlite_by_timestamp(conn, timestamp, table_name, match_type, debug_mode)
        
        conn.close()

        # Check for errors
        if "error" in result:
            return jsonify({
                "status_code": 500,
                "status": "error",
                "message": "Failed to delete SQLite data by timestamp",
                "error": result["error"]
            }), 500

        # Check if timestamp exists - return error if not found
        if not result.get("timestamp_exists", False):
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in table '{table_name}'",
                "data": {
                    "deleted_count": 0,
                    "timestamp_exists": False,
                    "table_name": table_name
                }
            }), 404

        # Success response when timestamp found and deleted
        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": f"Successfully deleted {result['deleted_count']} records with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}' from table '{table_name}'",
            "data": {
                "deleted_count": result["deleted_count"],
                "timestamp_exists": result["timestamp_exists"],
                "table_name": table_name,
                "debug_info": result.get("debug_info") if debug_mode else None
            }
        }), 200

    except sqlite3.Error as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "SQLite database error",
            "error": str(e)
        }), 500
    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete SQLite data by timestamp",
            "error": str(e)
        }
        
        return jsonify(error_response), 500


@logger_bp.route('/data/sqlite', methods=['DELETE'])
@api_session_required
def delete_all_sqlite_data():
    """
    Delete all SQLite data from specified table
    
    Query parameters:
    - table: Target table name (default: 'bms_data')
    - confirm: Must be 'yes' to confirm deletion (required)
    - debug: Enable debug mode (true/false)
    """
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        table_name = request.args.get('table', 'bms_data')
        confirm = request.args.get('confirm', '').lower()
        debug_mode = request.args.get('debug', 'false').lower() == 'true'
        
        # Validate table name (SQL injection prevention)
        if not table_name.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid table name format"
            }), 400

        # Require confirmation for safety
        if confirm != 'yes':
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all data."
            }), 400

        # Get count before deletion
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        cursor = conn.execute(count_query)
        total_before = cursor.fetchone()['total']

        if total_before == 0:
            conn.close()
            return jsonify({
                "status_code": 200,
                "status": "success",
                "message": f"Table '{table_name}' is already empty",
                "data": {
                    "deleted_count": 0,
                    "table_name": table_name
                }
            }), 200

        # Delete all records
        delete_query = f"DELETE FROM {table_name}"
        cursor = conn.execute(delete_query)
        conn.commit()
        
        deleted_count = cursor.rowcount
        conn.close()

        # Build response
        response_data = {
            "status_code": 200,
            "status": "success",
            "message": f"Successfully deleted all {deleted_count} records from table '{table_name}'",
            "data": {
                "deleted_count": deleted_count,
                "table_name": table_name,
                "records_before_deletion": total_before
            }
        }

        if debug_mode:
            response_data["debug_info"] = {
                "table_name": table_name,
                "records_before": total_before,
                "records_deleted": deleted_count,
                "confirmation_required": True
            }

        return jsonify(response_data), 200

    except sqlite3.Error as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "SQLite database error",
            "error": str(e)
        }), 500
    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete all SQLite data",
            "error": str(e)
        }
        
        return jsonify(error_response), 500


# ============== Storage Overview Endpoint ===========================

@logger_bp.route('/data/overview', methods=['GET'])
@api_session_required
def get_storage_overview():
    """Get storage overview and statistics"""
    try:
        overview_data = {
            "storage_overview": {
                "redis_storage": 0.0,  # in MB
                "unit": "MB",
                "sqlite_storage": 0.0,  # in MB  
                "unit": "MB",
                "disk_usage": {
                    "free": 0.0,
                    "total": 0.0
                }
            },
            "data_statistics": {
                "logger_records": 0,
                "bms_records": 0,
                "energy_records": 0,
                "sqlite_records": 0
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Get Redis statistics and memory usage
        if red:
            try:
                # Get Redis memory usage for all keys
                redis_info = red.info('memory')
                redis_used_memory = redis_info.get('used_memory', 0)
                # Convert bytes to MB
                redis_storage_mb = round(redis_used_memory / (1024 * 1024), 2)
                overview_data["storage_overview"]["redis_storage"] = redis_storage_mb
                
                # Get stream info for both streams (record counts)
                bms_count = 0
                energy_count = 0
                
                try:
                    bms_info = red.xinfo_stream('stream:bms')
                    bms_count = bms_info['length']
                except Exception:
                    pass
                    
                try:
                    energy_info = red.xinfo_stream('stream:energy')
                    energy_count = energy_info['length']
                except Exception:
                    pass
                
                total_redis_entries = bms_count + energy_count
                overview_data["data_statistics"]["logger_records"] = total_redis_entries
                overview_data["data_statistics"]["bms_records"] = bms_count
                overview_data["data_statistics"]["energy_records"] = energy_count
            except Exception:
                pass

        # Get SQLite statistics and file size
        try:
            # Get SQLite database file size
            sqlite_db_path = f'{PATH}/data_storage.db'
            if os.path.exists(sqlite_db_path):
                sqlite_file_size = os.path.getsize(sqlite_db_path)
                # Convert bytes to MB
                sqlite_storage_mb = round(sqlite_file_size / (1024 * 1024), 2)
                overview_data["storage_overview"]["sqlite_storage"] = sqlite_storage_mb
            
            # Get record counts from SQLite
            conn = get_sqlite_connection()
            if conn:
                total_sqlite_records = 0
                
                # Count bms_data records
                try:
                    cursor = conn.execute("SELECT COUNT(*) as total FROM bms_data")
                    result = cursor.fetchone()
                    if result:
                        total_sqlite_records += result['total']
                except Exception:
                    pass
                
                # Count energy_data records
                try:
                    cursor = conn.execute("SELECT COUNT(*) as total FROM energy_data")
                    result = cursor.fetchone()
                    if result:
                        total_sqlite_records += result['total']
                except Exception:
                    pass
                
                overview_data["data_statistics"]["sqlite_records"] = total_sqlite_records
                conn.close()
        except Exception:
            pass

        # Get disk usage (simplified)
        try:
            disk = get_disk_detail()
            disk_usage = {
                "free": round(disk.free / (1024**3), 1),  # Convert to GB
                "used": round(disk.used / (1024**3), 1),  # Convert to GB
                "total": round(disk.total / (1024**3), 1),  # Convert to GB
                "unit": "GB"
            }
            overview_data["storage_overview"]["disk_usage"] = disk_usage
        except:
            pass

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": overview_data
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to get storage overview",
            "error": str(e)
        }), 500


# ============== SCC Alarm Log Endpoints ===========================

@logger_bp.route('/scc-alarm/overview', methods=['GET'])
@api_session_required
def get_scc_alarm_overview():
    """Get SCC alarm log overview from Redis Stream"""
    try:
        total_alarms = 0
        
        # Get alarm count from Redis Stream
        if red:
            try:
                stream_info = red.xinfo_stream('scc-logs:data')
                total_alarms = stream_info['length']
            except Exception:
                # Stream doesn't exist yet
                total_alarms = 0

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "data_statistics": {
                    "total_scc_logs": total_alarms,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to get SCC alarm overview",
            "error": str(e)
        }), 500


@logger_bp.route('/scc-alarm/history', methods=['GET'])
@api_session_required
def get_scc_alarm_history():
    """
    Get SCC alarm history from Redis Stream with pagination and filtering
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)
    - limit: Maximum records (default: 50, max: 1000)
    - offset: Records to skip (default: 0)
    - debug: Enable debug mode (true/false)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 50)), 1000)
        offset = int(request.args.get('offset', 0))
        debug_mode = request.args.get('debug', 'false').lower() == 'true'

        # Validate dates
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid start_date format",
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400
            
        if end_date and end_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid end_date format",
                "error": "Date must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
            }), 400

        # Convert datetime to Redis timestamp format for comparison
        redis_start_ts = convert_to_redis_timestamp_format(start_dt) if start_dt else None
        redis_end_ts = convert_to_redis_timestamp_format(end_dt) if end_dt else None

        debug_info = {"stream_checked": "scc-logs:data"} if debug_mode else None

        # Get SCC logs from Redis Stream
        try:
            if redis_start_ts and redis_end_ts:
                # Use XRANGE for time-based filtering
                entries = red.xrange('scc-logs:data', min=f"{redis_start_ts}-0", max=f"{redis_end_ts}-0")
            elif redis_start_ts:
                # From start_date to end
                entries = red.xrange('scc-logs:data', min=f"{redis_start_ts}-0")
            elif redis_end_ts:
                # From beginning to end_date
                entries = red.xrange('scc-logs:data', max=f"{redis_end_ts}-0")
            else:
                # Get recent entries (newest first)
                entries = red.xrevrange('scc-logs:data', count=limit + offset + 100)
        except Exception as e:
            if debug_mode:
                debug_info["stream_error"] = str(e)
            # Stream doesn't exist or error occurred
            entries = []

        # Process entries
        all_records = []
        for entry_id, fields in entries:
            try:
                # Decode entry data
                timestamp = fields.get(b'timestamp', b'').decode('utf-8') if isinstance(fields.get(b'timestamp', b''), bytes) else fields.get('timestamp', '')
                data_json = fields.get(b'data', b'').decode('utf-8') if isinstance(fields.get(b'data', b''), bytes) else fields.get('data', '')
                
                # Parse SCC data
                scc_data = json.loads(data_json) if data_json else {}
                
                # Format record
                record = {
                    'stream_id': entry_id.decode('utf-8') if isinstance(entry_id, bytes) else str(entry_id),
                    'timestamp': timestamp,
                    'scc_data': scc_data
                }
                
                # Apply additional date filtering if needed (for precision)
                if start_dt or end_dt:
                    record_dt = validate_date_format(timestamp)
                    if record_dt:
                        if start_dt and record_dt < start_dt:
                            continue
                        if end_dt and record_dt > end_dt:
                            continue
                
                all_records.append(record)
                
            except Exception as e:
                if debug_mode and debug_info:
                    debug_info.setdefault("parsing_errors", []).append(str(e))
                continue

        # Sort by timestamp (newest first) if not already sorted by XREVRANGE
        if redis_start_ts or redis_end_ts:
            all_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Paginate results
        paginated_data = paginate_data(all_records, limit, offset)

        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": paginated_data['records'],
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Add helpful message when no records found
        if len(all_records) == 0:
            if start_dt or end_dt:
                response_data["message"] = "No SCC logs found in the specified date range."
            else:
                response_data["message"] = "No SCC logs found."

        # Add debug info if requested
        if debug_mode and debug_info:
            response_data["debug_info"] = debug_info

        return jsonify(response_data), 200

    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to get SCC alarm history",
            "error": str(e)
        }
        
        if debug_mode and 'debug_info' in locals():
            error_response["debug_info"] = debug_info
            
        return jsonify(error_response), 500


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
            entries = red.xrevrange('scc-logs:data', count=limit)
        except Exception:
            # Stream doesn't exist
            entries = []

        all_logs = []
        for entry_id, fields in entries:
            try:
                # Decode entry data
                timestamp = fields.get(b'timestamp', b'').decode('utf-8') if isinstance(fields.get(b'timestamp', b''), bytes) else fields.get('timestamp', '')
                data_json = fields.get(b'data', b'').decode('utf-8') if isinstance(fields.get(b'data', b''), bytes) else fields.get('data', '')
                
                # Parse SCC data
                scc_data = json.loads(data_json) if data_json else {}
                
                # Format log entry
                log_entry = {
                    'stream_id': entry_id.decode('utf-8') if isinstance(entry_id, bytes) else str(entry_id),
                    'timestamp': timestamp,
                    'scc_data': scc_data
                }
                
                all_logs.append(log_entry)
                
            except Exception:
                continue

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "total_records": len(all_logs),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": all_logs
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to download SCC alarms",
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
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all SCC logs."
            }), 400

        # Get count before deletion
        deleted_count = 0
        try:
            stream_info = red.xinfo_stream('scc-logs:data')
            deleted_count = stream_info['length']
            
            # Delete entire stream
            red.delete('scc-logs:data')
        except Exception:
            # Stream doesn't exist
            deleted_count = 0

        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": "SCC logs deleted successfully",
            "data": {
                "deleted_records": deleted_count
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to clear SCC alarms",
            "error": str(e)
        }), 500


# ============== SCC Data Endpoints (Additional) ===========================

@logger_bp.route('/data/scc', methods=['GET'])
@api_session_required
def get_scc_data():
    """
    Get SCC data from Redis Stream with filtering options (alias for /scc-alarm/history)
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)
    - limit: Maximum records (default: 50, max: 1000)
    - offset: Records to skip (default: 0)
    - debug: Enable debug mode (true/false)
    """
    # Redirect to scc-alarm/history with same parameters
    return get_scc_alarm_history()


@logger_bp.route('/data/scc/<timestamp>', methods=['DELETE'])
@api_session_required
def delete_scc_data_by_timestamp(timestamp):
    """
    Delete SCC data by timestamp from Redis Stream
    Supports both exact timestamp match and prefix match
    
    Parameters:
    - timestamp: Timestamp to delete (exact match or prefix)
    
    Query parameters:
    - match_type: 'exact' (default) or 'prefix'
    - confirm: Must be 'yes' to confirm deletion (required)
    - debug: Enable debug mode (true/false)
    """
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Get query parameters
        match_type = request.args.get('match_type', 'exact').lower()
        confirm = request.args.get('confirm', '').lower()
        debug_mode = request.args.get('debug', 'false').lower() == 'true'
        
        # Require confirmation for safety
        if confirm != 'yes':
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion."
            }), 400
        
        # Validate match_type
        if match_type not in ['exact', 'prefix']:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid match_type. Must be 'exact' or 'prefix'"
            }), 400

        # Validate timestamp format (basic validation)
        if not timestamp or len(timestamp) < 8:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid timestamp format. Timestamp too short."
            }), 400

        # Delete from SCC stream using helper function
        result = delete_scc_entries_by_timestamp(red, timestamp, match_type, debug_mode)
        
        # Check for errors
        if "error" in result:
            return jsonify({
                "status_code": 500,
                "status": "error",
                "message": "Failed to delete SCC data by timestamp",
                "error": result["error"]
            }), 500

        # Check if timestamp exists - return error if not found
        if not result.get("timestamp_exists", False):
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in SCC logs stream",
                "data": {
                    "deleted_count": 0,
                    "timestamp_exists": False
                }
            }), 404

        # Success response when timestamp found and deleted
        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": f"Successfully deleted {result['deleted_count']} SCC entries with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}'",
            "data": {
                "deleted_count": result["deleted_count"],
                "timestamp_exists": result["timestamp_exists"],
                "debug_info": result.get("debug_info") if debug_mode else None
            }
        }), 200

    except Exception as e:
        error_response = {
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete SCC data by timestamp",
            "error": str(e)
        }
        
        return jsonify(error_response), 500


@logger_bp.route('/data/scc', methods=['DELETE'])
@api_session_required  
def delete_all_scc_data():
    """
    Delete all SCC data from Redis Stream
    
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
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all SCC data."
            }), 400

        # Get count before deletion
        deleted_count = 0
        try:
            stream_info = red.xinfo_stream('scc-logs:data')
            deleted_count = stream_info['length']
            
            # Delete entire stream
            red.delete('scc-logs:data')
        except Exception:
            # Stream doesn't exist
            deleted_count = 0

        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": "All SCC data deleted successfully",
            "data": {
                "deleted_records": deleted_count
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete all SCC data",
            "error": str(e)
        }), 500
