#!/usr/bin/env python3

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import ChatClient


def test_client(client_id, commands, delay=1):
    print(f"\n{'='*60}")
    print(f"TESTE CLIENTE {client_id}")
    print(f"{'='*60}\n")
    
    client = ChatClient('localhost', 5555)
    
    if not client.connect():
        print(f"Falha ao conectar cliente {client_id}")
        return
    
    import threading
    receive_thread = threading.Thread(target=client.receive_messages_thread, daemon=True)
    receive_thread.start()
    
    for cmd_type, arg in commands:
        time.sleep(delay)
        
        print(f"\n[Cliente {client_id}] Executando: {cmd_type} {arg}")
        
        if cmd_type == 'chat':
            client.send_chat_message(arg)
            
        elif cmd_type == 'arquivo':
            client.request_file(arg)
            
        elif cmd_type == 'sair':
            client.disconnect()
            break
        
        elif cmd_type == 'wait':
            print(f"[Cliente {client_id}] Aguardando {arg} segundos...")
            time.sleep(float(arg))
    
    time.sleep(2)
    client.disconnect()
    print(f"\n[Cliente {client_id}] Teste concluído")


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║     SCRIPT DE TESTE - CLIENTE/SERVIDOR TCP MULTITHREAD     ║
║                                                            ║
║  CERTIFIQUE-SE QUE O SERVIDOR ESTÁ RODANDO:               ║
║  python3 server.py                                         ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    input("Pressione ENTER quando o servidor estiver pronto...")
    
    print("\n\nIniciando testes...\n")
    
    cliente1_commands = [
        ('chat', 'Olá! Sou o Cliente 1'),
        ('wait', '2'),
        ('chat', 'Vou solicitar um arquivo pequeno'),
        ('arquivo', 'teste_pequeno.txt'),
        ('wait', '3'),
        ('chat', 'Arquivo pequeno recebido!'),
        ('sair', ''),
    ]
    
    cliente2_commands = [
        ('wait', '1'),
        ('chat', 'Cliente 2 conectado!'),
        ('wait', '3'),
        ('chat', 'Vou baixar o arquivo grande'),
        ('arquivo', 'arquivo_grande.bin'),
        ('wait', '5'),
        ('chat', 'Download do arquivo grande concluído!'),
        ('wait', '2'),
        ('sair', ''),
    ]
    
    import threading
    
    thread1 = threading.Thread(target=test_client, args=(1, cliente1_commands))
    thread2 = threading.Thread(target=test_client, args=(2, cliente2_commands))
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    print("\n\n" + "="*60)
    print("TESTES CONCLUÍDOS")
    print("="*60)
    print("\nVerifique:")
    print("  1. Múltiplos clientes conectados simultaneamente")
    print("  2. Chat bidirecional funcionando")
    print("  3. Transferência de arquivos com verificação SHA-256")
    print("  4. Desconexão limpa dos clientes")
    print("\nArquivos baixados em: client_downloads/")


if __name__ == '__main__':
    main()
