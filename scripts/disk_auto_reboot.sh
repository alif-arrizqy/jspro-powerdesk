#!/bin/bash

# Enhanced Disk Monitoring and Auto Reboot Script for Raspberry Pi
# Monitors disk usage and automatically reboots when threshold is exceeded
# Logs all activities and sends notifications to webapp

# Configuration
THRESHOLD=60
LOGFILE="logs/disk_auto_reboot.log"
LOCKFILE="/tmp/disk_reboot.lock"
WEBAPP_URL="http://localhost:5000"
AUTH_TOKEN="d1587d98aa2348b600edc7e7569e3997"

# Functions
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOGFILE"
}

send_webapp_notification() {
    local type="$1"
    local disk_usage="$2"
    local message="$3"
    
    curl -s -X POST "${WEBAPP_URL}/api/v1/power/disk-alert" \
         -H "Content-Type: application/json" \
         -H "Authorization: Bearer ${AUTH_TOKEN}" \
         -d "{
            \"type\": \"${type}\",
            \"disk_usage\": ${disk_usage},
            \"message\": \"${message}\",
            \"timestamp\": \"$(date -Iseconds)\"
         }" 2>/dev/null || true
}

log_auto_reboot() {
    local disk_usage="$1"
    
    curl -s -X POST "${WEBAPP_URL}/api/v1/power/auto-reboot-log" \
         -H "Content-Type: application/json" \
         -H "Authorization: Bearer ${AUTH_TOKEN}" \
         -d "{
            \"disk_usage\": ${disk_usage},
            \"timestamp\": \"$(date -Iseconds)\",
            \"action\": \"auto_reboot\",
            \"status\": \"initiated\"
         }" 2>/dev/null || true
}

cleanup_before_reboot() {
    log_message "Performing cleanup before reboot..."
    
    # Clear systemd logs older than 3 days
    journalctl --vacuum-time=3d 2>/dev/null || true
    
    # Clear tmp files older than 1 day
    find /tmp -type f -atime +1 -delete 2>/dev/null || true
    
    # Clear cache if exists
    [ -d /var/cache ] && find /var/cache -type f -atime +7 -delete 2>/dev/null || true
    
    # Clear log files larger than 10MB
    [ -d /var/log ] && find /var/log -name "*.log" -size +10M -delete 2>/dev/null || true
    
    # Sync filesystem
    sync
    
    log_message "Cleanup completed"
}

# Main script
main() {
    # Prevent multiple executions
    if [ -f "$LOCKFILE" ]; then
        log_message "Another instance is running, exiting..."
        exit 1
    fi

    # Create lock file
    touch "$LOCKFILE"
    
    # Ensure cleanup on exit
    trap 'rm -f "$LOCKFILE"' EXIT

    # Rotate log if too big (1MB)
    if [ -f "$LOGFILE" ] && [ $(stat -c%s "$LOGFILE") -gt 1048576 ]; then
        mv "$LOGFILE" "${LOGFILE}.old"
        log_message "Log rotated"
    fi

    # Get disk usage (more efficient for Raspberry Pi)
    DISK_USAGE=$(df / | awk 'NR==2 {print int($5)}')
    
    if [ -z "$DISK_USAGE" ] || ! [[ "$DISK_USAGE" =~ ^[0-9]+$ ]]; then
        log_message "ERROR: Could not determine disk usage"
        exit 1
    fi

    # Check disk usage and take action
    if [ "$DISK_USAGE" -gt "$THRESHOLD" ]; then
        log_message "CRITICAL: Disk usage ${DISK_USAGE}% > ${THRESHOLD}%"
        
        # Send critical alert to webapp
        send_webapp_notification "critical" "$DISK_USAGE" "Critical disk usage detected. Auto-reboot initiated."
        
        # Log the auto reboot event
        log_auto_reboot "$DISK_USAGE"
        
        # Perform cleanup
        cleanup_before_reboot
        
        # Check disk usage after cleanup
        DISK_USAGE_AFTER=$(df / | awk 'NR==2 {print int($5)}')
        log_message "Disk usage after cleanup: ${DISK_USAGE_AFTER}%"
        
        # Still above threshold? Proceed with reboot
        if [ "$DISK_USAGE_AFTER" -gt "$THRESHOLD" ]; then
            log_message "Disk usage still above threshold after cleanup. Initiating reboot..."
            
            # Send final notification
            send_webapp_notification "reboot" "$DISK_USAGE_AFTER" "Cleanup insufficient. System rebooting now."
            
            # Graceful reboot with 1 minute delay
            sudo shutdown -r +1 "Auto-reboot: High disk usage (${DISK_USAGE_AFTER}%). System will restart in 1 minute." &
            
            log_message "Reboot command issued. System will restart in 1 minute."
        else
            log_message "Cleanup successful. Disk usage reduced to ${DISK_USAGE_AFTER}%. Reboot cancelled."
            send_webapp_notification "cleanup_success" "$DISK_USAGE_AFTER" "Cleanup successful. Disk usage reduced."
        fi
        
    elif [ "$DISK_USAGE" -gt 50 ]; then
        # Warning level - log and notify but don't reboot
        log_message "WARNING: Disk usage ${DISK_USAGE}% approaching threshold"
        send_webapp_notification "warning" "$DISK_USAGE" "Disk usage approaching threshold."
        
        # Log normal status every hour (when minute is 00)
        MINUTE=$(date '+%M')
        if [ "$MINUTE" = "00" ]; then
            log_message "NORMAL: Disk usage ${DISK_USAGE}%"
        fi
    else
        # Normal level - only log once per hour
        MINUTE=$(date '+%M')
        if [ "$MINUTE" = "00" ]; then
            log_message "NORMAL: Disk usage ${DISK_USAGE}%"
        fi
    fi
}

# Run main function
main "$@"
