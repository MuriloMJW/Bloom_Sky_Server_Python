# Servidor de Jogo Multiplayer em Python com `websocket` e `asyncio`

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Libs](https://img.shields.io/badge/libs-websockets%20%7C%20pygame-brightgreen)

Este repositório contém o código-fonte do backend para um jogo 2D multiplayer em tempo real. O servidor é construído inteiramente em Python, utilizando `asyncio` e `websockets` para gerenciar múltiplas conexões de jogadores de forma eficiente e não-bloqueante.

O código para o client do jogo que se conecta ao servidor pode ser encontrado em: https://github.com/MuriloMJW/Network-Game-Client

## Principais Funcionalidades
- **Comunicação em Tempo Real:** Utiliza WebSockets para uma comunicação de baixa latência entre o cliente e o servidor.
- **Arquitetura Assíncrona:** Construído sobre o `asyncio`, o servidor pode lidar com um grande número de conexões simultâneas sem a necessidade de múltiplas threads, garantindo alta performance.
- **Fluxo de Conexão Seguro:** Implementa um handshake de duas etapas (Autenticação -> Admissão no Jogo), garantindo que um jogador só entre no mundo do jogo quando seu cliente estiver totalmente carregado e pronto.
- **Protocolo de Rede Binário:** Utiliza um protocolo binário customizado para serialização de dados, o que é mais eficiente em termos de banda do que formatos baseados em texto como JSON.
- **Game Loop no Servidor:** Possui um game loop próprio que roda a um `TICK_RATE` fixo, responsável por processar a física (movimento de projéteis), colisões e outras lógicas de jogo de forma autoritativa.
- **Visualização Opcional:** Utiliza `Pygame` para criar uma janela no servidor que renderiza o estado atual do jogo, servindo como uma poderosa ferramenta de debug visual.
- **Sistema de Comandos:** Inclui um console no servidor para administração e envio de mensagens ou comandos para todos os jogadores.

## Arquitetura do Servidor
O núcleo do servidor é o **Event Loop** do `asyncio`. A biblioteca `websockets` se integra a este loop para gerenciar as conexões.

- **Um Handler por Conexão:** Para cada cliente que se conecta, o servidor instancia uma nova corrotina `handler`. Isso significa que cada jogador tem sua própria "thread" de execução lógica, com suas próprias variáveis de estado (autenticado, em jogo, etc.), garantindo isolamento e clareza.
- **Gerenciamento de Estado Global:** Estados compartilhados, como a lista de jogadores ativos (`players`) e a lista de conexões pendentes (`pending_connections`), são globais. O acesso a essas estruturas é protegido por `asyncio.Lock` para prevenir condições de corrida (`race conditions`) durante a conexão ou desconexão de múltiplos jogadores.
- **Handshake de Duas Etapas:**
    1.  **Autenticação:** O cliente envia credenciais. O servidor valida e, se bem-sucedido, move a conexão para um estado "autenticado, aguardando admissão" (no dicionário `pending_connections`). O jogador ainda não existe no mundo do jogo.
    2.  **Admissão:** Após a cena do jogo carregar, o cliente envia um pedido de "entrar no jogo". O servidor verifica se a conexão já foi autenticada, e só então cria a instância do `Player`, a insere no mundo e sincroniza o estado do jogo com o cliente.

## Protocolo de Rede
A comunicação é feita através de pacotes binários customizados, gerenciados pela classe `MyBuffer`. A estrutura geral de um pacote é:
`[ID da Mensagem (u8)] [Payload...]`

O `Payload` varia de acordo com o ID da mensagem. Alguns dos principais IDs são:
- `REQUEST_AUTH` (Cliente -> Servidor): Envia credenciais para autenticação.
- `AUTH_SUCCESS` / `AUTH_FAILURE` (Servidor -> Cliente): Responde ao pedido de autenticação.
- `REQUEST_ENTER_GAME` (Cliente -> Servidor): Sinaliza que o cliente carregou o jogo e está pronto para "spawnar".
- `PLAYER_CONNECTED` (Servidor -> Cliente): Envia os dados completos de um jogador que acabou de entrar.
- `PLAYER_UPDATED` (Servidor -> Cliente): Envia atualizações parciais de estado de um jogador (posição, vida, etc.) usando uma bitmask.
- `OTHER_PLAYER_DISCONNECTED` (Servidor -> Cliente): Notifica que um jogador saiu.

## Requisitos
- Python 3.9 ou superior
- Bibliotecas Python:
    - `websockets`
    - `pygame` (para a janela de debug do servidor)
    - `aioconsole` (para o input de comandos no terminal do servidor)

## Instalação e Configuração

1.  **Clone o repositório:**

2.  **Crie o arquivo `requirements.txt`:**
    Se você ainda não tem este arquivo, gere-o a partir das bibliotecas que você já instalou no seu ambiente:
    ```bash
    pip freeze > requirements.txt
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure o IP e a Porta:**
    Abra o arquivo principal do servidor (ex: `server.py`) e ajuste as variáveis globais `server_ip` e `server_port` conforme necessário.

## Como Executar
Com o ambiente virtual ativado e as dependências instaladas, simplesmente execute o script principal:

```bash
python server.py
```

## Estrutura do Projeto
Uma visão geral dos arquivos mais importantes e suas responsabilidades.

```
.
├── server.py             # Script principal: inicia o servidor, gerencia o game loop e o handler de conexões.
├── player.py             # Definição da classe Player, que representa um jogador no mundo do jogo.
├── bullet.py             # Definição da classe Bullet, para os projéteis disparados.
├── network.py            # Enum Network com todos os IDs dos pacotes de rede para uma comunicação organizada.
├── buffer.py             # Classe MyBuffer para ler e escrever dados no protocolo binário customizado.
└── requirements.txt      # Lista de dependências Python para fácil instalação do ambiente.
```
