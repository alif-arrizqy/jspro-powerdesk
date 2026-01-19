import subprocess
import os
from subprocess import Popen
from config import *

def change_ip(path, ip, gw, subnet):
    """
    Change IP address using the change_ip.py script
    
    Args:
        path: Path to the change_ip.py script
        ip: New IP address
        gw: Gateway address
        subnet: Subnet mask (CIDR notation like /24 or dotted decimal)
    
    Returns:
        bool: True if script started successfully, False otherwise
        Note: If successful, system will reboot immediately, so we can't wait for output.
        If script fails, it will print "Fail" and exit without rebooting.
    """
    try:
        # Ensure the path exists
        if not os.path.exists(path):
            print(f"Error: Script not found at {path}")
            return False
        
        p = Popen([
            "sudo", "python3", path, ip, gw, subnet
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, start_new_session=True)
        
        import time
        time.sleep(0.15)
        
        if p.poll() is not None:
            try:
                output, errors = p.communicate(timeout=0.1)
                if 'Fail' in output or (errors and len(errors.strip()) > 0):
                    print(f"IP change failed - Output: {output}, Errors: {errors}")
                    return False
                if 'Success' in output:
                    print(f"IP change successful: {output}")
                    return True
            except:
                pass
        
        print("IP change script executed. System will reboot if configuration is valid.")
        return True
            
    except Exception as e:
        print(f"Exception in change_ip: {e}")
        return False


def bash_command(command, universal_newlines=False, shell=False):
    """
    Execute bash commands
    
    Args:
        command: Command to execute (string or list)
        universal_newlines: Whether to use universal newlines
        shell: Whether to use shell
        
    Returns:
        str: Command output
    """
    try:
        if isinstance(command, str):
            sep_command = command.split(' ')
        else:
            sep_command = command
            
        p = Popen(
            sep_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=universal_newlines, 
            shell=shell
        )
        
        output, errors = p.communicate()
        
        if isinstance(output, bytes):
            return str(output)[2:-1]
        else:
            return output
            
    except Exception as e:
        print(f"Exception in bash_command: {e}")
        return ""
