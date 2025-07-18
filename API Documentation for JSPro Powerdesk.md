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
            "total": 15.4
        },
        "last_update": "2025-07-18T10:10:23"
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
        "last_update": "2025-07-18T10:10:23"
    }
}
```


### 3. Systemd Service Status

**Endpoint:** `GET /api/v1/systemd-status`

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
        "last_update": "2025-07-18T10:10:23"
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
        "last_update": "2025-07-18T10:10:23"
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
                "slave_id": 1,
                "port": "usb0",
            },
            {
                "slave_id": 2,
                "port": "usb0",
            },
            {
                "slave_id": 3,
                "port": "usb0",
            },
            {
                "slave_id": 4,
                "port": "usb0",
            },
            {
                "slave_id": 5,
                "port": "usb0",
            },
            {
                "slave_id": 6,
                "port": "usb1",
            },
            {
                "slave_id": 7,
                "port": "usb1",
            },
            {
                "slave_id": 8,
                "port": "usb1",
            },
            {
                "slave_id": 9,
                "port": "usb1",
            },
            {
                "slave_id": 10,
                "port": "usb1",
            },
        ],
        "last_update": "2025-07-18T10:10:23"
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
        "last_update": "2025-07-18T10:10:23Z"
    }
}
```


### 7. Historical Data - [GET] Data Logs

**Endpoint** `GET /api/v1/loggers/data`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": [
        {
            "energy_data": {},
            "bms_data": []
        },
        {
            "energy_data": {},
            "bms_data": []
        },
    ]
}
```


### 8. Historical Data - [POST] Data Logs

**Endpoint** `POST /api/v1/loggers/data`

**Body**
```json
{
    "site_id": "PAP9999",
    "site_name": "Sundaya RnD",
    "data": [
        {
            "energy_data": {},
            "bms_data": []
        },
        {
            "energy_data": {},
            "bms_data": []
        },
    ]
}
```

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "message": "loggers insert successfully"
}
```



### 9. Historical Data - [DELETE] Data Logs

**Endpoint** `DELETE /api/v1/loggers/data/:timestamp`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "message": "loggers deleted successfully"
}
```


### 10. Historical Data - Storage Overview

**Endpoint** `GET /api/v1/loggers/overview`

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
            "last_update": "2025-07-18T10:10:23"
        },
        "data_statistics": {
            "logger_records": 22,
            "sqlite_records": 100,
            "last_update": "2025-07-18T10:10:23"
        }
    }
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
- All timestamps should use ISO 8601 format: `YYYY-MM-DDTHH:mm:ssZ`
- Timezone: UTC

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
curl -X GET "http://your-domain/api/dashboard/system-resources" \
  -H "Content-Type: application/json"
```

### Get Systemd Status
```bash
curl -X GET "http://your-domain/api/dashboard/systemd-status" \
  -H "Content-Type: application/json"
```

### Get Device Information
```bash
curl -X GET "http://your-domain/api/device/information" \
  -H "Content-Type: application/json"
```

### Get SCC Data
```bash
curl -X GET "http://your-domain/api/scc/data" \
  -H "Content-Type: application/json"
```

## Notes

- All JSON responses are formatted with proper indentation for readability
- Numeric values are returned as actual numbers, not strings
- Status values use consistent naming conventions (e.g., "normal", "running", "active")
- Complex nested structures are used for alarm statuses to provide detailed information
- Error handling follows HTTP status code conventions
