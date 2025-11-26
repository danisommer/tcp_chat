import socket
import threading
import os
import sys
from protocol import (
    MSG_QUIT, MSG_FILE, MSG_CHAT,
    send_message, receive_message, receive_file
)

DOWNLOAD_DIR = 'client_downloads'


class ChatClient:
    
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.running = True
        
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
            send_message(self.socket, MSG_FILE, filename)
            
            success, message = receive_file(self.socket, DOWNLOAD_DIR)
            print(message)
            
        except Exception as e:
            print(f"Erro ao solicitar arquivo: {e}")
    
    def receive_messages_thread(self):
        while self.running and self.connected:
            try:
                msg_type, payload = receive_message(self.socket)
                
                if msg_type is None:
                    print("\n[Sistema] Conexão encerrada pelo servidor")
                    self.connected = False
                    break
                
                if msg_type == MSG_CHAT:
                    message = payload.decode('utf-8')
                    print(f"\n{message}")
                    self.show_prompt()
                    
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
