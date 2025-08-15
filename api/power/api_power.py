"""
Power Management API endpoints
Base URL: /api/v1/power
"""

import json
import os
from flask import jsonify, request, Response
from . import power_bp
from auths import token_auth as auth
from .helper import PowerManagementAPI


# Global instance
power_api = PowerManagementAPI()


@power_bp.route('/overview', methods=['GET'])
@auth.login_required
def get_overview():
    """Get system overview"""
    result = power_api.get_overview()
    return jsonify(result), result['status_code']


@power_bp.route('/disk-alert', methods=['POST'])
@auth.login_required
def log_disk_alert():
    """Log disk alert"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    return jsonify(power_api.log_disk_alert(data))


@power_bp.route('/auto-reboot-log', methods=['POST'])
@auth.login_required
def log_auto_reboot():
    """Log auto reboot event"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    return jsonify(power_api.log_auto_reboot(data))


@power_bp.route('/auto-reboot-stats', methods=['GET'])
@auth.login_required
def get_auto_reboot_stats():
    """Get auto reboot statistics"""
    return jsonify(power_api.get_auto_reboot_stats())


@power_bp.route('/auto-reboot-history', methods=['GET'])
@auth.login_required
def get_auto_reboot_history():
    """Get auto reboot history"""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    limit = request.args.get('limit', type=int)
    
    return jsonify(power_api.get_auto_reboot_history(from_date, to_date, limit))


@power_bp.route('/auto-reboot-history/export', methods=['GET'])
@auth.login_required
def export_auto_reboot_history():
    """Export auto reboot history as CSV"""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    result = power_api.export_auto_reboot_history(from_date, to_date)
    
    if result['success']:
        return Response(
            result['data'],
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=auto_reboot_history_{from_date or "all"}_{to_date or "all"}.csv'
            }
        )
    else:
        return jsonify(result), 500


@power_bp.route('/settings', methods=['GET'])
@auth.login_required
def get_auto_reboot_settings():
    """Get auto reboot settings"""
    return jsonify(power_api.get_auto_reboot_settings())


@power_bp.route('/settings', methods=['POST'])
@auth.login_required
def update_auto_reboot_settings():
    """Update auto reboot settings"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        user = data.get('user')
        password = data.get('password')
        settings = data.get('settings')
        
        if not user or not password or not settings:
            return jsonify({
                'success': False,
                'error': 'User, password, and settings are required'
            }), 400
        
        # Password validation
        valid_passwords = {
            'apt': os.getenv('APT_PASSWORD', 'powerapt'),
            'teknisi': os.getenv('TEKNISI_PASSWORD', 'Joulestore2020'),
            'admin': os.getenv('ADMIN_PASSWORD', 'admin')
        }
        
        if user not in valid_passwords or valid_passwords[user] != password:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
        
        # Update settings
        result = power_api.update_auto_reboot_settings(settings, user)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@power_bp.route('/reboot', methods=['POST'])
@auth.login_required
def system_reboot():
    """Execute system reboot"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        password = data.get('password')
        user = data.get('user')
        
        if not password or not user:
            return jsonify({
                'success': False,
                'error': 'Password and user are required'
            }), 400
        
        # Password validation
        valid_passwords = {
            'apt': os.getenv('APT_PASSWORD', 'powerapt'),
            'teknisi': os.getenv('TEKNISI_PASSWORD', 'Joulestore2020'),
            'admin': os.getenv('ADMIN_PASSWORD', 'admin')
        }
        
        if user not in valid_passwords or valid_passwords[user] != password:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
        
        # Execute reboot
        result = power_api.execute_reboot(user)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@power_bp.route('/shutdown', methods=['POST'])
@auth.login_required
def system_shutdown():
    """Execute system shutdown"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        password = data.get('password')
        user = data.get('user')
        
        if not password or not user:
            return jsonify({
                'success': False,
                'error': 'Password and user are required'
            }), 400
        
        # Password validation
        valid_passwords = {
            'apt': os.getenv('APT_PASSWORD', 'powerapt'),
            'teknisi': os.getenv('TEKNISI_PASSWORD', 'Joulestore2020'),
            'admin': os.getenv('ADMIN_PASSWORD', 'admin')
        }
        
        if user not in valid_passwords or valid_passwords[user] != password:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
        
        # Execute shutdown
        result = power_api.execute_shutdown(user)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500
