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

### 13. SNMP Monitoring

#### 13.1. SNMP Get Single OID
**Endpoint:** `POST /api/v1/snmp/get`

**Request Body:**
```json
{
    "ip": "192.168.1.100",
    "community": "public",
    "oid": ".1.3.6.1.2.1.25.1.11",
    "version": "1",
    "timeout": 5
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "ip": "192.168.1.100",
        "community": "public",
        "oid": ".1.3.6.1.2.1.25.1.11",
        "value": "12.5",
        "raw_output": "SNMPv2-SMI::enterprises.1.3.6.1.2.1.25.1.11 = STRING: 12.5",
        "timestamp": "2025-08-15T10:30:00"
    }
}
```

#### 13.2. SNMP Bulk Get Multiple OIDs
**Endpoint:** `POST /api/v1/snmp/bulk-get`

**Request Body:**
```json
{
    "ip": "192.168.1.100",
    "community": "public",
    "oids": [
        ".1.3.6.1.2.1.25.1.11",
        ".1.3.6.1.2.1.25.1.12",
        ".1.3.6.1.2.1.25.1.13"
    ],
    "version": "1",
    "timeout": 5
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "ip": "192.168.1.100",
        "community": "public",
        "total_oids": 3,
        "successful_oids": 3,
        "failed_oids": 0,
        "results": {
            ".1.3.6.1.2.1.25.1.11": {
                "success": true,
                "value": "12.5",
                "raw_output": "...",
                "timestamp": "2025-08-15T10:30:00"
            },
            ".1.3.6.1.2.1.25.1.12": {
                "success": true,
                "value": "24.8",
                "raw_output": "...",
                "timestamp": "2025-08-15T10:30:00"
            }
        },
        "timestamp": "2025-08-15T10:30:00"
    }
}
```

#### 13.3. SNMP Connection Test
**Endpoint:** `POST /api/v1/snmp/test-connection`

**Request Body:**
```json
{
    "ip": "192.168.1.100",
    "community": "public",
    "version": "1",
    "timeout": 5
}
```

**Response:**
```json
{
    "success": true,
    "message": "SNMP connection successful",
    "data": {
        "ip": "192.168.1.100",
        "community": "public",
        "test_oid": ".1.3.6.1.2.1.1.3.0",
        "uptime": "123456789",
        "timestamp": "2025-08-15T10:30:00"
    }
}
```

#### 13.4. SNMP OID Information
**Endpoint:** `GET /api/v1/snmp/info`

**Response:**
```json
{
    "success": true,
    "data": {
        "total_oids": 15,
        "oids": [
            {
                "oid": ".1.3.6.1.2.1.25.1.11",
                "name": "pv1_voltage",
                "label": "PV1 Voltage",
                "unit": "V",
                "description": "Photovoltaic 1 voltage measurement"
            },
            {
                "oid": ".1.3.6.1.2.1.25.1.12",
                "name": "pv2_voltage",
                "label": "PV2 Voltage",
                "unit": "V",
                "description": "Photovoltaic 2 voltage measurement"
            }
        ],
        "supported_versions": ["1", "2c"],
        "default_community": "public",
        "default_timeout": 5
    }
}
```

### 14. Power Management

#### 14.1. Power System Overview
**Endpoint:** `GET /api/v1/power/overview`

**Response:**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "disk_usage": {
            "free": 11.4,
            "used": 1.8,
            "total": 13.2,
            "unit": "GB"
        },
        "uptime": "1 day, 20 minutes",
        "auto_reboot": 1,
        "last_operation": "reboot",
        "last_update": "2025-08-15 10:30:00"
    }
}
```

#### 14.2. Log Disk Alert
**Endpoint:** `POST /api/v1/power/disk-alert`

**Request Body:**
```json
{
    "timestamp": "2025-08-15T10:30:00",
    "type": "warning",
    "disk_usage": 85,
    "message": "Disk usage exceeded 80% threshold"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Disk alert logged successfully"
}
```

#### 14.3. Log Auto Reboot Event
**Endpoint:** `POST /api/v1/power/auto-reboot-log`

**Request Body:**
```json
{
    "timestamp": "2025-08-15T10:30:00",
    "disk_usage": 90,
    "action": "auto_reboot",
    "status": "initiated",
    "message": "Auto reboot triggered due to high disk usage"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Auto reboot logged successfully"
}
```

#### 14.4. Get Auto Reboot Statistics
**Endpoint:** `GET /api/v1/power/auto-reboot-stats`

**Response:**
```json
{
    "success": true,
    "data": {
        "monthly_count": 3,
        "total_count": 15,
        "last_reboot": {
            "timestamp": "2025-08-15T08:30:00",
            "disk_usage": 92
        }
    }
}
```

#### 14.5. Get Auto Reboot History
**Endpoint:** `GET /api/v1/power/auto-reboot-history`

**Query Parameters:**
- `from` (optional): Start date (YYYY-MM-DD format)
- `to` (optional): End date (YYYY-MM-DD format)
- `limit` (optional): Maximum number of records

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "timestamp": "2025-08-15T08:30:00",
            "disk_usage": 92,
            "action": "auto_reboot",
            "status": "completed",
            "message": "Auto reboot completed successfully"
        },
        {
            "timestamp": "2025-08-14T15:45:00",
            "disk_usage": 89,
            "action": "auto_reboot",
            "status": "initiated",
            "message": "Auto reboot triggered due to high disk usage"
        }
    ]
}
```

#### 14.6. Export Auto Reboot History
**Endpoint:** `GET /api/v1/power/auto-reboot-history/export`

**Query Parameters:**
- `from` (optional): Start date (YYYY-MM-DD format)
- `to` (optional): End date (YYYY-MM-DD format)

**Response:**
CSV file download with columns: Timestamp, Disk Usage (%), Action, Status, Message

#### 14.7. Get Auto Reboot Settings
**Endpoint:** `GET /api/v1/power/settings`

**Response:**
```json
{
    "success": true,
    "data": {
        "auto_reboot_enabled": true,
        "disk_threshold": 85,
        "check_interval": 300,
        "reboot_delay": 60,
        "last_modified": "2025-08-15T10:30:00",
        "modified_by": "admin"
    }
}
```

#### 14.8. Update Auto Reboot Settings
**Endpoint:** `POST /api/v1/power/settings`

**Request Body:**
```json
{
    "user": "admin",
    "password": "admin",
    "settings": {
        "auto_reboot_enabled": true,
        "disk_threshold": 90,
        "check_interval": 600,
        "reboot_delay": 120
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Auto reboot settings updated successfully",
    "data": {
        "auto_reboot_enabled": true,
        "disk_threshold": 90,
        "check_interval": 600,
        "reboot_delay": 120,
        "last_modified": "2025-08-15T10:30:00",
        "modified_by": "admin"
    }
}
```

#### 14.9. System Reboot
**Endpoint:** `POST /api/v1/power/reboot`

**Request Body:**
```json
{
    "user": "admin",
    "password": "admin"
}
```

**Response:**
```json
{
    "success": true,
    "message": "System reboot initiated",
    "data": {
        "action": "reboot",
        "initiated_by": "admin",
        "timestamp": "2025-08-15T10:30:00"
    }
}
```

#### 14.10. System Shutdown
**Endpoint:** `POST /api/v1/power/shutdown`

**Request Body:**
```json
{
    "user": "admin",
    "password": "admin"
}
```

**Response:**
```json
{
    "success": true,
    "message": "System shutdown initiated",
    "data": {
        "action": "shutdown",
        "initiated_by": "admin",
        "timestamp": "2025-08-15T10:30:00"
    }
}
```

### 16. I2C Communication Management

#### 16.1. Get I2C Settings
**Endpoint:** `GET /api/v1/power/i2c/settings`

**Response:**
```json
{
    "success": true,
    "data": {
        "interval_minutes": 2,
        "address": "0x28",
        "enabled": true,
        "last_modified": "2025-08-22T10:30:00",
        "modified_by": "admin"
    }
}
```

#### 16.2. Update I2C Settings
**Endpoint:** `POST /api/v1/power/i2c/settings`

**Request Body:**
```json
{
    "user": "admin",
    "password": "admin",
    "settings": {
        "interval_minutes": 5,
        "address": "0x28",
        "enabled": true
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "I2C settings updated successfully",
    "data": {
        "interval_minutes": 5,
        "address": "0x28",
        "enabled": true,
        "last_modified": "2025-08-22T10:30:00",
        "modified_by": "admin"
    }
}
```

#### 16.3. Test I2C Communication
**Endpoint:** `POST /api/v1/power/i2c/test`

**Request Body:**
```json
{
    "address": "0x28",
    "message": "H"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "address": "0x28",
        "message_sent": "H",
        "response": "OK",
        "timestamp": "2025-08-22T10:30:00",
        "status": "success"
    }
}
```

#### 16.4. Get I2C Communication Logs
**Endpoint:** `GET /api/v1/power/i2c/logs`

**Query Parameters:**
- `limit` (optional): Maximum number of logs to return (default: 50)

**Response:**
```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "timestamp": "2025-08-22T10:30:00",
                "address": "0x28",
                "message": "H",
                "response": "OK",
                "status": "success"
            },
            {
                "timestamp": "2025-08-22T10:28:00",
                "address": "0x28",
                "message": "H",
                "response": "TIMEOUT",
                "status": "error"
            }
        ],
        "total_logs": 2
    }
}
```

### 15. Power Operation

**Endpoint** `GET /api/v1/power/overview`

**Response**
```json
{
    "status_code": 200,
    "status": "success",
    "data": {
        "disk_usage": {
            "free": 11.4,
            "total": 13.8,
            "unit": "GB",
            "used": 1.8
        },
        "uptime": "1 day, 20 minutes",
        "auto_reboot": 1,
        "last_operation": 
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

### SNMP Get Single OID
```bash
curl -X POST "http://your-domain/api/v1/snmp/get" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "ip": "192.168.1.100",
    "community": "public",
    "oid": ".1.3.6.1.2.1.25.1.11",
    "version": "1",
    "timeout": 5
  }'
```

### SNMP Bulk Get Multiple OIDs
```bash
curl -X POST "http://your-domain/api/v1/snmp/bulk-get" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "ip": "192.168.1.100",
    "community": "public",
    "oids": [".1.3.6.1.2.1.25.1.11", ".1.3.6.1.2.1.25.1.12"],
    "version": "1",
    "timeout": 5
  }'
```

### Test SNMP Connection
```bash
curl -X POST "http://your-domain/api/v1/snmp/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "ip": "192.168.1.100",
    "community": "public",
    "version": "1",
    "timeout": 5
  }'
```

### Get Power System Overview
```bash
curl -X GET "http://your-domain/api/v1/power/overview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token"
```

### Get Auto Reboot Statistics
```bash
curl -X GET "http://your-domain/api/v1/power/auto-reboot-stats" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token"
```

### Update Auto Reboot Settings
```bash
curl -X POST "http://your-domain/api/v1/power/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "user": "admin",
    "password": "admin",
    "settings": {
      "auto_reboot_enabled": true,
      "disk_threshold": 90,
      "check_interval": 600,
      "reboot_delay": 120
    }
  }'
```

### System Reboot
```bash
curl -X POST "http://your-domain/api/v1/power/reboot" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "user": "admin",
    "password": "admin"
  }'
```

### Export Auto Reboot History
```bash
curl -X GET "http://your-domain/api/v1/power/auto-reboot-history/export?from=2025-08-01&to=2025-08-15" \
  -H "Authorization: Bearer your-token" \
  -o "auto_reboot_history.csv"
```

### Get I2C Settings
```bash
curl -X GET "http://your-domain/api/v1/power/i2c/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token"
```

### Update I2C Settings
```bash
curl -X POST "http://your-domain/api/v1/power/i2c/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "user": "admin",
    "password": "admin",
    "settings": {
      "interval_minutes": 5,
      "address": "0x28",
      "enabled": true
    }
  }'
```

### Test I2C Communication
```bash
curl -X POST "http://your-domain/api/v1/power/i2c/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "address": "0x28",
    "message": "H"
  }'
```

### Get I2C Communication Logs
```bash
curl -X GET "http://your-domain/api/v1/power/i2c/logs?limit=50" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token"
```

## Notes

- All JSON responses are formatted with proper indentation for readability
- Numeric values are returned as actual numbers, not strings
- Status values use consistent naming conventions (e.g., "normal", "running", "active")
- Complex nested structures are used for alarm statuses to provide detailed information
- Error handling follows HTTP status code conventions

### SNMP API Notes
- All SNMP endpoints require authentication via Bearer token
- IP address validation is performed on all requests
- OID format validation ensures proper SNMP syntax
- Timeout values are limited to 1-30 seconds range
- Bulk GET operations are limited to 50 OIDs maximum
- Supported SNMP versions: 1, 2c
- Default community string: "public"

### Power Management API Notes
- All Power Management endpoints require authentication via Bearer token
- Password validation is required for sensitive operations (reboot, shutdown, settings update)
- Valid user roles: apt, teknisi, admin
- Auto reboot settings include disk threshold monitoring
- Disk usage alerts are logged to SQLite database
- CSV export functionality available for historical data
- System uptime tracking included in overview
- Power operations are logged with user attribution

### I2C Communication API Notes
- All I2C endpoints require authentication via Bearer token
- Password validation is required for I2C settings updates
- Valid user roles: apt, teknisi, admin
- I2C address must be in hexadecimal format (e.g., "0x28")
- Monitoring interval can be set between 1-60 minutes
- I2C communication logs include timestamps and status
- Test endpoint allows manual I2C communication testing
- Settings are persistent across system reboots
- Default I2C address: 0x28, default interval: 2 minutes

### Authentication Users
- **apt**: Password from APT_PASSWORD environment variable (default: 'powerapt')
- **teknisi**: Password from TEKNISI_PASSWORD environment variable (default: 'Joulestore2020')
- **admin**: Password from ADMIN_PASSWORD environment variable (default: 'admin')
