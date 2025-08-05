# API Documentation for JSPro Powerdesk

This document provides an overview of the JSPro Powerdesk API, detailing its structure, endpoints, and usage examples. The API is designed to facilitate interactions with the JSPro Powerdesk system, allowing developers to integrate and extend its functionalities.

## API Response Structure

All API responses follow a consistent structure:

```json
{
    "status_code": 200,
    "status": "success",
    "data": {...}
}
```

## Endpoints

### 1. System Resources & Service Status

**Endpoint:** `GET /api/v1/device/system-resources`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "cpu_usage": 40,
        "memory_usage": 50,
        "temperature": 27.2,
        "disk_usage": {
            "free": 8.6,
            "used": 6.1,
            "total": 15.4,
            "unit": "GB"
        },
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 2. Device Information

**Endpoint:** `GET /api/v1/device/information`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "site_information": {
            "site_id": "PAP9999",
            "site_name": "Site Name",
            "address": "Jl. Bakti No. 1"
        },
        "device_version": {
            "ehub_version": "new",
            "panel2_type": "new",
            "site_type": "bakti",
            "scc_type": "scc-epveper",
            "scc_source": "serial",
            "scc_id": [2, 1],
            "battery_type": "talis5"
        },
        "device_model": {
            "model": "JSPro MPPT",
            "part_number": "JP-MPPT-40A",
            "serial_number": "SN123456789",
            "software_version": "2.0.0",
            "hardware_version": "2.0.0"
        },
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 3. Systemd Service Status

**Endpoint:** `GET /api/v1/device/systemd-status`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "active_service": 10,
        "inactive_service": 2,
        "failed_service": 0,
        "services_status": {
            "mqtt_publish.service": "active",
            "redis.service": "active",
            "thread_bms.service": "active",
            "scc.service": "active",
            "scc_logs.service": "inactive",
            "scc_logs.timer": "active"
        },
        "system_uptime": "2d 2h",
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 4. Monitoring SCC Data

**Endpoint:** `GET /api/v1/monitoring/scc`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "scc1": {
            "scc_id": 1,
            "battery_temperature": 22,
            "counter_heartbeat": 3,
            "device_temperature": 25,
            "load_status": "is running",
            "pv_current": 3.3,
            "pv_voltage": 69.9,
            "load_voltage": 55.67,
            "load_current": 1.68,
            "load_power": 273,
            "alarm_status": {
                "battery_status": {
                    "battery_condition": "normal",
                    "battery_temperature": "normal",
                    "battery_inner_resistance": "normal",
                    "battery_identification": "normal"
                },
                "charging_status": {
                    "charging_state": "running",
                    "charging_condition": "normal",
                    "charging_status": "no_charging",
                    "pv_input_short": "normal",
                    "disequilibrium": "normal",
                    "load_mosfet_short": "normal",
                    "load_short": "normal",
                    "load_over_current": "normal",
                    "input_over_current": "normal",
                    "anti_reverse_mosfet": "normal",
                    "charging_anti_reverse_mosfet": "normal",
                    "charging_mosfet_short": "normal",
                    "input_voltage_status": "normal"
                },
                "discharging_status": {
                    "discharging_state": "running",
                    "discharging_condition": "normal",
                    "boost_voltage": "normal",
                    "high_voltage_side": "normal",
                    "input_voltage": "normal",
                    "output_voltage": "normal",
                    "stop_discharging": "normal",
                    "discharge_short": "normal",
                    "discharging_output": "normal",
                    "output_power": "light_load"
                }
            }
        },
        "scc2": {
            "scc_id": 2,
            "battery_temperature": 19,
            "counter_heartbeat": -1,
            "device_temperature": 24,
            "load_status": "is running",
            "pv_current": 3.1,
            "pv_voltage": 71.7,
            "load_voltage": 55.67,
            "load_current": 5.68,
            "load_power": 222,
            "alarm_status": {
                "battery_status": {
                    "battery_condition": "normal",
                    "battery_temperature": "normal",
                    "battery_inner_resistance": "normal",
                    "battery_identification": "normal"
                },
                "charging_status": {
                    "charging_state": "running",
                    "charging_condition": "normal",
                    "charging_status": "no_charging",
                    "pv_input_short": "normal",
                    "disequilibrium": "normal",
                    "load_mosfet_short": "normal",
                    "load_short": "normal",
                    "load_over_current": "normal",
                    "input_over_current": "normal",
                    "anti_reverse_mosfet": "normal",
                    "charging_anti_reverse_mosfet": "normal",
                    "charging_mosfet_short": "normal",
                    "input_voltage_status": "normal"
                },
                "discharging_status": {
                    "discharging_state": "running",
                    "discharging_condition": "normal",
                    "boost_voltage": "normal",
                    "high_voltage_side": "normal",
                    "input_voltage": "normal",
                    "output_voltage": "normal",
                    "stop_discharging": "normal",
                    "discharge_short": "normal",
                    "discharging_output": "normal",
                    "output_power": "light_load"
                }
            }
        },
        "relay_configuration": {
            "vsat_reconnect": 4700,
            "vsat_cutoff": 4600,
            "bts_reconnect": 4900,
            "bts_cutoff": 4800
        },
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 5. Monitoring Battery Data

**Endpoint:** `GET /api/v1/monitoring/battery`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "bms_data": [
            {
                "ambient_temperature": 338,
                "average_cell_temperature": 315,
                "cell_difference": 10,
                "cell_temperature": [
                    318,
                    313,
                    313
                ],
                "cell_voltage": [
                    3386,
                    3392,
                    3396,
                    3390,
                    3393,
                    3388,
                    3389,
                    3390,
                    3388,
                    3392,
                    3396,
                    3393,
                    3390,
                    3386,
                    3387,
                    3389
                ],
                "counter": 9,
                "cycle_count": 1,
                "environment_temperature": 338,
                "error_messages": [
                    "Pack voltage 5424 exceeds limit 5325",
                    "Max cell voltage 3396 exceeds limit 425 at indices [2, 10]",
                    "Min cell voltage 3386 exceeds limit 375 at indices [0, 13]",
                    "Cell difference 10 below limit 300",
                    "Max cell temperature 318 exceeds limit 240 at indices [0]",
                    "Min cell temperature 313 exceeds limit 230 at indices [1, 2]",
                    "FET temperature 318 exceeds limit 250"
                ],
                "fault_status_flag": [
                    "state of charge",
                    "charge Mosfet ON",
                    "discharge Mosfet ON",
                    "charge limit current function is ON"
                ],
                "fet_temperature": 318,
                "full_charged_capacity": 108,
                "max_cell_temperature": 318,
                "max_cell_voltage": 3396,
                "min_cell_temperature": 313,
                "min_cell_voltage": 3386,
                "pack_current": 35,
                "pack_voltage": 5424,
                "pcb_code": "TBI24032703195",
                "port": "usb0",
                "protection_flag": [
                    "no alarm detected"
                ],
                "remaining_capacity": 108,
                "remaining_charge_time": 0,
                "remaining_discharge_time": 65535,
                "slave_id": 1,
                "sn1_code": "AO67950111",
                "soc": 10000,
                "soh": 10000,
                "warning_flag": [
                    "no alarm detected"
                ]
            },
            {
                "ambient_temperature": 337,
                "average_cell_temperature": 315,
                "cell_difference": 17,
                "cell_temperature": [
                    314,
                    314,
                    315
                ],
                "cell_voltage": [
                    3388,
                    3387,
                    3386,
                    3386,
                    3386,
                    3388,
                    3389,
                    3390,
                    3385,
                    3395,
                    3388,
                    3385,
                    3387,
                    3387,
                    3402,
                    3385
                ],
                "counter": 9,
                "cycle_count": 2,
                "environment_temperature": 337,
                "error_messages": [
                    "Pack voltage 5421 exceeds limit 5325",
                    "Max cell voltage 3402 exceeds limit 425 at indices [14]",
                    "Min cell voltage 3385 exceeds limit 375 at indices [8, 11, 15]",
                    "Cell difference 17 below limit 300",
                    "Max cell temperature 320 exceeds limit 240",
                    "Min cell temperature 314 exceeds limit 230 at indices [0, 1]",
                    "FET temperature 319 exceeds limit 250"
                ],
                "fault_status_flag": [
                    "state of charge",
                    "charge Mosfet ON",
                    "discharge Mosfet ON",
                    "charge limit current function is ON"
                ],
                "fet_temperature": 319,
                "full_charged_capacity": 108,
                "max_cell_temperature": 320,
                "max_cell_voltage": 3402,
                "min_cell_temperature": 314,
                "min_cell_voltage": 3385,
                "pack_current": 33,
                "pack_voltage": 5421,
                "pcb_code": "TBI24032703301",
                "port": "usb1",
                "protection_flag": [
                    "no alarm detected"
                ],
                "remaining_capacity": 108,
                "remaining_charge_time": 0,
                "remaining_discharge_time": 65535,
                "slave_id": 6,
                "sn1_code": "AO67950135",
                "soc": 10000,
                "soh": 10000,
                "warning_flag": [
                    "no alarm detected"
                ]
            },
        ],
        "last_update": "2025-07-18 10:10:23"
    },
}
```

### 6. Monitoring Battery Aktif

**Endpoint:** `GET /api/v1/monitoring/battery/active`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "bms_data": [
            {
                "slave_id": 1,
                "port": "usb0",
                "status": true
            },
            {
                "slave_id": 2,
                "port": "usb0",
                "status": true
            },
            {
                "slave_id": 3,
                "port": "usb0",
                "status": true
            },
            {
                "slave_id": 4,
                "port": "usb0",
                "status": true
            },
            {
                "slave_id": 5,
                "port": "usb0",
                "status": true
            },
            {
                "slave_id": 6,
                "port": "usb1",
                "status": true
            },
            {
                "slave_id": 7,
                "port": "usb1",
                "status": true
            },
            {
                "slave_id": 8,
                "port": "usb1",
                "status": true
            },
            {
                "slave_id": 9,
                "port": "usb1",
                "status": true
            },
            {
                "slave_id": 10,
                "port": "usb1",
                "status": true
            },
        ],
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 7. Historical Data - Redis Storage

#### 7.1. Get Redis Data Logs
**Endpoint:** `GET /api/v1/loggers/data/redis`

**Query Parameters:**
- `start_date` (optional): Start date for filtering (ISO 8601 format)
- `end_date` (optional): End date for filtering (ISO 8601 format)
- `limit` (optional): Maximum number of records to return
- `offset` (optional): Number of records to skip

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "records": [
            {
                "timestamp": "2025-07-21 10:30:00",
                "energy_data": {
                    "scc_voltage": 48.5,
                    "scc_current": 12.3,
                    "battery_voltage": 47.8,
                    "load_power": 250.5
                },
                "bms_data": [
                    {
                        "slave_id": 1,
                        "voltage": 3.65,
                        "current": 2.1,
                        "temperature": 25.4
                    }
                ]
            }
        ],
        "total_records": 150,
        "page_info": {
            "limit": 50,
            "offset": 0,
            "has_next": true
        },
        "last_update": "2025-07-21 10:30:00"
    }
}
```

#### 7.2. Store Data to Redis
**Endpoint:** `POST /api/v1/loggers/data/redis`

***notes***: Endpoint will adjust to the server


**Request Body:**
```json
{
    "site_id": "PAP9999",
    "site_name": "Sundaya RnD",
    "data": [
        {
            "timestamp": "2025-07-21 10:30:00",
            "energy_data": {
                "scc_voltage": 48.5,
                "scc_current": 12.3,
                "battery_voltage": 47.8,
                "load_power": 250.5
            },
            "bms_data": [
                {
                    "slave_id": 1,
                    "voltage": 3.65,
                    "current": 2.1,
                    "temperature": 25.4
                }
            ]
        }
    ]
}
```

**Response:**
```json
{
    "status_code": 201,
    "status": "success",
    "message": "Redis data stored successfully"
}
```

#### 7.3. Delete Redis Data
**Endpoint:** `DELETE /api/v1/loggers/data/redis/:timestamp`

**Response:**

**Success**
```json
{
    "data": {
        "bms_deleted": 10,
        "debug_info": null,
        "energy_deleted": 1,
        "total_deleted": 11
    },
    "message": "Successfully deleted entries with timestamp exactly matching '20250804T154003'",
    "status": "success",
    "status_code": 200
}
```

**Error 404 - ts not found**
```
{
    "data": {
        "bms_deleted": 0,
        "energy_deleted": 0,
        "timestamp_exists": false,
        "total_deleted": 0
    },
    "message": "Timestamp exact match '20250804T154003' not found in Redis streams",
    "status": "error",
    "status_code": 404
}
```

#### 7.4 Delete All Redis Data
**Endpoint:** `DELETE /api/v1/loggers/data/redis`

**Response:**
```json
{
    "data": {
        "bms_entries_deleted": 102856,
        "energy_entries_deleted": 8668,
        "total_deleted": 111524
    },
    "message": "All Redis stream data deleted successfully",
    "status": "success",
    "status_code": 200
}
```


### 8. Historical Data - SQLite Storage

#### 8.1. Get SQLite Data Logs
**Endpoint:** `GET /api/v1/loggers/data/sqlite`

**Query Parameters:**
- `start_date` (optional): Start date for filtering (ISO 8601 format)
- `end_date` (optional): End date for filtering (ISO 8601 format)
- `limit` (optional): Maximum number of records to return (default: 100)
- `offset` (optional): Number of records to skip (default: 0)
- `table` (optional): Specific table name to query

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "records": [
            {
                "id": 1,
                "timestamp": "2025-07-21 10:30:00",
                "energy_data": {
                    "scc_voltage": 48.5,
                    "scc_current": 12.3,
                    "battery_voltage": 47.8,
                    "load_power": 250.5
                },
                "bms_data": [
                    {
                        "slave_id": 1,
                        "voltage": 3.65,
                        "current": 2.1,
                        "temperature": 25.4
                    }
                ],
                "created_at": "2025-07-21 10:30:00"
            }
        ],
        "total_records": 1000,
        "page_info": {
            "limit": 100,
            "offset": 0,
            "has_next": true
        },
        "last_update": "2025-07-21 10:30:00"
    }
}
```

#### 8.2. Store Data to SQLite
**Endpoint:** `POST /api/v1/loggers/data/sqlite`

**Request Body:**
```json
{
    "site_id": "PAP9999",
    "site_name": "Sundaya RnD",
    "table_name": "energy_logs",
    "data": [
        {
            "timestamp": "2025-07-21 10:30:00",
            "energy_data": {
                "scc_voltage": 48.5,
                "scc_current": 12.3,
                "battery_voltage": 47.8,
                "load_power": 250.5
            },
            "bms_data": [
                {
                    "slave_id": 1,
                    "voltage": 3.65,
                    "current": 2.1,
                    "temperature": 25.4
                }
            ]
        }
    ]
}
```

**Response:**
```json
{
    "status_code": 201,
    "status": "success",
    "message": "SQLite data stored successfully",
}
```

#### 8.3. Delete SQLite Data
**Endpoint:** `DELETE /api/v1/loggers/data/sqlite/:id`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "message": "SQLite data deleted successfully"
}
```

### 9. Historical Data - Storage Overview

**Endpoint** `GET /api/v1/loggers/data/overview`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "storage_overview": {
            "redis_storage": 22,
            "sqlite_storage": 133,
            "disk_usage": {
                "free": 8.6,
                "used": 6.1,
                "total": 15.4
            },
        },
        "data_statistics": {
            "logger_records": 22,
            "sqlite_records": 100,
        },
        "last_update": "2025-07-18 10:10:23"
    }
}
```

### 10. SCC Alarm Log - Overview

**Endpoint** `GET /api/v1/loggers/scc-alarm/overview`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "data_statistics": {
            "total_alarm_logs": 100,
            "last_update": "2025-07-18 10:10:23"
        }
    }
}
```

### 11. SCC Alarm Log - Alarm Log History

**Endpoint** `GET /api/v1/loggers/scc-alarm/history`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "logger_records": 100,
        "logs": [
            {
                "device": "scc2",
                "alarm": "batt_overdisc",
                "battery_temperature": 25,
                "battery_voltage": 5333,
                "device_temperature": 28,
                "load_status": "is standby",
                "timestamp": "2025-07-21 10:30:00"
            },
            {
                "device": "scc2",
                "alarm": "batt_undervolt",
                "battery_temperature": 25,
                "battery_voltage": 5333,
                "device_temperature": 28,
                "load_status": "is standby",
                "timestamp": "2025-07-21 10:30:00"
            },
        ],
        "page_info": {
            "limit": 50,
            "offset": 0,
            "has_next": true
        },
        "last_update": "2025-07-21 10:30:00"
    }
}
```

### 12. SCC Alarm Log - Download Alarm Logs

**Endpoint** `GET /api/v1/loggers/scc-alarm`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "logger_records": 100,
        "last_update": "2025-07-18 10:10:23",
        "logs": [
            {
                "scc1": {
                    "alarm": {},
                    "battery_temperature": 25,
                    "battery_voltage": 5827,
                    "device_temperature": 25,
                    "load": {
                        "bts_curr": 4.95,
                        "obl": 0.02,
                        "relay_state": {
                            "bts": true,
                            "obl": true,
                            "vsat": true
                        },
                        "vsat_curr": 1.6
                    },
                    "load_status": "is running"
                },
                "scc2": {
                    "alarm": {},
                    "battery_temperature": 25,
                    "battery_voltage": 5827,
                    "device_temperature": 25,
                    "load": {
                        "bts_curr": 4.95,
                        "obl": 0.02,
                        "relay_state": {
                            "bts": true,
                            "obl": true,
                            "vsat": true
                        },
                        "vsat_curr": 1.6
                    },
                    "load_status": "is running"
                }
            }
        ]
    }
}
```

### 12. SCC Alarm Logs - Clear Alarms

**Endpoint** `DELETE /api/v1/loggers/scc-alarm`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "message": "SCC Alarm data deleted successfully"
}
```


## Error Responses

All endpoints follow the same error response format:

```json
{
    "status_code": 400|401|404|500,
    "message": "Error description",
    "data": null
}
```

### Common Error Codes:
- **400 Bad Request**: Invalid parameters or request format
- **401 Unauthorized**: Authentication required or invalid credentials
- **404 Not Found**: Requested resource not found
- **500 Internal Server Error**: Server-side error

## Request/Response Standards

### Date Format
- All timestamps should use format: `YYYY-MM-DDTHH:mm:ss`

### Data Types
- **Numbers**: Float values for measurements (voltage, current, power, temperature)
- **Strings**: Status values, descriptions, and identifiers
- **Arrays**: Lists of SCC IDs, alarm codes, etc.
- **Objects**: Nested data structures for complex information

### Authentication
- Some endpoints may require authentication headers
- Use Bearer token or session-based authentication

### Rate Limiting
- API requests may be rate-limited
- Check response headers for rate limit information

## Usage Examples

### Get System Resources
```bash
curl -X GET "http://your-domain/api/v1/dashboard/system-resources" \
  -H "Content-Type: application/json"
```

### Get Systemd Status
```bash
curl -X GET "http://your-domain/api/v1/dashboard/systemd-status" \
  -H "Content-Type: application/json"
```

### Get Device Information
```bash
curl -X GET "http://your-domain/api/v1/device/information" \
  -H "Content-Type: application/json"
```

### Get SCC Data
```bash
curl -X GET "http://your-domain/api/v1/monitoring/scc" \
  -H "Content-Type: application/json"
```

## Notes

- All JSON responses are formatted with proper indentation for readability
- Numeric values are returned as actual numbers, not strings
- Status values use consistent naming conventions (e.g., "normal", "running", "active")
- Complex nested structures are used for alarm statuses to provide detailed information
- Error handling follows HTTP status code conventions
