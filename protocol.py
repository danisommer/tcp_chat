import struct
import hashlib
import os

HEADER_SIZE = 12
TYPE_SIZE = 4

MSG_QUIT = b'QUIT'
MSG_FILE = b'FILE'
MSG_CHAT = b'CHAT'
MSG_FILE_OK = b'FROK'
MSG_FILE_ERROR = b'FERR'
MSG_FILE_META = b'FMTA'
MSG_FILE_DATA = b'FDAT'
MSG_FILE_HASH = b'FHSH'

CHUNK_SIZE = 8192


class Message:
    
    def __init__(self, msg_type, payload=b''):
        self.msg_type = msg_type
        self.payload = payload if isinstance(payload, bytes) else payload.encode('utf-8')
    
    def serialize(self):
        payload_size = len(self.payload)
        header = struct.pack('!Q', payload_size) + self.msg_type
        return header + self.payload
    
    @staticmethod
    def deserialize_header(header_bytes):
        if len(header_bytes) != HEADER_SIZE:
            raise ValueError(f"Cabeçalho inválido: esperado {HEADER_SIZE} bytes, recebido {len(header_bytes)}")
        
        payload_size = struct.unpack('!Q', header_bytes[:8])[0]
        msg_type = header_bytes[8:12]
        return payload_size, msg_type


def send_message(sock, msg_type, payload=b''):
    message = Message(msg_type, payload)
    data = message.serialize()
    sock.sendall(data)


def receive_message(sock):
    header = receive_exact(sock, HEADER_SIZE)
    if not header:
        return None, None
    
    payload_size, msg_type = Message.deserialize_header(header)
    
    payload = receive_exact(sock, payload_size) if payload_size > 0 else b''
    
    return msg_type, payload


def receive_exact(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(min(num_bytes - len(data), 4096))
        if not chunk:
            return None
        data += chunk
    return data


def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.digest()


def send_file(sock, filepath):
    try:
        if not os.path.exists(filepath):
            send_message(sock, MSG_FILE_ERROR, "Arquivo não encontrado")
            return False
        
        send_message(sock, MSG_FILE_OK)
        
        file_hash = calculate_file_hash(filepath)
        
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        filename_bytes = filename.encode('utf-8')
        metadata = struct.pack('!I', len(filename_bytes)) + filename_bytes + struct.pack('!Q', file_size)
        send_message(sock, MSG_FILE_META, metadata)
        
        send_message(sock, MSG_FILE_HASH, file_hash)
        
        with open(filepath, 'rb') as f:
            bytes_sent = 0
            while bytes_sent < file_size:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                send_message(sock, MSG_FILE_DATA, chunk)
                bytes_sent += len(chunk)
        
        return True
        
    except Exception as e:
        print(f"Erro ao enviar arquivo: {e}")
        send_message(sock, MSG_FILE_ERROR, str(e))
        return False


def receive_file(sock, save_dir):
    try:
        msg_type, payload = receive_message(sock)
        
        if msg_type == MSG_FILE_ERROR:
            error_msg = payload.decode('utf-8')
            return False, f"Erro: {error_msg}"
        
        if msg_type != MSG_FILE_OK:
            return False, "Resposta inválida do servidor"
        
        msg_type, metadata = receive_message(sock)
        if msg_type != MSG_FILE_META:
            return False, "Metadados não recebidos"
        
        filename_size = struct.unpack('!I', metadata[:4])[0]
        filename = metadata[4:4+filename_size].decode('utf-8')
        file_size = struct.unpack('!Q', metadata[4+filename_size:])[0]
        
        print(f"Recebendo arquivo: {filename} ({file_size} bytes)")
        
        msg_type, file_hash_received = receive_message(sock)
        if msg_type != MSG_FILE_HASH:
            return False, "Hash não recebido"
        
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        bytes_received = 0
        sha256 = hashlib.sha256()
        
        with open(filepath, 'wb') as f:
            while bytes_received < file_size:
                msg_type, chunk = receive_message(sock)
                if msg_type != MSG_FILE_DATA:
                    return False, "Dados do arquivo não recebidos corretamente"
                
                f.write(chunk)
                sha256.update(chunk)
                bytes_received += len(chunk)
                
                progress = (bytes_received / file_size) * 100
                print(f"\rProgresso: {progress:.1f}%", end='', flush=True)
        
        print()
        
        file_hash_calculated = sha256.digest()
        
        if file_hash_calculated == file_hash_received:
            return True, f"Arquivo '{filename}' recebido com sucesso! Integridade verificada ✓"
        else:
            return False, f"Arquivo '{filename}' recebido, mas a verificação de integridade FALHOU ✗"
        
    except Exception as e:
        return False, f"Erro ao receber arquivo: {e}"
