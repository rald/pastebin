#!/usr/bin/env python3.11
import socket
import os
import random
import string
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import mimetypes

HOST = 'pantasya.mooo.com'
PORT = 5254
HTTP_PORT = 5255
PASTEDIR = Path('pastes')
MAX_SIZE = 1024 * 1024  # 1MB

PASTEDIR.mkdir(exist_ok=True)

def generate_id():
    count_file = 'count.txt'
    try:
        if os.path.exists(count_file):
            with open(count_file, 'r') as f:
                count = int(f.read().strip())
        else:
            count = 0
            with open(count_file, 'w') as f:
                f.write('0')
        
        if count >= 0xFFFF:
            return None
        
        hex_id = f"{count:04x}"
        with open(count_file, 'w') as f:
            f.write(str(count + 1))
        return hex_id
    except (ValueError, IOError):
        return None  # Fallback on errors

def handle_client(client_sock):
    try:
        data = client_sock.recv(MAX_SIZE + 1)  # +1 to detect overflow
    except:
        data = b''

    if len(data) > MAX_SIZE:
        client_sock.sendall(b"Error: Paste too large (max 1MB)\n")
        client_sock.shutdown(socket.SHUT_RDWR)
        return

    content = data.decode('utf-8', errors='replace')
    paste_id = generate_id()

    if paste_id is None:
        client_sock.sendall(b"Error: Bin is full\n")
        client_sock.shutdown(socket.SHUT_RDWR)
        return

    paste_path = PASTEDIR / paste_id
    with open(paste_path, 'w') as f:
        f.write(content)

    url = f"http://{HOST}:{HTTP_PORT}/{paste_id}\n"
    client_sock.sendall(url.encode('utf-8'))
    client_sock.shutdown(socket.SHUT_RDWR)

class PasteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/'):
            paste_id = self.path[1:]
            paste_path = PASTEDIR / paste_id

            if paste_path.exists():
                content = paste_path.read_text()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Paste not found')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_paste_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT))
        sock.listen(5)
        print(f"NC paste server: {HOST}:{PORT}")

        while True:
            client_sock, addr = sock.accept()
            handle_client(client_sock)
            client_sock.close()

def run_http_server():
    httpd = HTTPServer((HOST, HTTP_PORT), PasteHandler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"HTTP server: http://{HOST}:{HTTP_PORT}/")
    httpd.serve_forever()

if __name__ == '__main__':
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    run_paste_server()
