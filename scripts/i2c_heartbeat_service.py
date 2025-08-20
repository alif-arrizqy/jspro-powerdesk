#!/usr/bin/env python3
"""
I2C Heartbeat Background Service
Automatically sends I2C heartbeat signals based on configured interval
"""

import time
import signal
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functions import send_i2c_heartbeat, get_i2c_settings

class I2CHeartbeatService:
    def __init__(self):
        self.running = False
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Setup logging for the service"""
        log_dir = Path('/var/lib/sundaya/jspro-powerdesk/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'i2c_heartbeat_service.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('I2CHeartbeatService')
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def get_current_settings(self):
        """Get current I2C settings"""
        try:
            settings = get_i2c_settings()
            return {
                'enabled': settings.get('enabled', True),
                'interval_minutes': settings.get('interval_minutes', 2),
                'i2c_address': settings.get('i2c_address', '0x28'),
                'message': settings.get('message', 'H')
            }
        except Exception as e:
            self.logger.error(f"Error getting settings: {e}")
            return {
                'enabled': True,
                'interval_minutes': 2,
                'i2c_address': '0x28',
                'message': 'H'
            }
    
    def send_heartbeat(self):
        """Send I2C heartbeat using current settings"""
        try:
            settings = self.get_current_settings()
            
            if not settings['enabled']:
                self.logger.debug("I2C monitoring is disabled, skipping heartbeat")
                return
            
            # Convert address from hex string to int
            address = int(settings['i2c_address'], 16)
            message = ord(settings['message'][0]) if settings['message'] else ord('H')
            
            # Send heartbeat
            result = send_i2c_heartbeat(address, message)
            
            if result['success']:
                self.logger.info(f"Heartbeat sent successfully to {result['address']}: {result['message']}")
            else:
                self.logger.warning(f"Heartbeat failed to {result['address']}: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}")
    
    def run(self):
        """Main service loop"""
        self.logger.info("I2C Heartbeat Service starting...")
        self.running = True
        
        last_heartbeat = 0
        last_settings_check = 0
        current_interval = 2  # Default 2 minutes
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check settings every 30 seconds
                if current_time - last_settings_check >= 30:
                    settings = self.get_current_settings()
                    new_interval = settings['interval_minutes']
                    
                    if new_interval != current_interval:
                        self.logger.info(f"Interval changed from {current_interval} to {new_interval} minutes")
                        current_interval = new_interval
                    
                    last_settings_check = current_time
                
                # Send heartbeat based on interval
                interval_seconds = current_interval * 60
                if current_time - last_heartbeat >= interval_seconds:
                    self.send_heartbeat()
                    last_heartbeat = current_time
                
                # Sleep for 1 second before next iteration
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Service interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # Wait 5 seconds before retrying
        
        self.logger.info("I2C Heartbeat Service stopped")
    
    def status(self):
        """Get service status"""
        settings = self.get_current_settings()
        return {
            'running': self.running,
            'settings': settings,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='I2C Heartbeat Background Service')
    parser.add_argument('command', choices=['start', 'stop', 'status', 'test'], 
                       help='Service command')
    parser.add_argument('--daemon', action='store_true', 
                       help='Run as daemon (background process)')
    
    args = parser.parse_args()
    
    service = I2CHeartbeatService()
    
    if args.command == 'start':
        if args.daemon:
            # Run as daemon
            import daemon
            with daemon.DaemonContext():
                service.run()
        else:
            # Run in foreground
            service.run()
            
    elif args.command == 'test':
        # Test single heartbeat
        print("Testing I2C heartbeat...")
        service.send_heartbeat()
        print("Test completed")
        
    elif args.command == 'status':
        # Show status
        status = service.status()
        print(f"Service Status: {'Running' if status['running'] else 'Stopped'}")
        print(f"Settings: {status['settings']}")
        print(f"Last Check: {status['timestamp']}")
        
    elif args.command == 'stop':
        # Stop service (this would need to be implemented with PID file)
        print("Stop command requires PID file implementation")

if __name__ == '__main__':
    main()
