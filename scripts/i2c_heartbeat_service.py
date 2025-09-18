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
from helpers.i2c_helper import send_i2c_heartbeat, get_i2c_settings

class I2CHeartbeatService:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Setup logging for the service"""
        log_dir = Path('/var/lib/sundaya/jspro-powerdesk/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging with explicit flush
        logging.basicConfig(
            level=logging.DEBUG,  # Changed to DEBUG for more detailed logging
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'i2c_heartbeat_service.log'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # Force reconfiguration
        )
        self.logger = logging.getLogger('I2CHeartbeatService')
        
        # Ensure immediate flushing
        for handler in self.logger.handlers:
            handler.flush()
        
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
                'interval_seconds': settings.get('interval_seconds', 2), 
                'i2c_address': settings.get('i2c_address', '0x28'),
                'message': settings.get('message', 'H')
            }
        except Exception as e:
            self.logger.warning(f"Error getting settings, using defaults: {e}")
            return {
                'enabled': True,
                'interval_seconds': 2,
                'i2c_address': '0x28',
                'message': 'H'
            }
    
    def send_heartbeat(self):
        """Send I2C heartbeat using current settings"""
        try:
            settings = self.get_current_settings()
            
            if not settings['enabled']:
                self.logger.debug("I2C monitoring is disabled, skipping heartbeat")
                return True
            
            # Convert address from hex string to int
            address = int(settings['i2c_address'], 16)
            message = ord(settings['message'][0]) if settings['message'] else ord('H')
            
            # Send heartbeat
            result = send_i2c_heartbeat(address, message)
            
            if result['success']:
                self.logger.debug(f"Heartbeat sent successfully to {result['address']}: {result['message']}")
                return True
            else:
                self.logger.warning(f"Heartbeat failed to {result['address']}: {result['error']}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}", exc_info=True)
            return False
    
    def run(self):
        """Main service loop"""
        self.start_time = datetime.now()
        self.logger.info(f"I2C Heartbeat Service starting at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Process PID: {os.getpid()}")
        
        self.running = True
        
        last_heartbeat = 0
        last_settings_check = 0
        current_interval = 2  # Default 2 seconds
        error_count = 0
        max_consecutive_errors = 10
        heartbeat_count = 0
        successful_heartbeats = 0
        failed_heartbeats = 0
        loop_count = 0
        
        self.logger.info(f"Service loop started with interval: {current_interval} seconds")
        
        try:
            self.logger.info("Entering main service loop...")
            sys.stdout.flush()
            
            while self.running:
                try:
                    loop_count += 1
                    current_time = time.time()
                    
                    # Log every 60 seconds to show service is alive
                    if loop_count % 60 == 0:
                        self.logger.debug(f"Service alive - loop #{loop_count}, uptime: {datetime.now() - self.start_time}")
                    
                    # Check settings every 2 seconds
                    if current_time - last_settings_check >= 2:
                        self.logger.debug("Checking settings...")
                        settings = self.get_current_settings()
                        new_interval = settings['interval_seconds'] 
                        
                        if new_interval != current_interval:
                            self.logger.info(f"Interval changed from {current_interval} to {new_interval} seconds")
                            current_interval = new_interval
                        
                        last_settings_check = current_time
                    
                    # Send heartbeat based on interval
                    interval_seconds = current_interval  # Already in seconds
                    time_since_last = current_time - last_heartbeat
                    
                    if time_since_last >= interval_seconds:
                        self.logger.info(f"Time for heartbeat (last heartbeat was {time_since_last:.1f} seconds ago, interval: {interval_seconds}s)")
                        success = self.send_heartbeat()
                        last_heartbeat = current_time
                        heartbeat_count += 1
                        
                        if success:
                            successful_heartbeats += 1
                            self.logger.info(f"Heartbeat #{heartbeat_count} successful - next heartbeat in {interval_seconds} seconds")
                        else:
                            failed_heartbeats += 1
                            self.logger.warning(f"Heartbeat #{heartbeat_count} failed - next heartbeat in {interval_seconds} seconds")
                        
                        error_count = 0  # Reset error count on successful iteration
                        
                        # Flush logs immediately after heartbeat
                        sys.stdout.flush()
                        
                        # Log summary every 5 heartbeats for debugging
                        if heartbeat_count % 5 == 0:
                            uptime = datetime.now() - self.start_time
                            success_rate = (successful_heartbeats / heartbeat_count * 100) if heartbeat_count > 0 else 0
                            self.logger.info(f"Service summary: {heartbeat_count} heartbeats sent ({successful_heartbeats} success, {failed_heartbeats} failed), success rate: {success_rate:.1f}%, uptime: {uptime}")
                    
                    # Sleep for 1 second before next iteration
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    self.logger.info("Service interrupted by user")
                    break
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"Unexpected error in main loop (#{error_count}): {e}", exc_info=True)
                    sys.stdout.flush()
                    
                    if error_count >= max_consecutive_errors:
                        self.logger.critical(f"Too many consecutive errors ({error_count}), stopping service")
                        break
                    
                    # Exponential backoff for retries
                    sleep_time = min(60, 5 * (2 ** min(error_count, 5)))
                    self.logger.warning(f"Waiting {sleep_time} seconds before retry...")
                    time.sleep(sleep_time)
            
            self.logger.info("Main service loop ended normally")
            
        except Exception as e:
            self.logger.critical(f"Fatal error in service main loop: {e}", exc_info=True)
            sys.stdout.flush()
            raise
        
        end_time = datetime.now()
        uptime = end_time - self.start_time if self.start_time else "unknown"
        success_rate = (successful_heartbeats / heartbeat_count * 100) if heartbeat_count > 0 else 0
        self.logger.info(f"I2C Heartbeat Service stopped at {end_time.strftime('%Y-%m-%d %H:%M:%S')}, total uptime: {uptime}, heartbeats sent: {heartbeat_count} (success rate: {success_rate:.1f}%)")
    
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
    
    args = parser.parse_args()
    
    service = I2CHeartbeatService()
    
    if args.command == 'start':
        # Always run in foreground for systemd
        exit_code = 0
        try:
            service.logger.info("Starting I2C Heartbeat Service...")
            service.run()
            service.logger.info("Service ended normally")
        except KeyboardInterrupt:
            service.logger.info("Service interrupted by user")
            exit_code = 0
        except Exception as e:
            service.logger.critical(f"Failed to start service: {e}", exc_info=True)
            exit_code = 1
        finally:
            service.logger.info(f"Service exiting with code {exit_code}")
            sys.stdout.flush()
            sys.exit(exit_code)
            
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
        # Stop service (handled by systemd)
        print("Use 'systemctl stop i2c-heartbeat.service' to stop the service")

if __name__ == '__main__':
    main()
