#!/bin/bash

# Installation script for Disk Auto Reboot Monitoring System
# This script sets up the disk monitoring with auto reboot functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPP_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/disk-monitor"
SERVICE_USER="$(whoami)"

echo "=== Disk Auto Reboot Monitoring System Installation ==="
echo "Script Directory: $SCRIPT_DIR"
echo "Webapp Directory: $WEBAPP_DIR"
echo "Install Directory: $INSTALL_DIR"
echo "Service User: $SERVICE_USER"
echo

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root for system modifications
check_permissions() {
    if [ "$EUID" -ne 0 ]; then
        log "WARNING: Not running as root. Some operations may require sudo."
        log "You may be prompted for password during installation."
    fi
}

# Create necessary directories
create_directories() {
    log "Creating directories..."
    
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p /etc/logrotate.d
    sudo mkdir -p "$WEBAPP_DIR/logs"
    
    # Set proper ownership
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$WEBAPP_DIR/logs"
    
    # Set permissions for logs directory
    sudo chmod 777 "$WEBAPP_DIR/logs"
    
    log "Directories created successfully."
}

# Copy scripts to install directory
install_scripts() {
    log "Installing scripts..."
    
    # Copy the main monitoring script
    sudo cp "$SCRIPT_DIR/disk_auto_reboot.sh" "$INSTALL_DIR/"
    sudo chmod +x "$INSTALL_DIR/disk_auto_reboot.sh"
    
    # Create configuration file
    sudo tee "$INSTALL_DIR/config.conf" > /dev/null << EOF
# Disk Auto Reboot Configuration
THRESHOLD=60
WEBAPP_URL="http://localhost:5000"
AUTH_TOKEN="d1587d98aa2348b600edc7e7569e3997"
LOG_RETENTION_DAYS=30
ENABLE_NOTIFICATIONS=true
CLEANUP_BEFORE_REBOOT=true
EOF
    
    # Set proper ownership and permissions for config file
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/config.conf"
    sudo chmod 644 "$INSTALL_DIR/config.conf"
    
    log "Scripts installed to $INSTALL_DIR"
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/disk-auto-reboot > /dev/null << EOF
$WEBAPP_DIR/logs/disk_auto_reboot.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 777 $SERVICE_USER $SERVICE_USER
    postrotate
        # Send log rotation notification to webapp
        curl -s -X POST "http://localhost:5000/api/system/disk-alert" \\
             -H "Content-Type: application/json" \\
             -H "Authorization: Bearer d1587d98aa2348b600edc7e7569e3997" \\
             -d '{"type":"log_rotation","disk_usage":0,"message":"Log rotation completed","timestamp":"'"\$(date -Iseconds)"'"}' || true
    endscript
}

$WEBAPP_DIR/logs/auto_reboot.db* {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 777 $SERVICE_USER $SERVICE_USER
}
EOF
    
    log "Log rotation configured."
}

# Setup crontab entry
setup_crontab() {
    log "Setting up crontab..."
    
    # Check if crontab entry already exists
    if crontab -l 2>/dev/null | grep -q "disk_auto_reboot.sh"; then
        log "Crontab entry already exists. Updating..."
        # Remove existing entry
        crontab -l 2>/dev/null | grep -v "disk_auto_reboot.sh" | crontab -
    fi
    
    # Add new crontab entry
    (crontab -l 2>/dev/null; echo "*/5 * * * * $INSTALL_DIR/disk_auto_reboot.sh >> $WEBAPP_DIR/logs/disk_auto_reboot.log 2>&1") | crontab -
    
    # Create log file with proper permissions if it doesn't exist
    mkdir -p "$WEBAPP_DIR/logs"
    touch "$WEBAPP_DIR/logs/disk_auto_reboot.log"
    chmod 777 "$WEBAPP_DIR/logs/disk_auto_reboot.log"
    
    # Also create a symlink in the install directory for easy access
    sudo ln -sf "$WEBAPP_DIR/logs/disk_auto_reboot.log" "$INSTALL_DIR/current.log" 2>/dev/null || true
    
    log "Crontab configured to run every 5 minutes."
}

# Create monitoring status script
create_status_script() {
    log "Creating status monitoring script..."
    
    sudo tee "$INSTALL_DIR/status.sh" > /dev/null << EOF
#!/bin/bash

# Disk Auto Reboot Monitoring Status Script

LOGFILE="$WEBAPP_DIR/logs/disk_auto_reboot.log"
INSTALL_DIR="/opt/disk-monitor"

echo "=== Disk Auto Reboot Monitoring Status ==="
echo

# Check if monitoring is active
echo "1. Monitoring Status:"
if crontab -l 2>/dev/null | grep -q "disk_auto_reboot.sh"; then
    echo "   ✓ Active (runs every 5 minutes)"
    NEXT_RUN=\$(crontab -l | grep "disk_auto_reboot.sh" | head -1)
    echo "   Schedule: \$NEXT_RUN"
else
    echo "   ✗ Not configured in crontab"
fi
echo

# Check current disk usage
echo "2. Current Disk Usage:"
DISK_USAGE=\$(df / 2>/dev/null | awk 'NR==2 {print \$5}' | sed 's/%//' 2>/dev/null)
if [ -z "\$DISK_USAGE" ] || ! echo "\$DISK_USAGE" | grep -q '^[0-9][0-9]*\$'; then
    echo "   Usage: Unable to determine (non-Linux environment)"
    echo "   Status: ⚠️  Cannot check disk usage"
else
    echo "   Usage: \${DISK_USAGE}%"
    if [ "\$DISK_USAGE" -gt 60 ]; then
        echo "   Status: ⚠️  Above threshold (60%)"
    elif [ "\$DISK_USAGE" -gt 50 ]; then
        echo "   Status: ⚠️  Approaching threshold"
    else
        echo "   Status: ✓ Normal"
    fi
fi
echo

# Check recent log entries
echo "3. Recent Activity (last 10 entries):"
if [ -f "\$LOGFILE" ]; then
    tail -n 10 "\$LOGFILE" | while read line; do
        echo "   \$line"
    done
else
    echo "   No log file found"
fi
echo

# Check webapp connectivity
echo "4. Webapp Connectivity:"
if curl -s "http://localhost:5000/api/system/disk-usage" > /dev/null 2>&1; then
    echo "   ✓ Webapp reachable"
else
    echo "   ✗ Webapp not reachable"
fi
echo

# Show configuration
echo "5. Configuration:"
if [ -f "\$INSTALL_DIR/config.conf" ]; then
    cat "\$INSTALL_DIR/config.conf" | grep -E "^[A-Z]" | while read line; do
        echo "   \$line"
    done
else
    echo "   No configuration file found"
fi
EOF
    
    sudo chmod +x "$INSTALL_DIR/status.sh"
    
    log "Status script created at $INSTALL_DIR/status.sh"
}

# Create uninstall script
create_uninstall_script() {
    log "Creating uninstall script..."
    
    sudo tee "$INSTALL_DIR/uninstall.sh" > /dev/null << 'EOF'
#!/bin/bash

# Uninstall Disk Auto Reboot Monitoring System

echo "=== Uninstalling Disk Auto Reboot Monitoring System ==="

# Remove crontab entry
echo "Removing crontab entry..."
crontab -l 2>/dev/null | grep -v "disk_auto_reboot.sh" | crontab -

# Remove logrotate configuration
echo "Removing logrotate configuration..."
sudo rm -f /etc/logrotate.d/disk-auto-reboot

# Remove install directory
echo "Removing installation directory..."
sudo rm -rf /opt/disk-monitor

# Keep log files for manual review
echo "Log files preserved in jspro-powerdesk/logs/ for manual review"

echo "Uninstallation completed."
EOF
    
    sudo chmod +x "$INSTALL_DIR/uninstall.sh"
    
    log "Uninstall script created at $INSTALL_DIR/uninstall.sh"
}

# Test the installation
test_installation() {
    log "Testing installation..."
    
    # Test script execution
    if "$INSTALL_DIR/disk_auto_reboot.sh"; then
        log "✓ Script execution test passed"
    else
        log "✗ Script execution test failed"
        return 1
    fi
    
    # Test status script
    if "$INSTALL_DIR/status.sh" > /dev/null; then
        log "✓ Status script test passed"
    else
        log "✗ Status script test failed"
        return 1
    fi
    
    log "All tests passed!"
}

# Main installation process
main() {
    log "Starting installation..."
    
    check_permissions
    create_directories
    install_scripts
    setup_log_rotation
    setup_crontab
    create_status_script
    create_uninstall_script
    
    if test_installation; then
        log "Installation completed successfully!"
        echo
        echo "=== Installation Summary ==="
        echo "• Monitoring script: $INSTALL_DIR/disk_auto_reboot.sh"
        echo "• Configuration: $INSTALL_DIR/config.conf"
        echo "• Status check: $INSTALL_DIR/status.sh"
        echo "• Uninstall: $INSTALL_DIR/uninstall.sh"
        echo "• Log file: $WEBAPP_DIR/logs/disk_auto_reboot.log (permission: 777)"
        echo "• Crontab: Runs every 5 minutes"
        echo
        echo "To check status: $INSTALL_DIR/status.sh"
        echo "To uninstall: $INSTALL_DIR/uninstall.sh"
    else
        log "Installation failed during testing!"
        exit 1
    fi
}

# Run main function
main "$@"
