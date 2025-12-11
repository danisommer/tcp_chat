import os
import socket
import sys
import threading
from datetime import datetime
from urllib.parse import unquote

HOST = '0.0.0.0'
DEFAULT_PORT = 8080
ROOT_DIR = 'server_files'
MAX_REQUEST_SIZE = 65536


STATUS_MESSAGES = {
    200: 'OK',
    400: 'Bad Request',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    500: 'Internal Server Error',
}


CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.htm': 'text/html; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript',
}


def guess_content_type(path):
    _, ext = os.path.splitext(path.lower())
    return CONTENT_TYPES.get(ext, 'application/octet-stream')


def format_http_date():
    return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')


def build_response(status_code, body=b'', headers=None):
    reason = STATUS_MESSAGES.get(status_code, 'Unknown')
    headers = headers or {}
    default_headers = {
        'Date': format_http_date(),
        'Server': 'TCPChatHTTP/1.0',
        'Content-Length': str(len(body)),
        'Connection': 'close',
    }
    default_headers.update(headers)

    header_lines = [f"HTTP/1.1 {status_code} {reason}\r\n"]
    for key, value in default_headers.items():
        header_lines.append(f"{key}: {value}\r\n")
    header_lines.append('\r\n')

    return ''.join(header_lines).encode('utf-8') + body


def sanitize_path(raw_path):
    path = raw_path.split('?', 1)[0].split('#', 1)[0]
    decoded = unquote(path)
    normalized = os.path.normpath(decoded.lstrip('/'))
    return normalized if normalized != '.' else ''


class HTTPClientHandler(threading.Thread):

    def __init__(self, client_socket, client_address, root_dir):
        super().__init__(daemon=True)
        self.socket = client_socket
        self.address = client_address
        self.root_dir = os.path.abspath(root_dir)

    def run(self):
        try:
            request_data = self.read_request()
            if not request_data:
                return

            method, target, version = self.parse_request_line(request_data)
            if method != 'GET':
                body = b'Method not allowed'
                response = build_response(405, body, {'Content-Type': 'text/plain; charset=utf-8'})
                self.socket.sendall(response)
                return

            file_path = self.resolve_path(target)
            if not file_path:
                body = b'Forbidden'
                response = build_response(403, body, {'Content-Type': 'text/plain; charset=utf-8'})
                self.socket.sendall(response)
                return

            if os.path.isdir(file_path):
                file_path = os.path.join(file_path, 'index.html')

            if not os.path.exists(file_path):
                body = b"<html><body><h1>404 Not Found</h1></body></html>"
                response = build_response(404, body, {'Content-Type': 'text/html; charset=utf-8'})
                self.socket.sendall(response)
                return

            self.send_file_response(file_path)

        except ValueError as err:
            body = f"Bad request: {err}".encode('utf-8')
            response = build_response(400, body, {'Content-Type': 'text/plain; charset=utf-8'})
            self.socket.sendall(response)
        except Exception as err:
            print(f"[Erro] {self.address}: {err}")
            body = b'Internal server error'
            response = build_response(500, body, {'Content-Type': 'text/plain; charset=utf-8'})
            try:
                self.socket.sendall(response)
            except Exception:
                pass
        finally:
            try:
                self.socket.close()
            except Exception:
                pass

    def read_request(self):
        data = b''
        self.socket.settimeout(5)
        while b'\r\n\r\n' not in data and len(data) < MAX_REQUEST_SIZE:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            data += chunk
        return data

    def parse_request_line(self, request_bytes):
        try:
            text = request_bytes.decode('iso-8859-1', errors='replace')
            lines = text.split('\r\n')
            request_line = lines[0].strip()
            parts = request_line.split()
            if len(parts) != 3:
                raise ValueError('linha de requisição inválida')
            method, target, version = parts
            if not version.startswith('HTTP/'):
                raise ValueError('versão HTTP desconhecida')
            return method, target, version
        except Exception as err:
            raise ValueError(err)

    def resolve_path(self, target):
        safe_path = sanitize_path(target)
        abs_path = os.path.abspath(os.path.join(self.root_dir, safe_path))
        if not abs_path.startswith(self.root_dir):
            return None
        return abs_path

    def send_file_response(self, file_path):
        with open(file_path, 'rb') as f:
            body = f.read()

        content_type = guess_content_type(file_path)
        headers = {
            'Content-Type': content_type,
        }
        response = build_response(200, body, headers)
        self.socket.sendall(response)
        print(f"[200] {self.address} -> {os.path.relpath(file_path, self.root_dir)} ({len(body)} bytes)")


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    os.makedirs(ROOT_DIR, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, port))
        server_socket.listen(10)

        print('=' * 60)
        print('Servidor HTTP simples (TCP) iniciado')
        print(f'Escutando em http://{HOST}:{port}')
        print(f'Diretório raiz: {os.path.abspath(ROOT_DIR)}')
        print('=' * 60)

        while True:
            client_socket, client_address = server_socket.accept()
            handler = HTTPClientHandler(client_socket, client_address, ROOT_DIR)
            handler.start()


if __name__ == '__main__':
    main()
