#!/bin/bash

# I2C Heartbeat Service Installation Script
# This script installs and configures the I2C heartbeat background service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="i2c-heartbeat"
SERVICE_USER="pi"
INSTALL_DIR="/opt/sundaya/jspro-powerdesk"
LOG_DIR="/var/lib/sundaya/jspro-powerdesk/logs"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

print_status() {
    printf "${BLUE}[INFO]${NC} %s\n" "$1"
}

print_success() {
    printf "${GREEN}[SUCCESS]${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}[WARNING]${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

check_requirements() {
    print_status "Checking requirements..."
    
    # Check if running as root
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    # Check if systemd is available
    if ! command -v systemctl > /dev/null 2>&1; then
        print_error "systemctl not found. This script requires systemd"
        exit 1
    fi
    
    # Check if Python3 is available
    if ! command -v python3 > /dev/null 2>&1; then
        print_error "Python3 not found. Please install Python3"
        exit 1
    fi
    
    print_success "Requirements check passed"
}

create_directories() {
    print_status "Creating directories..."
    
    # Create installation directory
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$LOG_DIR"
    sudo mkdir -p "$INSTALL_DIR/scripts"
    
    # Set ownership
    sudo chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"
    sudo chown -R $SERVICE_USER:$SERVICE_USER "$LOG_DIR"
    
    print_success "Directories created"
}

install_service_files() {
    print_status "Installing service files..."
    
    # Copy Python scripts
    sudo cp "$SCRIPT_DIR/../functions.py" "$INSTALL_DIR/"
    sudo cp "$SCRIPT_DIR/../config.py" "$INSTALL_DIR/" 2>/dev/null || print_warning "config.py not found, skipping"
    sudo cp "$SCRIPT_DIR/i2c_heartbeat_service.py" "$INSTALL_DIR/scripts/"
    
    # Make script executable
    sudo chmod +x "$INSTALL_DIR/scripts/i2c_heartbeat_service.py"
    
    # Copy systemd service file
    sudo cp "$SCRIPT_DIR/i2c-heartbeat.service" "/etc/systemd/system/"
    
    # Set ownership
    sudo chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"
    
    print_success "Service files installed"
}

configure_service() {
    print_status "Configuring systemd service..."
    
    # Reload systemd daemon
    sudo systemctl daemon-reload
    
    # Enable service (start on boot)
    sudo systemctl enable $SERVICE_NAME
    
    print_success "Service configured"
}

start_service() {
    print_status "Starting I2C heartbeat service..."
    
    # Start the service
    sudo systemctl start $SERVICE_NAME
    
    # Check if service started successfully
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Service started successfully"
    else
        print_error "Failed to start service"
        print_status "Checking service status..."
        sudo systemctl status $SERVICE_NAME
        exit 1
    fi
}

show_status() {
    print_status "Service Status:"
    sudo systemctl status $SERVICE_NAME --no-pager
    
    echo ""
    print_status "Recent logs:"
    sudo journalctl -u $SERVICE_NAME --no-pager -n 10
}

uninstall_service() {
    print_status "Uninstalling I2C heartbeat service..."
    
    # Stop and disable service
    sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
    sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
    
    # Remove service file
    sudo rm -f "/etc/systemd/system/i2c-heartbeat.service"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Optionally remove installation directory
    printf "Remove installation directory (%s)? [y/N]: " "$INSTALL_DIR"
    read -r REPLY
    case "$REPLY" in
        [Yy]|[Yy][Ee][Ss])
            sudo rm -rf "$INSTALL_DIR"
            print_success "Installation directory removed"
            ;;
        *)
            ;;
    esac
    
    print_success "Service uninstalled"
}

show_help() {
    echo "I2C Heartbeat Service Installation Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  install     Install and start the service"
    echo "  uninstall   Stop and remove the service"
    echo "  status      Show service status"
    echo "  restart     Restart the service"
    echo "  logs        Show service logs"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 install"
    echo "  sudo $0 status"
    echo "  sudo $0 restart"
}

# Main script logic
case "${1:-help}" in
    install)
        echo "=================================="
        echo "I2C Heartbeat Service Installation"
        echo "=================================="
        check_requirements
        create_directories
        install_service_files
        configure_service
        start_service
        echo ""
        print_success "Installation completed successfully!"
        echo ""
        print_status "Service commands:"
        echo "  Start:   sudo systemctl start $SERVICE_NAME"
        echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
        echo "  Status:  sudo systemctl status $SERVICE_NAME"
        echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
        ;;
    uninstall)
        uninstall_service
        ;;
    status)
        show_status
        ;;
    restart)
        print_status "Restarting service..."
        sudo systemctl restart $SERVICE_NAME
        print_success "Service restarted"
        show_status
        ;;
    logs)
        print_status "Following service logs (Ctrl+C to exit):"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    help|*)
        show_help
        ;;
esac
