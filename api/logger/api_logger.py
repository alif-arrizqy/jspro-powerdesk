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
from functools import wraps
from ..redisconnection import connection as red
from .helper import *
from helpers.system_resources_helper import get_disk_detail
from config import PATH

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import battery configuration for section filtering
try:
    from config import battery_type as default_battery_type
except ImportError:
    default_battery_type = 'talis5'

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

# ============== Section Filtering Helper Functions ===========================

def get_streams_for_section(section=None):
    """
    Get appropriate Redis streams based on section parameter
    
    Args:
        section: Battery section (talis5, jspro, scc) or None for default
        
    Returns:
        list: List of stream names to process
    """
    if section is None:
        section = default_battery_type
    
    if section == 'talis5':
        # Talis5: BMS stream only
        return ['stream:bms']
    elif section == 'jspro':
        # JSPro: Only JSPro battery stream
        return ['stream:jspro_battery']
    elif section == 'scc':
        # SCC/Energy: Only Energy/SCC stream
        return ['stream:energy']
    else:
        # Default fallback to talis5 stream
        return ['stream:bms']

def get_tables_for_section(section=None, default_table='bms_data'):
    """
    Get appropriate SQLite table names based on section parameter
    
    Args:
        section: Battery section (talis5, jspro, scc) or None for default
        default_table: Default table name if not specified
        
    Returns:
        list: List of table names to query
    """
    if section is None:
        section = default_battery_type
    
    if section == 'talis5':
        # Talis5: BMS data table only
        return ['bms_data']
    elif section == 'jspro':
        # JSPro: JSPro battery data table only
        return ['jspro_battery_data']
    elif section == 'scc':
        # SCC/Energy: Energy data table only
        return ['energy_data']
    else:
        # Default fallback based on specified table or default
        return [default_table]

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
    - section: Battery section for filtering data:
        * 'talis5': BMS (stream:bms)
        * 'jspro': JSPro Battery (stream:jspro_battery)
        * 'scc': Energy/SCC (stream:energy)
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
        section = request.args.get('section')  # New section parameter
        
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

        # Get appropriate streams based on section parameter
        target_streams = get_streams_for_section(section)
        
        # Get data from Redis Streams using highly optimized processing
        if debug_mode:
            debug_info["streams_checked"] = target_streams
            debug_info["processing_steps"].append("Using Redis-level filtering for optimal performance")
            debug_info["section"] = section or default_battery_type
        
        # Process streams efficiently with Redis-level filtering
        all_records = []
        stream_results = {}
        
        for stream_name in target_streams:
            stream_result = process_redis_stream(stream_name, start_dt, end_dt, redis_start_ts, redis_end_ts, debug_mode, debug_info)
            stream_results[stream_name] = stream_result
            all_records.extend(stream_result['records'])
        
        # Update debug info efficiently
        debug_info["raw_data_found"] = {}
        debug_info["filter_results"] = {}
        
        for stream_name, result in stream_results.items():
            debug_info["raw_data_found"][stream_name] = result['raw_count']
            debug_info["filter_results"][stream_name] = {
                "raw_count": result['raw_count'],
                "processed_count": result['processed_count'],
                "filtered_count": result['filtered_count']
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

        # Format response data to ensure proper types
        formatted_records = [format_response_data(record) for record in paginated_data['records']]

        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": formatted_records,
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "section": section or default_battery_type,
                "target_streams": target_streams,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Add helpful message when no records found but filtering was applied
        if len(all_records) == 0 and (start_dt or end_dt):
            message_parts = []
            total_raw_count = sum(debug_info["raw_data_found"].values())
            
            if total_raw_count == 0:
                message_parts.append("No data found in the specified date range.")
            else:
                message_parts.append(f"No records match the date filter. Redis returned {total_raw_count} entries but none passed validation.")
            
            response_data["message"] = " ".join(message_parts)
            
            # Add data range info in debug mode - optimized to only run when needed
            if debug_mode:
                range_info = {}
                
                # Only get range info if no records were found
                for stream_name in target_streams:
                    try:
                        # Get first and last efficiently
                        first_entry = red.xrange(stream_name, count=1)
                        if first_entry:
                            last_entry = red.xrevrange(stream_name, count=1)
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
    - section: Battery section (talis5, jspro, scc) for targeting specific streams
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
        section = request.args.get('section')  # New section parameter
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

        # Get appropriate streams based on section parameter
        target_streams = get_streams_for_section(section)
        
        # Delete from target streams using optimized helper function
        result = delete_entries_by_timestamp_section(red, timestamp, match_type, target_streams, debug_mode)
        
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
            stream_names = ', '.join(target_streams)
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": f"Timestamp {'prefix' if match_type == 'prefix' else 'exact match'} '{timestamp}' not found in Redis streams ({stream_names})",
                "data": {
                    "streams_deleted": result.get("streams_deleted", {}),
                    "total_deleted": 0,
                    "timestamp_exists": False,
                    "section": section or default_battery_type,
                    "target_streams": target_streams
                }
            }), 404
        
        # Success response when timestamp found and deleted
        stream_names = ', '.join(target_streams)
        return jsonify({
            "status_code": 200,
            "status": "success", 
            "message": f"Successfully deleted {result['total_deleted']} entries with timestamp {'matching prefix' if match_type == 'prefix' else 'exactly matching'} '{timestamp}' from streams ({stream_names})",
            "data": {
                "streams_deleted": result.get("streams_deleted", {}),
                "total_deleted": result["total_deleted"],
                "timestamp_exists": result["timestamp_exists"],
                "section": section or default_battery_type,
                "target_streams": target_streams,
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
    Delete all Redis stream data based on section
    
    Query parameters:
    - confirm: Must be 'yes' to confirm deletion (required)
    - section: Battery section (talis5, jspro, scc) for targeting specific streams
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
        section = request.args.get('section')  # New section parameter
        
        # Require confirmation for safety
        if confirm != 'yes':
            return jsonify({
                "status_code": 400,
                "status": "error",
                "message": "Confirmation required. Add '?confirm=yes' to confirm deletion of all Redis data."
            }), 400

        # Get appropriate streams based on section parameter
        target_streams = get_streams_for_section(section)
        
        # Delete entire streams using DEL command
        streams_deleted = {}
        total_deleted = 0
        
        # Delete each target stream
        for stream_name in target_streams:
            try:
                # Check if stream exists and get its length before deletion
                stream_info = red.xinfo_stream(stream_name)
                stream_length = stream_info['length']
                deleted = red.delete(stream_name)
                if deleted:
                    streams_deleted[stream_name] = stream_length
                    total_deleted += stream_length
                else:
                    streams_deleted[stream_name] = 0
            except Exception:
                streams_deleted[stream_name] = 0  # Stream doesn't exist or error
        
        stream_names = ', '.join(target_streams)
        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": f"Redis stream data deleted successfully from section '{section or default_battery_type}' ({stream_names})",
            "data": {
                "streams_deleted": streams_deleted,
                "total_deleted": total_deleted,
                "section": section or default_battery_type,
                "target_streams": target_streams
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
    - section: Battery section for filtering data:
        * 'talis5': BMS data (bms_data)
        * 'jspro': JSPro Battery data (jspro_battery_data)
        * 'scc': Energy/SCC data (energy_data)
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
        section = request.args.get('section')  # New section parameter
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

        # Determine target tables based on section parameter
        if section:
            target_tables = get_tables_for_section(section)
        else:
            target_tables = [table_name]  # Use specified table or default

        # Validate table names (basic SQL injection prevention)
        for table in target_tables:
            if not table.replace('_', '').replace('-', '').isalnum():
                return jsonify({
                    "status_code": 400,
                    "status": "error",
                    "message": f"Invalid table name format: {table}"
                }), 400

        # Process SQLite data using optimized helper function for multiple tables
        all_records = []
        total_records = 0
        combined_debug_info = {
            "section": section or default_battery_type,
            "target_tables": target_tables,
            "table_results": {}
        } if debug_mode else None
        
        for table in target_tables:
            try:
                result = process_sqlite_data(conn, start_dt, end_dt, table, limit, offset, debug_mode)
                
                # Check for errors
                if "error" in result:
                    conn.close()
                    return jsonify({
                        "status_code": 500,
                        "status": "error", 
                        "message": f"Failed to retrieve SQLite data from {table}",
                        "error": result["error"]
                    }), 500
                
                all_records.extend(result["records"])
                total_records += result["total_records"]
                
                if debug_mode:
                    combined_debug_info["table_results"][table] = {
                        "records_found": len(result["records"]),
                        "total_records": result["total_records"],
                        "processed_count": result["processed_count"]
                    }
                    
            except Exception as e:
                # If table doesn't exist, skip it (for backwards compatibility)
                if debug_mode:
                    combined_debug_info["table_results"][table] = {
                        "error": f"Table {table} not accessible: {str(e)}",
                        "records_found": 0
                    }
                continue
        
        conn.close()

        # Sort combined records by timestamp if we have multiple tables
        if len(target_tables) > 1 and all_records:
            all_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Apply pagination to combined results
        paginated_data = paginate_data(all_records, limit, offset)

        # Format response data to ensure proper types
        formatted_records = [format_response_data(record) for record in paginated_data['records']]

        # Build successful response with dynamic pagination
        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": formatted_records,
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "processed_count": len(all_records),
                "section": section or default_battery_type,
                "tables_queried": target_tables,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Add debug info if requested
        if debug_mode and combined_debug_info:
            response_data["debug_info"] = combined_debug_info

        # Add helpful message when no records found
        if len(all_records) == 0:
            if start_dt or end_dt:
                response_data["message"] = "No records found in the specified date range."
            else:
                response_data["message"] = "No records found in the tables."

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


# ============== SCC/Energy Data Endpoints ===========================

@logger_bp.route('/scc', methods=['GET'])
@api_session_required
def get_scc_data():
    """
    Get SCC/Energy data from Redis stream:energy with filtering options
    This is a dedicated endpoint for SCC/Energy data
    
    Query parameters:
    - start_date: Start date (ISO 8601 format)
    - end_date: End date (ISO 8601 format)  
    - limit: Maximum records (default: 55)
    - offset: Records to skip (default: 0)
    - debug: Enable debug mode (true/false)
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
                "streams_checked": ["stream:energy"],
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

        # Get data from stream:energy only
        target_streams = ['stream:energy']
        
        # Get data from Redis Streams using highly optimized processing
        if debug_mode:
            debug_info["processing_steps"].append("Using Redis-level filtering for SCC/Energy stream")
            debug_info["section"] = "scc"
        
        # Process stream efficiently with Redis-level filtering
        all_records = []
        stream_results = {}
        
        for stream_name in target_streams:
            stream_result = process_redis_stream(stream_name, start_dt, end_dt, redis_start_ts, redis_end_ts, debug_mode, debug_info)
            stream_results[stream_name] = stream_result
            all_records.extend(stream_result['records'])
        
        # Update debug info efficiently
        debug_info["raw_data_found"] = {}
        debug_info["filter_results"] = {}
        
        for stream_name, result in stream_results.items():
            debug_info["raw_data_found"][stream_name] = result['raw_count']
            debug_info["filter_results"][stream_name] = {
                "raw_count": result['raw_count'],
                "processed_count": result['processed_count'],
                "filtered_count": result['filtered_count']
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

        # Format response data to ensure proper types
        formatted_records = [format_response_data(record) for record in paginated_data['records']]

        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": formatted_records,
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "section": "scc",
                "target_streams": target_streams,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Add helpful message when no records found but filtering was applied
        if len(all_records) == 0 and (start_dt or end_dt):
            message_parts = []
            total_raw_count = sum(debug_info["raw_data_found"].values())
            
            if total_raw_count == 0:
                message_parts.append("No SCC/Energy data found in the specified date range.")
            else:
                message_parts.append(f"No records match the date filter. Redis returned {total_raw_count} entries but none passed validation.")
            
            response_data["message"] = " ".join(message_parts)
            
            # Add data range info in debug mode - optimized to only run when needed
            if debug_mode:
                range_info = {}
                
                # Only get range info if no records were found
                for stream_name in target_streams:
                    try:
                        # Get first and last efficiently
                        first_entry = red.xrange(stream_name, count=1)
                        if first_entry:
                            last_entry = red.xrevrange(stream_name, count=1)
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
            "message": "Failed to retrieve SCC/Energy data",
            "error": str(e)
        }
        
        # Only add debug info in debug mode and if it exists
        if debug_mode and 'debug_info' in locals():
            error_response["debug_info"] = debug_info
            
        return jsonify(error_response), 500


# ============== Section-based Data Endpoints ===========================

@logger_bp.route('/talis5', methods=['GET'])
@api_session_required
def get_talis5_data():
    """
    Get Talis5 BMS data - redirects to /data/redis with section=talis5
    This is a convenience endpoint for Talis5 BMS data
    """
    # Copy all query parameters and add section
    args = dict(request.args)
    args['section'] = 'talis5'
    
    # Forward to the main Redis endpoint with section parameter
    from flask import redirect, url_for
    return redirect(url_for('logger.get_redis_data', **args))


@logger_bp.route('/jspro', methods=['GET'])
@api_session_required
def get_jspro_data():
    """
    Get JSPro battery data - redirects to /data/redis with section=jspro
    This is a convenience endpoint for JSPro battery data
    """
    # Copy all query parameters and add section
    args = dict(request.args)
    args['section'] = 'jspro'
    
    # Forward to the main Redis endpoint with section parameter
    from flask import redirect, url_for
    return redirect(url_for('logger.get_redis_data', **args))


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
                "jspro_records": 0,
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
                
                # Get stream info for all streams (record counts)
                bms_count = 0
                energy_count = 0
                jspro_count = 0
                
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
                
                try:
                    jspro_info = red.xinfo_stream('stream:jspro_battery')
                    jspro_count = jspro_info['length']
                except Exception:
                    pass
                
                total_redis_entries = bms_count + energy_count + jspro_count
                overview_data["data_statistics"]["logger_records"] = total_redis_entries
                overview_data["data_statistics"]["bms_records"] = bms_count
                overview_data["data_statistics"]["energy_records"] = energy_count
                overview_data["data_statistics"]["jspro_records"] = jspro_count
            except Exception:
                pass

        # Get SQLite statistics and file size
        try:
            # Get SQLite database file size
            sqlite_db_path = f'{PATH}/database/data_storage.db'
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
                
                # Count jspro_battery_data records
                try:
                    cursor = conn.execute("SELECT COUNT(*) as total FROM jspro_battery_data")
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
        active_alarms = 0
        last_alarm_time = None
        alarm_types = {}
        severity_count = {
            'critical': 0,
            'warning': 0,
            'info': 0
        }
        
        # Get alarm count and statistics from Redis Stream
        if red:
            try:
                # Check if stream exists
                stream_info = red.xinfo_stream('scc-logs:data')
                total_alarms = stream_info['length']
                
                # Get recent entries to analyze patterns (last 100 entries)
                recent_entries = red.xrevrange('scc-logs:data', '+', '-', count=100)
                
                for entry_id, fields in recent_entries:
                    try:
                        # Parse timestamp from entry ID
                        timestamp_ms = int(entry_id.split(b'-')[0])
                        entry_time = datetime.fromtimestamp(timestamp_ms / 1000)
                        
                        if not last_alarm_time or entry_time > last_alarm_time:
                            last_alarm_time = entry_time
                        
                        # Parse alarm data if available
                        if b'data' in fields:
                            import json
                            alarm_data = json.loads(fields[b'data'].decode())
                            
                            # Count different alarm types and severities
                            for scc_id, scc_data in alarm_data.items():
                                if isinstance(scc_data, dict) and 'alarm' in scc_data:
                                    alarm_obj = scc_data['alarm']
                                    if alarm_obj:
                                        active_alarms += 1
                                        
                                        # Categorize alarms by type and severity
                                        for alarm_type, alarm_status in alarm_obj.items():
                                            if alarm_type not in alarm_types:
                                                alarm_types[alarm_type] = 0
                                            alarm_types[alarm_type] += 1
                                            
                                            # Categorize by severity
                                            if alarm_status in ['fault', 'overvoltage', 'short_circuit', 'overload', 'high_voltage', 'wrong', 'overtemp', 'overdischarge']:
                                                severity_count['critical'] += 1
                                            elif alarm_status in ['warning', 'unrecognized', 'abnormal', 'low_voltage', 'undervoltage', 'lowtemp']:
                                                severity_count['warning'] += 1
                                            else:
                                                severity_count['info'] += 1
                                                
                    except Exception as e:
                        continue
                        
            except Exception:
                # Stream doesn't exist yet
                total_alarms = 0

        overview_data = {
            "total_alarms": total_alarms,
            "active_alarms": active_alarms,
            "last_alarm_time": last_alarm_time.strftime("%Y-%m-%d %H:%M:%S") if last_alarm_time else None,
            "alarm_statistics": {
                "severity_breakdown": severity_count,
                "top_alarm_types": dict(sorted(alarm_types.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            "stream_info": {
                "stream_name": "scc-logs:data",
                "total_entries": total_alarms
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
                # Parse timestamp from entry ID (milliseconds)
                timestamp_ms = int(entry_id.split(b'-')[0]) if isinstance(entry_id, bytes) else int(entry_id.split('-')[0])
                entry_time = datetime.fromtimestamp(timestamp_ms / 1000)
                
                # Decode entry data
                timestamp = fields.get(b'timestamp', b'').decode('utf-8') if isinstance(fields.get(b'timestamp', b''), bytes) else fields.get('timestamp', '')
                data_json = fields.get(b'data', b'').decode('utf-8') if isinstance(fields.get(b'data', b''), bytes) else fields.get('data', '')
                
                # Parse SCC data
                import json
                scc_data = json.loads(data_json) if data_json else {}
                
                # Extract individual alarms from SCC data
                alarms = []
                for scc_id, scc_info in scc_data.items():
                    if isinstance(scc_info, dict) and 'alarm' in scc_info:
                        alarm_obj = scc_info.get('alarm')
                        if alarm_obj and isinstance(alarm_obj, dict):
                            for alarm_type, alarm_status in alarm_obj.items():
                                if alarm_status and alarm_status != 'normal':
                                    alarms.append({
                                        'scc_id': scc_id,
                                        'alarm_type': alarm_type,
                                        'alarm_status': alarm_status,
                                        'battery_voltage': scc_info.get('battery_voltage', 0),
                                        'battery_temperature': scc_info.get('battery_temperature', 0),
                                        'device_temperature': scc_info.get('device_temperature', 0),
                                        'load_status': scc_info.get('load_status', 'unknown')
                                    })
                
                # Format record
                record = {
                    'stream_id': entry_id.decode('utf-8') if isinstance(entry_id, bytes) else str(entry_id),
                    'timestamp': timestamp or entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'entry_time': entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'total_alarms': len(alarms),
                    'alarms': alarms,
                    'raw_scc_data': scc_data
                }
                
                all_records.append(record)
                
            except Exception as e:
                if debug_mode:
                    if "parsing_errors" not in debug_info:
                        debug_info["parsing_errors"] = []
                    debug_info["parsing_errors"].append(f"Error parsing entry {entry_id}: {str(e)}")
                continue

        # Sort by timestamp (newest first) if not already sorted by XREVRANGE
        if redis_start_ts or redis_end_ts:
            all_records.sort(key=lambda x: x.get('entry_time', ''), reverse=True)

        # Paginate results
        paginated_data = paginate_data(all_records, limit, offset)

        response_data = {
            "status_code": 200,
            "status": "success",
            "data": {
                "records": paginated_data['records'],
                "total_records": paginated_data['total_records'],
                "page_info": paginated_data['page_info'],
                "stream_info": {
                    "stream_name": "scc-logs:data",
                    "total_entries_processed": len(all_records)
                },
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Add helpful message when no records found
        if len(all_records) == 0:
            if redis_start_ts or redis_end_ts:
                response_data["message"] = "No SCC alarm logs found for the specified date range"
            else:
                response_data["message"] = "No SCC alarm logs available"

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
                import json
                scc_data = json.loads(data_json) if data_json else {}
                
                # Format log entry
                log_entry = {
                    'stream_id': entry_id.decode('utf-8') if isinstance(entry_id, bytes) else str(entry_id),
                    'timestamp': timestamp,
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
                "download_info": {
                    "requested_limit": limit,
                    "actual_downloaded": len(all_logs),
                    "stream_name": "scc-logs:data"
                },
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
            stream_info = red.xinfo_stream('scc-logs:data')
            deleted_count = stream_info['length']
            # Delete the entire stream
            red.delete('scc-logs:data')
        except Exception:
            # Stream doesn't exist
            deleted_count = 0

        return jsonify({
            "status_code": 200,
            "status": "success",
            "message": f"Successfully cleared {deleted_count} SCC alarm logs",
            "data": {
                "deleted_count": deleted_count,
                "stream_name": "scc-logs:data",
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
