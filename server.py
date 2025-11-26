import socket
import threading
import os
import sys
from protocol import (
    MSG_QUIT, MSG_FILE, MSG_CHAT,
    send_message, receive_message, send_file
)

HOST = '0.0.0.0'
PORT = 5555
FILES_DIR = 'server_files'

clients_lock = threading.Lock()
clients = []
client_counter = 0


class ClientHandler(threading.Thread):
    
    def __init__(self, client_socket, client_address, client_id):
        super().__init__()
        self.socket = client_socket
        self.address = client_address
        self.client_id = client_id
        self.running = True
        
    def run(self):
        print(f"[Cliente {self.client_id}] Conectado de {self.address}")
        
        try:
            while self.running:
                msg_type, payload = receive_message(self.socket)
                
                if msg_type is None:
                    break
                
                if msg_type == MSG_QUIT:
                    self.handle_quit()
                    break
                    
                elif msg_type == MSG_FILE:
                    self.handle_file_request(payload)
                    
                elif msg_type == MSG_CHAT:
                    self.handle_chat_message(payload)
                    
                else:
                    print(f"[Cliente {self.client_id}] Comando desconhecido: {msg_type}")
                    
        except Exception as e:
            print(f"[Cliente {self.client_id}] Erro: {e}")
            
        finally:
            self.cleanup()
    
    def handle_quit(self):
        print(f"[Cliente {self.client_id}] Requisição de desconexão")
        self.running = False
    
    def handle_file_request(self, payload):
        filename = payload.decode('utf-8').strip()
        print(f"[Cliente {self.client_id}] Solicitou arquivo: '{filename}'")
        
        filepath = os.path.join(FILES_DIR, filename)
        
        success = send_file(self.socket, filepath)
        
        if success:
            print(f"[Cliente {self.client_id}] Arquivo '{filename}' enviado com sucesso")
        else:
            print(f"[Cliente {self.client_id}] Falha ao enviar arquivo '{filename}'")
    
    def handle_chat_message(self, payload):
        message = payload.decode('utf-8')
        print(f"[CHAT] Cliente {self.client_id}: {message}")
    
    def send_chat(self, message):
        try:
            send_message(self.socket, MSG_CHAT, message)
        except Exception as e:
            print(f"[Cliente {self.client_id}] Erro ao enviar chat: {e}")
    
    def cleanup(self):
        print(f"[Cliente {self.client_id}] Desconectado")
        
        with clients_lock:
            clients[:] = [c for c in clients if c[2] != self.client_id]
        
        try:
            self.socket.close()
        except:
            pass


def broadcast_message(message, exclude_id=None):
    with clients_lock:
        for client_socket, client_addr, client_id in clients:
            if exclude_id is None or client_id != exclude_id:
                try:
                    send_message(client_socket, MSG_CHAT, message)
                except Exception as e:
                    print(f"[Servidor] Erro ao enviar para Cliente {client_id}: {e}")


def console_input_thread():
    print("\n[Servidor] Digite mensagens para enviar a todos os clientes (ou 'quit' para parar):\n")
    
    while True:
        try:
            message = input()
            
            if message.lower() == 'quit':
                print("[Servidor] Encerrando...")
                os._exit(0)
                
            if message.strip():
                broadcast_message(f"[SERVIDOR]: {message}")
                print(f"[Broadcast] Mensagem enviada: {message}")
                
        except EOFError:
            break
        except Exception as e:
            print(f"[Servidor] Erro no console: {e}")


def main():
    global client_counter
    
    os.makedirs(FILES_DIR, exist_ok=True)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        
        print("="*60)
        print(f"Servidor TCP Multithread iniciado")
        print(f"Escutando em {HOST}:{PORT}")
        print(f"Diretório de arquivos: {os.path.abspath(FILES_DIR)}")
        print("="*60)
        
        console_thread = threading.Thread(target=console_input_thread, daemon=True)
        console_thread.start()
        
        while True:
            print("\n[Servidor] Aguardando conexões...")
            
            client_socket, client_address = server_socket.accept()
            
            client_counter += 1
            client_id = client_counter
            
            with clients_lock:
                clients.append((client_socket, client_address, client_id))
            
            handler = ClientHandler(client_socket, client_address, client_id)
            handler.daemon = True
            handler.start()
            
    except KeyboardInterrupt:
        print("\n[Servidor] Interrompido pelo usuário")
        
    except Exception as e:
        print(f"[Servidor] Erro: {e}")
        
    finally:
        with clients_lock:
            for client_socket, _, _ in clients:
                try:
                    client_socket.close()
                except:
                    pass
        
        server_socket.close()
        print("[Servidor] Encerrado")


if __name__ == '__main__':
    main()
