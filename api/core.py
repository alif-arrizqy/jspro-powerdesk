from flask import jsonify, request
from . import api


def register_blueprints(app):
    """
    Register all API blueprints to the Flask app
    """
    # Import blueprints here to avoid circular imports
    from .device import device_bp
    from .monitoring import monitoring_bp
    # from .loggers import loggers_bp  # Uncomment when loggers blueprint is ready
    
    # Register error handlers first
    register_error_handlers(app)
    
    # Register core API blueprint with /api prefix to avoid conflicts
    app.register_blueprint(api, url_prefix='/api')
    
    # Register v1 API blueprints with URL prefixes
    app.register_blueprint(device_bp, url_prefix='/api/v1/device')
    app.register_blueprint(monitoring_bp, url_prefix='/api/v1/monitoring')
    # app.register_blueprint(loggers_bp, url_prefix='/api/v1/loggers')  # Uncomment when ready
    
    print("✅ All API blueprints registered successfully")


def register_error_handlers(app):
    """
    Register custom error handlers for the Flask app
    """
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        # Check if request is for API endpoint
        if request.path.startswith('/api/'):
            return jsonify({
                "status_code": 404,
                "status": "error",
                "message": "Endpoint not found",
                "error": {
                    "type": "NotFound",
                    "description": f"The requested endpoint '{request.path}' was not found on this server",
                    "requested_url": request.url,
                    "method": request.method,
                },
                "suggestion": "Please check the API documentation at /api/docs/ for available endpoints"
            }), 404
        else:
            # For non-API requests, return standard HTML 404
            return '''
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
            <title>404 Not Found</title>
            <h1>Not Found</h1>
            <p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
            <p><a href="/api/">API Documentation</a></p>
            ''', 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 Method Not Allowed errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                "status_code": 405,
                "status": "error",
                "message": "Method not allowed",
                "error": {
                    "type": "MethodNotAllowed",
                    "description": f"The method '{request.method}' is not allowed for endpoint '{request.path}'",
                    "requested_method": request.method,
                    "requested_url": request.url,
                }
            }), 405
        else:
            return '''
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
            <title>405 Method Not Allowed</title>
            <h1>Method Not Allowed</h1>
            <p>The method is not allowed for the requested URL.</p>
            ''', 405

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error"""
        if request.path.startswith('/api/'):
            return jsonify({
                "status_code": 500,
                "status": "error",
                "message": "Internal server error",
                "error": {
                    "type": "InternalServerError",
                    "description": "An unexpected error occurred on the server",
                    "requested_url": request.url,
                    "method": request.method
                }
            }), 500
        else:
            return '''
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
            <title>500 Internal Server Error</title>
            <h1>Internal Server Error</h1>
            <p>The server encountered an internal error and was unable to complete your request.</p>
            ''', 500

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                "status_code": 401,
                "status": "error",
                "message": "Authentication required",
                "error": {
                    "type": "Unauthorized",
                    "description": "Authentication is required to access this endpoint",
                    "requested_url": request.url,
                    "method": request.method,
                    "authentication": {
                        "type": "Bearer Token",
                        "header": "Authorization",
                        "format": "Bearer <token>",
                        "example": "Authorization: Bearer your-secret-token"
                    }
                }
            }), 401
        else:
            return '''
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
            <title>401 Unauthorized</title>
            <h1>Unauthorized</h1>
            <p>Authentication is required to access this resource.</p>
            ''', 401

    print("✅ Error handlers registered successfully")

# ============== Base API Routes v1 ===========================
@api.route('/info', methods=['GET'])
def api_v1_info():
    """Base API v1 information endpoint"""
    return jsonify({
        "status_code": 200,
        "status": "success",
        "data": {
            "api_version": "v1",
            "service": "JSPro Powerdesk API",
            "description": "Centralized API management with modular blueprint architecture",
            "modules": {
                "device": {
                    "url_prefix": "/api/v1/device",
                    "description": "Device management and system information",
                    "endpoints": [
                        "/system-resources",
                        "/information", 
                        "/systemd-status"
                    ]
                },
                "monitoring": {
                    "url_prefix": "/api/v1/monitoring",
                    "description": "SCC and Battery monitoring data",
                    "endpoints": [
                        "/scc",
                        "/battery",
                        "/battery/active"
                    ]
                }
            },
            "documentation": "See API Documentation for JSPro Powerdesk.md"
        }
    }), 200


@api.route('/v1/device', methods=['GET'])
def device_module_info():
    """Device module information endpoint"""
    return jsonify({
        "status_code": 200,
        "status": "success",
        "data": {
            "module": "device",
            "description": "Device management and system information",
            "base_url": "/api/v1/device",
            "endpoints": [
                {
                    "path": "/api/v1/device/system-resources",
                    "method": "GET",
                    "description": "Get system resource usage (CPU, memory, disk, temperature)",
                    "authentication": "required"
                },
                {
                    "path": "/api/v1/device/information", 
                    "method": "GET",
                    "description": "Get device information, site details, and hardware configuration",
                    "authentication": "required"
                },
                {
                    "path": "/api/v1/device/systemd-status",
                    "method": "GET", 
                    "description": "Get systemd services status and system uptime",
                    "authentication": "required"
                }
            ]
        }
    }), 200


@api.route('/v1/monitoring', methods=['GET'])
def monitoring_module_info():
    """Monitoring module information endpoint"""
    return jsonify({
        "status_code": 200,
        "status": "success", 
        "data": {
            "module": "monitoring",
            "description": "SCC and Battery monitoring data",
            "base_url": "/api/v1/monitoring",
            "endpoints": [
                {
                    "path": "/api/v1/monitoring/scc",
                    "method": "GET",
                    "description": "Get Solar Charge Controller monitoring data",
                    "authentication": "required"
                },
                {
                    "path": "/api/v1/monitoring/battery",
                    "method": "GET",
                    "description": "Get battery monitoring data for all BMS units",
                    "authentication": "required"
                },
                {
                    "path": "/api/v1/monitoring/battery/active",
                    "method": "GET",
                    "description": "Get active battery status information",
                    "authentication": "required"
                }
            ]
        }
    }), 200


# ============== Wildcard Route for Unknown API Endpoints ===========================
@api.route('/<path:unknown_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def api_not_found(unknown_path):
    """Handle unknown API endpoints"""
    return jsonify({
        "status_code": 404,
        "status": "error",
        "message": "API endpoint not found",
        "error": {
            "type": "EndpointNotFound",
            "requested_path": f"/api/{unknown_path}",
            "requested_method": request.method,
            "description": "The requested API endpoint does not exist",
            "suggestions": [
                "Check the endpoint spelling",
                "Verify the API version (currently v1)",
                "Ensure you're using the correct HTTP method",
                "Review the API documentation"
            ],
            "available_endpoints": {
                "api_info": {
                    "path": "/api/",
                    "description": "Get API information and available modules"
                },
                "device_module": {
                    "path": "/api/v1/device/",
                    "description": "Device management endpoints"
                },
                "monitoring_module": {
                    "path": "/api/v1/monitoring/",
                    "description": "Monitoring data endpoints"
                }
            }
        }
    }), 404


# ============== Device Routes (v1) ===========================
# These routes are now handled by the device blueprint in api/device/api_device.py
# The device blueprint is registered with URL prefix '/api/v1/device'

# Available device endpoints:
# GET /api/v1/device/system-resources
# GET /api/v1/device/information  
# GET /api/v1/device/systemd-status


# ============== Monitoring Routes (v1) ===========================
# These routes are now handled by the monitoring blueprint in api/monitoring/api_monitoring.py
# The monitoring blueprint is registered with URL prefix '/api/v1/monitoring'

# Available monitoring endpoints:
# GET /api/v1/monitoring/scc
# GET /api/v1/monitoring/battery
# GET /api/v1/monitoring/battery/active
