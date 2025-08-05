# SQLite database path
from datetime import datetime
import sqlite3
import json
from ..redisconnection import connection as red
from config import PATH

SQLITE_DB_PATH = f'{PATH}/data_storage.db'

def get_sqlite_connection():
    """Get SQLite database connection"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    except Exception as e:
        print(f"SQLite connection error: {e}")
        return None

def validate_date_format(date_string):
    """Optimized date format validation with caching-like approach"""
    if not date_string:
        return None
    
    # Fast path for Redis format (most common case)
    if len(date_string) == 15 and 'T' in date_string:
        try:
            return datetime.strptime(date_string, '%Y%m%dT%H%M%S')
        except ValueError:
            pass
    
    # Try other formats only if needed
    formats_to_try = [
        lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')),
        lambda x: datetime.strptime(x, '%Y%m%d%H%M%S') if len(x) == 14 and x.isdigit() else None,
        lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'),
        lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
    ]
    
    for format_func in formats_to_try:
        try:
            result = format_func(date_string)
            if result:
                return result
        except (ValueError, TypeError):
            continue
    
    return False

def process_redis_stream(stream_name, start_dt=None, end_dt=None, redis_start_ts=None, redis_end_ts=None, debug_mode=False, debug_info=None):
    """
    Highly optimized stream processing with Redis-level filtering
    Uses Redis XRANGE with timestamp-based IDs for efficient querying
    """
    if not debug_info:
        debug_info = {"processing_steps": []}
    
    raw_count = 0
    processed_count = 0
    filtered_count = 0
    records = []
    
    try:
        if debug_mode and debug_info.get("processing_steps") is not None:
            debug_info["processing_steps"].append(f"Processing {stream_name}...")
        
        # Smart Redis querying based on date filters
        if start_dt or end_dt:
            # Use Redis-level filtering with XRANGE min/max parameters
            # Convert datetime to Redis Stream ID format (timestamp-based)
            min_id = "-"  # Start from beginning
            max_id = "+"  # End at latest
            
            if start_dt:
                # Create minimum stream ID from start datetime
                start_timestamp_ms = int(start_dt.timestamp() * 1000)
                min_id = f"{start_timestamp_ms}-0"
                
            if end_dt:
                # Create maximum stream ID from end datetime
                end_timestamp_ms = int(end_dt.timestamp() * 1000)
                max_id = f"{end_timestamp_ms}-999999999999999"
            
            if debug_mode and debug_info.get("processing_steps") is not None:
                debug_info["processing_steps"].append(f"Redis XRANGE query: {stream_name} {min_id} {max_id}")
            
            # Efficient Redis query - only get data in time range
            stream_data = red.xrange(stream_name, min=min_id, max=max_id)
        else:
            # If no date filters, get recent data with limit to avoid memory issues
            stream_data = red.xrevrange(stream_name, count=1000)  # Last 1000 entries
            
        raw_count = len(stream_data)
        
        if debug_mode and raw_count > 0 and debug_info.get("processing_steps") is not None:
            debug_info["processing_steps"].append(f"Redis returned {raw_count} entries for {stream_name}")
            
            # Sample first entry for debugging (simplified)
            sample_id, sample_fields = stream_data[0]
            debug_info[f"sample_{stream_name.split(':')[1]}_entry"] = {
                "stream_id": str(sample_id),
                "field_count": len(sample_fields),
                "has_timestamp": b'timestamp' in sample_fields or 'timestamp' in sample_fields
            }
        
        # Process only the filtered results from Redis
        for stream_id, fields in stream_data:
            try:
                processed_count += 1
                
                # Fast conversion - avoid multiple isinstance checks
                record = {}
                for k, v in fields.items():
                    key = k.decode('utf-8') if isinstance(k, bytes) else k
                    value = v.decode('utf-8') if isinstance(v, bytes) else v
                    record[key] = value
                
                # Get timestamp for additional validation (if needed)
                timestamp_str = record.get('timestamp', '')
                if not timestamp_str:
                    continue
                
                # Additional string-based validation for edge cases
                # (Most filtering already done by Redis XRANGE)
                if redis_start_ts and timestamp_str < redis_start_ts:
                    continue
                if redis_end_ts and timestamp_str > redis_end_ts:
                    continue
                
                # Add minimal metadata
                record.update({
                    'stream_id': stream_id.decode('utf-8') if isinstance(stream_id, bytes) else str(stream_id),
                    'data_type': stream_name.split(':')[1],  # 'bms' or 'energy'
                    'source_stream': stream_name
                })
                
                records.append(record)
                filtered_count += 1
                
            except Exception as e:
                # Only log first few errors in debug mode
                if debug_mode and debug_info.get("processing_steps") is not None and processed_count <= 3:
                    debug_info["processing_steps"].append(f"Error processing {stream_name} entry: {str(e)[:50]}")
                continue
                
    except Exception as e:
        if debug_info.get("processing_steps") is not None:
            debug_info["processing_steps"].append(f"Error retrieving {stream_name}: {str(e)[:50]}")
    
    return {
        'records': records,
        'raw_count': raw_count,
        'processed_count': processed_count,
        'filtered_count': filtered_count
    }

def convert_to_redis_timestamp_format(dt):
    """Convert datetime object to Redis timestamp format (YYYYMMDDTHHMMSS)"""
    return dt.strftime('%Y%m%dT%H%M%S') if dt else None

def paginate_data(data, limit, offset):
    """Memory-efficient data pagination"""
    total = len(data)
    if offset >= total:
        return {
            'records': [],
            'total_records': total,
            'page_info': {
                'limit': limit,
                'offset': offset,
                'has_next': False,
                'has_prev': offset > 0
            }
        }
    
    end = min(offset + limit, total)
    paginated = data[offset:end]
    
    return {
        'records': paginated,
        'total_records': total,
        'page_info': {
            'limit': limit,
            'offset': offset,
            'has_next': end < total,
            'has_prev': offset > 0
        }
    }


def delete_entries_by_timestamp(redis_conn, timestamp, match_type='exact', debug_mode=False):
    """
    Optimized delete Redis stream entries by timestamp with validation
    
    Parameters:
    - redis_conn: Redis connection object
    - timestamp: Timestamp to delete (exact match or prefix)
    - match_type: 'exact' or 'prefix'
    - debug_mode: Enable debug information
    
    Returns:
    - Dictionary with deletion results and validation
    """
    try:
        if not redis_conn:
            return {
                "error": "Redis connection unavailable",
                "bms_deleted": 0,
                "energy_deleted": 0,
                "total_deleted": 0,
                "timestamp_exists": False
            }
        
        result = {
            "bms_deleted": 0,
            "energy_deleted": 0,
            "total_deleted": 0,
            "timestamp_exists": False,
            "debug_info": {} if debug_mode else None
        }
        
        if debug_mode:
            result["debug_info"] = {
                "timestamp_filter": timestamp,
                "match_type": match_type,
                "streams_processed": [],
                "entries_found": {},
                "validation_method": "fast_search_before_delete"
            }
        
        # First, validate if timestamp exists (fast validation)
        timestamp_found = False
        
        # Process both streams with optimized validation and deletion
        for stream_name, stream_key in [('bms', 'stream:bms'), ('energy', 'stream:energy')]:
            deleted_count = 0
            stream_has_timestamp = False
            
            try:
                # Check if stream exists first
                try:
                    stream_info = redis_conn.xinfo_stream(stream_key)
                    total_entries = stream_info['length']
                    if total_entries == 0:
                        continue
                except:
                    continue  # Stream doesn't exist, skip
                
                if debug_mode:
                    result["debug_info"]["streams_processed"].append(stream_name)
                    result["debug_info"]["entries_found"][stream_name] = total_entries
                
                # Optimized search: Use XRANGE with efficient scanning
                if match_type == 'exact':
                    # For exact match, use more efficient chunked scanning
                    chunk_size = 100
                    start_id = "-"
                    entries_to_delete = []
                    
                    while True:
                        # Get chunk of entries
                        chunk = redis_conn.xrange(stream_key, min=start_id, count=chunk_size)
                        if not chunk:
                            break
                        
                        # Scan chunk for exact timestamp match
                        for entry_id, fields in chunk:
                            # Fast field extraction
                            timestamp_field = fields.get(b'timestamp') or fields.get('timestamp')
                            if timestamp_field:
                                entry_timestamp = timestamp_field.decode('utf-8') if isinstance(timestamp_field, bytes) else timestamp_field
                                
                                if entry_timestamp == timestamp:
                                    entries_to_delete.append(entry_id)
                                    stream_has_timestamp = True
                                    timestamp_found = True
                        
                        # If we found matches in exact mode, we can stop after this chunk
                        if stream_has_timestamp and match_type == 'exact':
                            break
                            
                        # Update start_id for next chunk
                        start_id = f"({chunk[-1][0].decode('utf-8') if isinstance(chunk[-1][0], bytes) else str(chunk[-1][0])}"
                        
                elif match_type == 'prefix':
                    # For prefix match, scan all but with optimized field access
                    chunk_size = 100
                    start_id = "-"
                    entries_to_delete = []
                    
                    while True:
                        chunk = redis_conn.xrange(stream_key, min=start_id, count=chunk_size)
                        if not chunk:
                            break
                            
                        for entry_id, fields in chunk:
                            timestamp_field = fields.get(b'timestamp') or fields.get('timestamp')
                            if timestamp_field:
                                entry_timestamp = timestamp_field.decode('utf-8') if isinstance(timestamp_field, bytes) else timestamp_field
                                
                                if entry_timestamp.startswith(timestamp):
                                    entries_to_delete.append(entry_id)
                                    stream_has_timestamp = True
                                    timestamp_found = True
                        
                        # Update start_id for next chunk
                        start_id = f"({chunk[-1][0].decode('utf-8') if isinstance(chunk[-1][0], bytes) else str(chunk[-1][0])}"
                
                # Delete matching entries in batch
                if entries_to_delete:
                    # Delete in chunks if there are many entries
                    if len(entries_to_delete) > 100:
                        for i in range(0, len(entries_to_delete), 100):
                            chunk_to_delete = entries_to_delete[i:i+100]
                            deleted_count += redis_conn.xdel(stream_key, *chunk_to_delete)
                    else:
                        deleted_count = redis_conn.xdel(stream_key, *entries_to_delete)
                
                # Update result
                if stream_name == 'bms':
                    result["bms_deleted"] = deleted_count
                else:
                    result["energy_deleted"] = deleted_count
                    
                if debug_mode and entries_to_delete:
                    if "matches_found" not in result["debug_info"]:
                        result["debug_info"]["matches_found"] = {}
                    result["debug_info"]["matches_found"][stream_name] = len(entries_to_delete)
                    
            except Exception as e:
                if debug_mode:
                    if "errors" not in result["debug_info"]:
                        result["debug_info"]["errors"] = {}
                    result["debug_info"]["errors"][stream_name] = str(e)
        
        result["total_deleted"] = result["bms_deleted"] + result["energy_deleted"]
        result["timestamp_exists"] = timestamp_found
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "bms_deleted": 0,
            "energy_deleted": 0,
            "total_deleted": 0,
            "timestamp_exists": False
        }
