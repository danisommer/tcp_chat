import socket
import threading
import os
import sys
import queue
import struct
import hashlib
from protocol import (
    MSG_QUIT, MSG_FILE, MSG_CHAT,
    MSG_FILE_OK, MSG_FILE_ERROR, MSG_FILE_META, MSG_FILE_DATA, MSG_FILE_HASH,
    send_message, receive_message, CHUNK_SIZE
)

DOWNLOAD_DIR = 'client_downloads'


class ChatClient:
    
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.running = True
        self.file_message_queue = queue.Queue()
        self.waiting_for_file = False
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            print(f"Conectando ao servidor {self.server_host}:{self.server_port}...")
            
            self.socket.connect((self.server_host, self.server_port))
            
            self.connected = True
            print("Conectado com sucesso!\n")
            
            return True
            
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        if self.connected:
            try:
                send_message(self.socket, MSG_QUIT)
            except:
                pass
            
            self.connected = False
            self.running = False
            
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
    
    def send_chat_message(self, message):
        try:
            send_message(self.socket, MSG_CHAT, message)
            print(f"[Você]: {message}")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
    
    def request_file(self, filename):
        try:
            print(f"\nSolicitando arquivo: {filename}")
            
            self.waiting_for_file = True
            while not self.file_message_queue.empty():
                self.file_message_queue.get()
            
            send_message(self.socket, MSG_FILE, filename)
            
            success, message = self.receive_file_from_queue()
            print(message)
            
        except Exception as e:
            print(f"Erro ao solicitar arquivo: {e}")
        finally:
            self.waiting_for_file = False
    
    def receive_file_from_queue(self):
        try:
            msg_type, payload = self.file_message_queue.get(timeout=10)
            
            if msg_type == MSG_FILE_ERROR:
                error_msg = payload.decode('utf-8')
                return False, f"Erro: {error_msg}"
            
            if msg_type != MSG_FILE_OK:
                return False, "Resposta inválida do servidor"
            
            msg_type, metadata = self.file_message_queue.get(timeout=10)
            if msg_type != MSG_FILE_META:
                return False, "Metadados não recebidos"
            
            filename_size = struct.unpack('!I', metadata[:4])[0]
            filename = metadata[4:4+filename_size].decode('utf-8')
            file_size = struct.unpack('!Q', metadata[4+filename_size:])[0]
            
            print(f"Recebendo arquivo: {filename} ({file_size} bytes)")
            
            msg_type, file_hash_received = self.file_message_queue.get(timeout=10)
            if msg_type != MSG_FILE_HASH:
                return False, "Hash não recebido"
            
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            
            bytes_received = 0
            sha256 = hashlib.sha256()
            
            with open(filepath, 'wb') as f:
                while bytes_received < file_size:
                    msg_type, chunk = self.file_message_queue.get(timeout=10)
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
                return True, f"Arquivo '{filename}' recebido com sucesso. Integridade verificada"
            else:
                return False, f"Arquivo '{filename}' recebido, mas a verificação de integridade FALHOU"
            
        except queue.Empty:
            return False, "Timeout: servidor não respondeu a tempo"
        except Exception as e:
            return False, f"Erro ao receber arquivo: {e}"
    
    def receive_messages_thread(self):
        while self.running and self.connected:
            try:
                msg_type, payload = receive_message(self.socket)
                
                if msg_type is None:
                    print("\n[Sistema] Conexão encerrada pelo servidor")
                    self.connected = False
                    break
                
                if self.waiting_for_file and msg_type in [MSG_FILE_OK, MSG_FILE_ERROR, MSG_FILE_META, MSG_FILE_DATA, MSG_FILE_HASH]:
                    self.file_message_queue.put((msg_type, payload))
                
                elif msg_type == MSG_CHAT:
                    message = payload.decode('utf-8')
                    print(f"\n{message}")
                    self.show_prompt()
                
                elif msg_type in [MSG_FILE_OK, MSG_FILE_ERROR, MSG_FILE_META, MSG_FILE_DATA, MSG_FILE_HASH]:
                    pass
                    
            except Exception as e:
                if self.running:
                    print(f"\n[Sistema] Erro ao receber mensagem: {e}")
                break
        
        self.running = False
    
    def show_prompt(self):
        print("\nComandos: [chat] [arquivo] [sair]", end='\n> ', flush=True)
    
    def run(self):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        if not self.connect():
            return
        
        receive_thread = threading.Thread(target=self.receive_messages_thread, daemon=True)
        receive_thread.start()
        
        print("="*60)
        print("COMANDOS DISPONÍVEIS:")
        print("  chat <mensagem>    - Envia mensagem para o servidor")
        print("  arquivo <nome>     - Solicita arquivo do servidor")
        print("  sair               - Desconecta do servidor")
        print("="*60)
        
        while self.running and self.connected:
            try:
                self.show_prompt()
                command = input().strip()
                
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                
                if cmd == 'sair' or cmd == 'quit':
                    print("Desconectando...")
                    self.disconnect()
                    break
                    
                elif cmd == 'chat':
                    if len(parts) < 2:
                        print("Uso: chat <mensagem>")
                    else:
                        self.send_chat_message(parts[1])
                        
                elif cmd == 'arquivo' or cmd == 'file':
                    if len(parts) < 2:
                        print("Uso: arquivo <nome_do_arquivo>")
                    else:
                        self.request_file(parts[1])
                        
                else:
                    print(f"Comando desconhecido: '{cmd}'")
                    print("Use: chat, arquivo, ou sair")
                    
            except EOFError:
                print("\nDesconectando...")
                self.disconnect()
                break
                
            except KeyboardInterrupt:
                print("\n\nDesconectando...")
                self.disconnect()
                break
                
            except Exception as e:
                print(f"Erro: {e}")
        
        print("Cliente encerrado.")


def main():
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
        server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    else:
        print("Cliente TCP - Transferência de Arquivos e Chat")
        print("="*60)
        
        server_host = input("Digite o IP do servidor [localhost]: ").strip()
        if not server_host:
            server_host = 'localhost'
        
        port_input = input("Digite a porta [5555]: ").strip()
        server_port = int(port_input) if port_input else 5555
    
    client = ChatClient(server_host, server_port)
    client.run()


if __name__ == '__main__':
    main()