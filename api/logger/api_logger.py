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
                **paginated_data,
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
    """Delete all Redis stream data (both BMS and Energy streams)"""
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

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
    Get historical data from SQLite with filtering options
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)
    - limit: Maximum records (default: 100)
    - offset: Records to skip (default: 0)
    - table: Specific table name (optional)
    """
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        table_name = request.args.get('table', 'energy_logs')

        # Validate dates
        start_dt = validate_date_format(start_date) if start_date else None
        end_dt = validate_date_format(end_date) if end_date else None
        
        if start_date and start_dt is False:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid start_date format"
            }), 400

        # Build SQL query
        base_query = f"SELECT * FROM {table_name}"
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        conditions = []
        params = []

        if start_dt:
            conditions.append("created_at >= ?")
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
            
        if end_dt:
            conditions.append("created_at <= ?")
            params.append(end_dt.strftime("%Y-%m-%d %H:%M:%S"))

        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause

        # Get total count
        cursor = conn.execute(count_query, params)
        total_records = cursor.fetchone()['total']

        # Get paginated data
        query = f"{base_query} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        cursor = conn.execute(query, params + [limit, offset])
        
        records = []
        for row in cursor.fetchall():
            record = dict(row)
            records.append(record)

        conn.close()

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "records": records,
                "total_records": total_records,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_next": (offset + limit) < total_records,
                    "has_prev": offset > 0
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to retrieve SQLite data",
            "error": str(e)
        }), 500


@logger_bp.route('/data/sqlite', methods=['POST'])
@api_session_required
def store_sqlite_data():
    """Store data to SQLite database"""
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        data = request.get_json()
        if not data:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Invalid request body"
            }), 400

        site_id = data.get('site_id')
        site_name = data.get('site_name')
        table_name = data.get('table_name', 'energy_logs')
        records = data.get('data', [])

        if not site_id or not records:
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Missing required fields"
            }), 400

        # Create table if not exists
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT NOT NULL,
            site_name TEXT,
            timestamp TEXT,
            energy_data TEXT,
            bms_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        conn.execute(create_table_query)

        # Insert records
        stored_count = 0
        for record in records:
            insert_query = f"""
            INSERT INTO {table_name} (site_id, site_name, timestamp, energy_data, bms_data)
            VALUES (?, ?, ?, ?, ?)
            """
            conn.execute(insert_query, (
                site_id,
                site_name,
                record.get('timestamp', datetime.now().isoformat()),
                json.dumps(record.get('energy_data', {})),
                json.dumps(record.get('bms_data', []))
            ))
            stored_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            "status_code": 201,
            "status": "success",
            "message": "SQLite data stored successfully",
            "data": {
                "records_stored": stored_count,
                "table_name": table_name
            }
        }), 201

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to store SQLite data",
            "error": str(e)
        }), 500


@logger_bp.route('/data/sqlite/<int:record_id>', methods=['DELETE'])
@api_session_required
def delete_sqlite_data(record_id):
    """Delete specific SQLite data by ID"""
    try:
        conn = get_sqlite_connection()
        if not conn:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "SQLite database unavailable"
            }), 503

        table_name = request.args.get('table', 'energy_logs')
        
        cursor = conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            conn.close()
            return jsonify({
                "status_code": 200,
                "status": "success",
                "message": "SQLite data deleted successfully"
            }), 200
        else:
            conn.close()
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": "SQLite data not found"
            }), 404

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to delete SQLite data",
            "error": str(e)
        }), 500


# ============== Storage Overview Endpoint ===========================

@logger_bp.route('/data/overview', methods=['GET'])
@api_session_required
def get_storage_overview():
    """Get storage overview and statistics"""
    try:
        overview_data = {
            "storage_overview": {
                "redis_storage": 0,
                "sqlite_storage": 0,
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

        # Get Redis statistics
        if red:
            try:
                # Get stream info for both streams
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
                overview_data["storage_overview"]["redis_storage"] = total_redis_entries
                overview_data["data_statistics"]["logger_records"] = total_redis_entries
                overview_data["data_statistics"]["bms_records"] = bms_count
                overview_data["data_statistics"]["energy_records"] = energy_count
            except:
                pass

        # Get SQLite statistics
        try:
            conn = get_sqlite_connection()
            if conn:
                cursor = conn.execute("SELECT COUNT(*) as total FROM energy_logs")
                result = cursor.fetchone()
                if result:
                    overview_data["storage_overview"]["sqlite_storage"] = result['total']
                    overview_data["data_statistics"]["sqlite_records"] = result['total']
                conn.close()
        except:
            pass

        # Get disk usage (simplified)
        try:
            total, used, free = shutil.disk_usage(".")
            overview_data["storage_overview"]["disk_usage"] = {
                "free": round(free / (1024**3), 1),  # GB
                "total": round(total / (1024**3), 1)  # GB
            }
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
    """Get SCC alarm log overview"""
    try:
        total_alarms = 0
        
        # Get alarm count from Redis
        if red:
            alarm_keys = red.keys("scc:alarm:*")
            total_alarms = len(alarm_keys)

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "data_statistics": {
                    "total_alarm_logs": total_alarms,
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
    """Get SCC alarm history with pagination"""
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        limit = min(int(request.args.get('limit', 50)), 1000)
        offset = int(request.args.get('offset', 0))

        # Get alarm data from Redis
        alarm_keys = red.keys("scc:alarm:*")
        all_alarms = []
        
        for key in alarm_keys:
            try:
                data = red.get(key)
                if data:
                    alarm = json.loads(data)
                    all_alarms.append(alarm)
            except:
                continue

        # Sort by timestamp (newest first)
        all_alarms.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Paginate
        paginated_data = paginate_data(all_alarms, limit, offset)

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "logger_records": len(all_alarms),
                "logs": paginated_data['records'],
                **paginated_data['page_info'],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to get SCC alarm history",
            "error": str(e)
        }), 500


@logger_bp.route('/scc-alarm', methods=['GET'])
@api_session_required
def download_scc_alarms():
    """Download all SCC alarm logs"""
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Get all alarm data
        alarm_keys = red.keys("scc:alarm:*")
        all_alarms = []
        
        for key in alarm_keys:
            try:
                data = red.get(key)
                if data:
                    all_alarms.append(json.loads(data))
            except:
                continue

        return jsonify({
            "status_code": 200,
            "status": "success",
            "data": {
                "logger_records": len(all_alarms),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": all_alarms
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
    """Clear all SCC alarm logs"""
    try:
        if not red:
            return jsonify({
                "status_code": 503,
                "status": "error",
                "message": "Redis service unavailable"
            }), 503

        # Delete all alarm keys
        alarm_keys = red.keys("scc:alarm:*")
        if alarm_keys:
            red.delete(*alarm_keys)

        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": "SCC Alarm data deleted successfully",
            "data": {
                "deleted_records": len(alarm_keys)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status_code": 500,
            "status": "error",
            "message": "Failed to clear SCC alarms",
            "error": str(e)
        }), 500
