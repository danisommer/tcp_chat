# Trabalho TCP - Cliente/Servidor Multithread com Chat e Transferência de Arquivos

## Autor
Daniel Zaki Sommer  
Disciplina: Redes de Computadores

---

## Descrição do Projeto

Sistema cliente-servidor TCP que implementa:
- **Servidor multithread**: Aceita múltiplos clientes simultâneos, cada um em sua própria thread
- **Transferência de arquivos**: Suporta arquivos de qualquer tamanho (testado com >10MB)
- **Verificação de integridade**: Usa hash SHA-256 para garantir que arquivos não foram corrompidos
- **Chat bidirecional**: Clientes podem enviar mensagens ao servidor e vice-versa
- **Uso direto de sockets**: Implementação manual do protocolo TCP sem frameworks que abstraiam a comunicação

---

## Estrutura do Projeto

```
tcp_chat/
├── server.py              # Servidor TCP multithread
├── client.py              # Cliente TCP interativo
├── protocol.py            # Definição do protocolo de aplicação
├── README.md              # Esta documentação
├── server_files/          # Arquivos disponíveis no servidor
│   ├── teste_pequeno.txt
│   ├── arquivo_medio.txt
│   └── arquivo_grande.bin (15MB)
└── client_downloads/      # Arquivos baixados pelos clientes
```

---

## Protocolo de Aplicação

### Formato das Mensagens

Todas as mensagens seguem o formato binário:

```
[TAMANHO (8 bytes)][TIPO (4 bytes)][PAYLOAD (N bytes)]
```

- **TAMANHO**: Inteiro de 64 bits (big-endian) indicando o tamanho do payload
- **TIPO**: String ASCII de 4 caracteres identificando o tipo da mensagem
- **PAYLOAD**: Dados da mensagem (tamanho variável)

### Tipos de Mensagem

#### Cliente → Servidor

| Tipo | Código | Payload | Descrição |
|------|--------|---------|-----------|
| Sair | `QUIT` | (vazio) | Solicita desconexão |
| Arquivo | `FILE` | nome do arquivo (UTF-8) | Solicita download de arquivo |
| Chat | `CHAT` | mensagem (UTF-8) | Envia mensagem de texto |

#### Servidor → Cliente

| Tipo | Código | Payload | Descrição |
|------|--------|---------|-----------|
| Arquivo OK | `FROK` | (vazio) | Confirma que arquivo será enviado |
| Erro | `FERR` | mensagem de erro (UTF-8) | Indica erro (arquivo não encontrado, etc) |
| Metadados | `FMTA` | [tam_nome(4)][nome][tam_arquivo(8)] | Informações do arquivo |
| Hash | `FHSH` | hash SHA-256 (32 bytes) | Hash do arquivo completo |
| Dados | `FDAT` | chunk de dados binários | Parte do arquivo (chunks de 8KB) |
| Chat | `CHAT` | mensagem (UTF-8) | Mensagem de texto do servidor |

### Fluxo de Transferência de Arquivo

```
Cliente                                Servidor
   |                                      |
   |--- FILE "nome.txt" ----------------->|
   |                                      | (verifica se arquivo existe)
   |<------------------- FROK ------------|  ou
   |<------------------- FERR ------------|  (se não existir)
   |                                      |
   |<------------------- FMTA ------------|  (metadados)
   |<------------------- FHSH ------------|  (hash SHA-256)
   |<------------------- FDAT ------------|  (chunk 1)
   |<------------------- FDAT ------------|  (chunk 2)
   |<------------------- FDAT ------------|  (chunk N)
   |                                      |
   (calcula hash e verifica integridade)
```

---

## Como Executar

### Requisitos

- Python 3.6 ou superior
- Sistema operacional: Linux, macOS ou Windows
- Bibliotecas padrão (socket, threading, hashlib, struct, os)

### Executar o Servidor

```bash
cd tcp_chat
python3 server.py
```

O servidor iniciará e aguardará conexões na porta **5555**.

**Console do servidor:**
- Digite mensagens para enviar broadcast a todos os clientes
- Digite `quit` para encerrar o servidor

### Executar o Cliente

**Opção 1: Modo interativo**
```bash
python3 client.py
```

Será solicitado:
- IP do servidor (padrão: localhost)
- Porta (padrão: 5555)

**Opção 2: Com argumentos**
```bash
python3 client.py <IP> <PORTA>
```

Exemplo:
```bash
python3 client.py localhost 5555
```

### Comandos do Cliente

Após conectar, use os seguintes comandos:

```
chat <mensagem>        # Envia mensagem ao servidor
arquivo <nome>         # Solicita arquivo do servidor
sair                   # Desconecta do servidor
```

**Exemplos:**
```
> chat Olá, servidor!
> arquivo teste_pequeno.txt
> arquivo arquivo_grande.bin
> sair
```

---

## Recursos Implementados

### ✅ Requisitos Obrigatórios

1. **Uso direto de sockets TCP**
   - Implementação manual usando `socket.socket(AF_INET, SOCK_STREAM)`
   - Nenhuma biblioteca que abstraia a comunicação TCP

2. **Servidor multithread**
   - Aceita múltiplas conexões simultâneas
   - Cada cliente é tratado em uma thread dedicada (`threading.Thread`)
   - Lista thread-safe de clientes conectados

3. **Comando QUIT**
   - Cliente envia `QUIT` e encerra conexão
   - Servidor fecha socket e finaliza thread do cliente

4. **Transferência de arquivos**
   - Suporta arquivos de qualquer tamanho
   - Testado com arquivos >10MB
   - Envia arquivo em chunks de 8KB

5. **Verificação de integridade SHA-256**
   - Servidor calcula hash antes de enviar
   - Cliente calcula hash após receber
   - Comparação automática e notificação ao usuário

6. **Chat bidirecional**
   - Cliente → Servidor: comando `chat`
   - Servidor → Cliente(s): broadcast de mensagens
   - Mensagens exibidas em tempo real

7. **Tratamento de erros**
   - Arquivo não encontrado
   - Conexão perdida
   - Comandos inválidos

---

## Detalhes de Implementação

### Servidor (`server.py`)

**Principais funcionalidades:**

```python
# Criação do socket TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

# Aceita conexões (loop principal)
while True:
    client_socket, client_address = server_socket.accept()
    handler = ClientHandler(client_socket, client_address, client_id)
    handler.start()  # Cria nova thread
```

**Classe ClientHandler:**
- Herda de `threading.Thread`
- Loop de processamento de mensagens
- Handlers específicos para cada tipo de comando:
  - `handle_quit()`: Encerra conexão
  - `handle_file_request()`: Envia arquivo
  - `handle_chat_message()`: Processa chat

**Broadcast de mensagens:**
```python
def broadcast_message(message):
    with clients_lock:  # Thread-safe
        for client_socket, _, _ in clients:
            send_message(client_socket, MSG_CHAT, message)
```

### Cliente (`client.py`)

**Principais funcionalidades:**

```python
# Conexão TCP
self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
self.socket.connect((server_host, server_port))

# Thread para receber mensagens
receive_thread = threading.Thread(target=self.receive_messages_thread)
receive_thread.start()

# Loop principal de comandos
while self.running:
    command = input().strip()
    # Processa comandos: chat, arquivo, sair
```

**Recepção de arquivos:**
- Recebe confirmação (`FROK`) ou erro (`FERR`)
- Recebe metadados (nome e tamanho)
- Recebe hash SHA-256
- Recebe dados em chunks
- Calcula hash e verifica integridade

### Protocolo (`protocol.py`)

**Funções principais:**

```python
# Enviar mensagem
def send_message(sock, msg_type, payload):
    header = struct.pack('!Q', len(payload)) + msg_type
    sock.sendall(header + payload)

# Receber mensagem
def receive_message(sock):
    header = receive_exact(sock, HEADER_SIZE)
    payload_size, msg_type = deserialize_header(header)
    payload = receive_exact(sock, payload_size)
    return msg_type, payload

# Calcular hash SHA-256
def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.digest()
```

**Garantia de recebimento completo:**
```python
def receive_exact(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(min(num_bytes - len(data), 4096))
        if not chunk:
            return None  # Conexão fechada
        data += chunk
    return data
```

---

## Testes Realizados

### 1. Múltiplos Clientes Simultâneos
- ✅ 2+ clientes conectados ao mesmo tempo
- ✅ Cada cliente em thread independente
- ✅ Comandos processados concorrentemente

### 2. Transferência de Arquivo Grande
- ✅ Arquivo de 15MB transferido com sucesso
- ✅ Barra de progresso durante download
- ✅ Verificação de integridade bem-sucedida

### 3. Chat Bidirecional
- ✅ Cliente envia mensagens ao servidor
- ✅ Servidor envia broadcast para todos os clientes
- ✅ Mensagens exibidas em tempo real

### 4. Tratamento de Erros
- ✅ Arquivo não encontrado (mensagem de erro)
- ✅ Desconexão abrupta de cliente
- ✅ Comando inválido

### 5. Comando QUIT
- ✅ Cliente desconecta corretamente
- ✅ Servidor limpa recursos da thread
- ✅ Socket fechado adequadamente

---

## Possíveis Melhorias Futuras

- Criptografia TLS/SSL para comunicação segura
- Autenticação de usuários
- Compressão de arquivos antes da transferência
- Interface gráfica (GUI)
- Suporte a transferência de múltiplos arquivos
- Retomada de downloads interrompidos
- Diretórios e listagem de arquivos disponíveis

---

## Conclusão

Este projeto implementa com sucesso todos os requisitos do trabalho:

✅ **Sockets TCP diretos** sem bibliotecas que abstraiam a comunicação  
✅ **Servidor multithread** com threads dedicadas para cada cliente  
✅ **Transferência de arquivos grandes** (>10MB) com sucesso  
✅ **Verificação de integridade** usando hash SHA-256  
✅ **Chat bidirecional** entre servidor e clientes  
✅ **Protocolo de aplicação** bem definido e documentado  
✅ **Tratamento robusto de erros** e desconexões  