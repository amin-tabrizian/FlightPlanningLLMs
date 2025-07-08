#!/usr/bin/env python3
"""
Diagnostic script to check Flask app accessibility
"""

import socket
import subprocess
import sys
import requests
import time

def get_server_ip():
    """Get the server's IP address"""
    try:
        # Get the IP address using hostname command
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split()[0]
    except:
        pass
    
    # Fallback method
    try:
        # Connect to a remote address to get local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "Unable to determine"

def check_port_open(host, port):
    """Check if a port is open on the host"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def check_firewall():
    """Check basic firewall status"""
    try:
        # Check if ufw is active
        result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    
    try:
        # Check if firewalld is running
        result = subprocess.run(['firewall-cmd', '--state'], capture_output=True, text=True)
        if result.returncode == 0:
            return "firewalld is running"
    except:
        pass
    
    return "Unable to check firewall status"

def main():
    print("=== Flask App Connectivity Diagnostic ===\n")
    
    # Get server IP
    server_ip = get_server_ip()
    print(f"Server IP Address: {server_ip}")
    
    # Check if Flask default port is open
    port = 5000
    print(f"\nChecking if port {port} is accessible...")
    
    # Check localhost
    localhost_open = check_port_open('localhost', port)
    print(f"  localhost:{port} - {'✓ Open' if localhost_open else '✗ Closed'}")
    
    # Check server IP
    if server_ip != "Unable to determine":
        serverip_open = check_port_open(server_ip, port)
        print(f"  {server_ip}:{port} - {'✓ Open' if serverip_open else '✗ Closed'}")
    
    # Check all interfaces
    all_interfaces_open = check_port_open('0.0.0.0', port)
    print(f"  0.0.0.0:{port} - {'✓ Open' if all_interfaces_open else '✗ Closed'}")
    
    # Test HTTP request if port is open
    if localhost_open:
        print(f"\nTesting HTTP request to localhost:{port}...")
        try:
            response = requests.get(f'http://localhost:{port}', timeout=5)
            print(f"  HTTP Status: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
        except requests.exceptions.ConnectionError:
            print("  ✗ Connection refused - Flask app may not be running")
        except requests.exceptions.Timeout:
            print("  ✗ Connection timeout")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Check firewall
    print(f"\nFirewall Status:")
    firewall_status = check_firewall()
    print(f"  {firewall_status}")
    
    # Provide recommendations
    print(f"\n=== Recommendations ===")
    
    if not localhost_open:
        print("• Flask app is not running. Start it with: python run.py")
    else:
        print("• Flask app appears to be running locally ✓")
    
    if server_ip != "Unable to determine":
        print(f"• For external access, use: http://{server_ip}:{port}")
        if not serverip_open:
            print("• External access blocked - check firewall settings")
            print(f"  Ubuntu/Debian: sudo ufw allow {port}")
            print(f"  RHEL/CentOS: sudo firewall-cmd --add-port={port}/tcp --permanent")
    
    print(f"• For SSH port forwarding: ssh -L {port}:localhost:{port} username@{server_ip}")
    print("• Make sure to run Flask with host='0.0.0.0' for external access")
    
    print(f"\n=== Next Steps ===")
    print("1. If Flask isn't running: cd /path/to/app && python run.py")
    print("2. If firewall is blocking: configure firewall to allow port 5000")
    print("3. If still having issues: try SSH port forwarding")

if __name__ == '__main__':
    main() 