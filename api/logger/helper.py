# SQLite database path
from datetime import datetime
import sqlite3
import os
import redis
import sys
from ..redisconnection import connection as red

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', './data/powerdesk.db')

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
