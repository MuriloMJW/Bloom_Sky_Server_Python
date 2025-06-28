import asyncio
import websockets
import traceback
from buffer import MyBuffer
from player import Player, player_bitmask_layout
from enum import IntEnum, auto
import aioconsole

# Ip onde o servidor ouve

# Local host
server_ip = "0.0.0.0"
# Hamachi
#server_ip = "25.3.218.182"

debug_send_packet = True
debug_received_packet = False

server_port = 9913
#server_port = 8080

# Lista de conexões
players = {}
friendly_fire_enabled = False

new_id = 0


class Network(IntEnum):
    # Client -> Server
    REQUEST_CONNECT = 0

    REQUEST_PLAYER_MOVE = 1

    REQUEST_PLAYER_SHOOT = 2
    REQUEST_PLAYER_DAMAGE = 3
    REQUEST_PLAYER_RESPAWN = 4
    REQUEST_PLAYER_CHANGE_TEAM = 5
    REQUEST_PLAYER_SONIC = 6

    REQUEST_PLAYER_UPDATE = 7
    CHAT_MESSAGE = 100
    PING = 254

    # Server -> Client
    PLAYER_CONNECTED = 100
    OTHER_PLAYER_CONNECTED = 101
    OTHER_PLAYER_DISCONNECTED = 102

    PLAYER_MOVED = 103          
    OTHER_PLAYER_MOVED = 104

    PLAYER_SHOOT = 105
    OTHER_PLAYER_SHOOT = 106
    PLAYER_DAMAGED = 107
    PLAYER_KILLED = 108
    PLAYER_RESPAWNED = 109
    PLAYER_CHANGED_TEAM = 110
    PLAYER_SONICKED = 111

    PLAYER_UPDATED = 112 
    PLAYER_SETUP = 113
    
    RANKING_UPDATED = 199
    CHAT_RECEIVED = 200
    PONG = 255


# ----- [ MÉTODOS DE TRATAMENTO DE PACKETS ] ----- #

async def send_packet(packet : MyBuffer, player : Player):
    if(debug_send_packet):
        print(f"==SENDING PACKET TO {player.id}==")
        print(packet.get_data_array())
        print(list(packet.get_data_array()))

    await player.websocket.send(packet.get_data_array())

async def send_packet_to_all(packet : MyBuffer):
    # Avisa a todos os jogadores o chat
    for other_player in players.values():
        await send_packet(packet, other_player)

async def send_packet_to_all_except(packet, player_except):
    for other_player in players.values():
        if(other_player.id != player_except.id):
            await send_packet(packet, other_player)

async def write_payload_to_buffer(buffer, payload_to_write):
    
    for data_type, player_attribute in payload_to_write:
        if data_type == 'u8':
            buffer.write_u8(player_attribute)
        elif data_type == 'u16':
            buffer.write_u16(player_attribute)
        elif data_type == 'u32':
            buffer.write_u32(player_attribute)
        elif data_type == 'u64':
            buffer.write_u64(player_attribute)
        elif data_type == 'string':
            buffer.write_string(player_attribute)
   
async def received_packets(packet, player):

    buffer = MyBuffer(packet)

    if(debug_received_packet):
        print("==RECEIVED PACKET==")
        print(buffer.get_data_array())
        print(list(buffer.get_data_array()))


    msgid = buffer.read_u8()

    match msgid:

        case Network.REQUEST_CONNECT:
            await handle_request_connect(buffer, player)

        case Network.REQUEST_PLAYER_MOVE:
            await handle_request_player_move(buffer, player)

        case Network.REQUEST_PLAYER_SHOOT:
            await handle_request_player_shoot(buffer, player)

        case Network.REQUEST_PLAYER_DAMAGE:
            await handle_request_player_damage(buffer, player)

        case Network.REQUEST_PLAYER_RESPAWN:
            await handle_request_player_respawn(buffer, player)

        case Network.REQUEST_PLAYER_CHANGE_TEAM:
            await handle_request_player_change_team(buffer, player)

        case Network.REQUEST_PLAYER_SONIC:
            await handle_request_player_sonic(buffer, player)

        case Network.CHAT_MESSAGE:
            await _handle_chat_message(buffer, player)

        case Network.PING:
            await _handle_ping(buffer, player)

        case _:
            print("UNKNOWN PACKET ID: ", msgid)

# ----- [ PEDIDOS DO CLIENT] ----- #

async def handle_request_connect(buffer, player):
    print("===SENDING PLAYER UPDATED TO ALL===")

    print(str(player))
    
    
    # Lista de tuplas ex ('u16', player.x)
    payload_to_write = []
    
    # Monta a lista do payload com cada atributo e seu valor 
    for attribute, _, data_type in player_bitmask_layout:
        payload_to_write.append( (data_type, getattr(player, attribute)) )
        # Resultado = ("u8", pegar atributo (classe, valor do atributo))
        # Ex:       [ ("u8", 100), ("u16", 500) ... ]
    
    # Montagem do Header (evento, quem conectou (eu ou outro player), player.id)
    buffer.clear()
    buffer.write_u8(Network.PLAYER_CONNECTED)
    buffer.write_u8(Network.PLAYER_CONNECTED) 
    buffer.write_u8(player.id)
    
    # Monta o buffer com payload
    await write_payload_to_buffer(buffer, payload_to_write)
    
    # Avisa a si mesmo que foi conectado
    await send_packet(buffer, player)
    
    # Avisar todos os jogadores que eu me conectei
    buffer_other = MyBuffer()
    buffer_other.clear()
    buffer_other.write_u8(Network.PLAYER_CONNECTED)
    buffer_other.write_u8(Network.OTHER_PLAYER_CONNECTED) # Me envia como other player
    buffer_other.write_u8(player.id)

    # Monta o buffer com payload
    await write_payload_to_buffer(buffer_other, payload_to_write)

    # Avisa todos os jogadores que me conectei
    await send_packet_to_all_except(buffer_other, player)
    
    # Avisa ao novo Player que conectou o dado de TODOS
    for other_player in players.values():
        if other_player.id == player.id: # Não avisa a si mesmo
            continue
        
        other_payload_to_write = []
        
        for attribute, _, data_type in player_bitmask_layout:
            other_payload_to_write.append( (data_type, getattr(other_player, attribute)) )

        buffer_other.clear()
        buffer_other.write_u8(Network.PLAYER_CONNECTED)
        buffer_other.write_u8(Network.OTHER_PLAYER_CONNECTED)
        buffer_other.write_u8(other_player.id)
        
        await write_payload_to_buffer(buffer_other, other_payload_to_write)

        await send_packet(buffer_other, player)

async def send_player_updated(buffer, player):
    print("===SENDING PLAYER UPDATED TO ALL===")

    print(str(player))
    
    
    # Lista de tuplas ex ('u16', player.x) a
    payload_to_write = []
    
    # Criar a mascara e a lista de payloads
    mask = 0
    for attribute, bitmask, data_type in player_bitmask_layout:
        if attribute in player._changed_attributes: # 
            mask |= bitmask
            payload_to_write.append( (data_type, getattr(player, attribute)) )
            
    player._changed_attributes.clear()  # Limpa o conjunto de stats alterados
    
    # Header
    buffer.clear()
    buffer.write_u8(Network.PLAYER_UPDATED)
    buffer.write_u8(player.id)
    buffer.write_u8(mask)
    
    # Payload
    await write_payload_to_buffer(buffer, payload_to_write)

    await send_packet_to_all(buffer)
 
async def handle_request_player_move(buffer, player):
    print("===REQUEST PLAYER MOVE===")

    # Lê a posição do player
    new_x = buffer.read_u16()
    new_y = buffer.read_u16()
    
    # Se clicou fora da area de jogo
    if(new_y > 500):
        return

    # Atualiza a posição do player
    player.x = new_x
    player.y = new_y

    print(str(player))


    await send_player_updated(buffer, player)

    #await send_packet(buffer, player)

async def handle_request_player_shoot(buffer, player):
    print("===REQUEST PLAYER SHOOT===")
    buffer.clear()
    buffer.write_u8(Network.PLAYER_SHOOT)
    buffer.write_u8(player.id)

    await send_packet_to_all(buffer)

async def handle_request_player_damage(buffer, player):
    print("===REQUEST PLAYER DAMAGE===")
    player_damaged_id = buffer.read_u8()
    player_damager_id = buffer.read_u8()
    damage = buffer.read_u8()
    
    
    
    if (player_damaged_id != player_damager_id                                   # Se quem causou dano foi outro player E
    and players[player_damaged_id].team_id == players[player_damager_id].team_id # Não são do mesmo time E
    and not friendly_fire_enabled):                                              # O friendly fire está desativado
        return                                                                   # Não faz nada  
    players[player_damaged_id].take_damage(damage) # Aplica o dano ao player

    chat_text = ''

    buffer.clear()

    # Se o player morreu
    if players[player_damaged_id].is_alive == False: 
        
        # Se foi suicídio
        if(player_damaged_id == player_damager_id):
            chat_text = f"[color=red]< PLAYER {player_damaged_id} SE MATOU PQ A TIFA REVELOU QUE DA >[/color]"
            await send_chat_message_to_all(chat_text)
            await send_player_updated(buffer, players[player_damaged_id])
            return
        
        
        players[player_damager_id].total_kills += 1
        
        await send_player_updated(buffer, players[player_damaged_id])  # Envia o player danificado atualizado
        await send_player_updated(buffer, players[player_damager_id])  # Envia o player que causou o dano atualizado
        
        chat_text =  f"[color=red][PLAYER {player_damager_id} MATOU O PLAYER {player_damaged_id}] [/color] "
        #chat_text += f"[KILLS: {players[player_damager_id].total_kills} | "
        #chat_text += f"DEATHS: {players[player_damager_id].total_deaths}][/color]"

        await send_chat_message_to_all(chat_text)
        await send_ranking_updated()  # Atualiza o ranking
        
    else: 
        
        
        await send_player_updated(buffer, players[player_damaged_id])   # Envia o player danificado atualizado

async def handle_request_player_respawn(buffer, player):
    print("===REQUEST PLAYER RESPAWN===")

    respawned_id = buffer.read_u8()

    player.respawn()  # Reseta o player

    await send_player_updated(buffer, player)

async def handle_request_player_change_team(buffer, player):
    print("===REQUEST PLAYER CHANGE TEAM===")

    player.change_team_id()

    await send_player_updated(buffer, player)

async def handle_request_player_sonic(buffer, player):
    print("===REQUEST PLAYER SONIC===")


    buffer.clear()
    buffer.write_u8(Network.PLAYER_SONICKED)
    buffer.write_u8(player.id)
    await send_packet_to_all(buffer)

async def _handle_chat_message(buffer, player):
    print("===CHAT MESSAGE===")

    message_received = buffer.read_string()

    if message_received[0] == "/":
        await commands(message_received, player)
        return

    
    
    chat_text = "["+str(player.id)+"] "

    
    
    chat_text += message_received
    print(chat_text)
    
    buffer.clear()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet_to_all(buffer)
    
    # Easter Egg
    if message_received == "RAT ATTACK":
 
        for p in players.values():
            buffer_rat = MyBuffer()
            buffer_rat.clear()
            buffer_rat.write_u8(p.id)
            buffer_rat.write_u8(player.id)
            buffer_rat.write_u8(100)
            buffer_rat.seek_start()
            await handle_request_player_damage(buffer_rat, player) # Dano de 1 HP para todos os players quando alguém envia uma mensagem no chat
        
        message = "RAT ATTACK\n"*10
        message += f"PLAYER {player.id} MANDOU OS RATO MATAR VCS TUDO"
            
        #await send_chat_message_to_all(message) # Envia mensagem de chat para todos os players

async def _handle_ping(buffer, player):
    #print("===PING===")

    time_stamp = buffer.read_u64()  # Lê o PING enviado pelo cliente

    buffer.clear()
    buffer.write_u8(Network.PONG)
    buffer.write_u64(time_stamp)

    await send_packet(buffer, player)

# ----- [ MÉTODOS DO SERVIDOR ] ----- #
async def send_chat_message_to_player(chat_text, player):
    buffer = MyBuffer()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet(buffer, player) 

async def send_chat_message_to_all(chat_text):
    buffer = MyBuffer()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet_to_all(buffer) 

async def send_ranking_updated():
    print("===SENDING RANKING UPDATED===")
    
    # Ordena os jogadores por total_kills
    players_ranked = sorted(players.values(), key=lambda p: p.total_kills, reverse=True)
    
    i = 0
    ranking_text = f"======= RANKING =======\n"
    for p in players_ranked:
        i+= 1
        ranking_text += f"{i} Player {p.id} [color='gold'] {p.total_kills} [/color] / [color='red'] {p.total_deaths} [/color]\n"
        
    #await send_chat_message_to_all(ranking_text)
    
    buffer = MyBuffer()
    buffer.write_u8(Network.RANKING_UPDATED)
    buffer.write_string(ranking_text)
    await send_packet_to_all(buffer)

async def toggle_friendly_fire():
    global friendly_fire_enabled
    friendly_fire_enabled = not friendly_fire_enabled


#  ----- [ COMANDOS] ----- #

async def commands(command_string, player):
    
    # Se a string ta vazia ou possui menos de 2 caracteres
    if not command_string or len(command_string) < 2:
        return
    
    
    parts = command_string[1:].lower().split()
    command_name = parts[0]
    args = parts[1:]
    
    
    if command_name == "friendlyfire" or command_name == "ff":
            await command_friendly_fire(args, player)
    elif command_name == "playerlist" or command_name == "pl":
            await command_playerlist(args, player)
    else:
        await send_chat_message_to_player("Invalid command", player)

            
async def command_friendly_fire(args, player):
    args_needed = 0
    
    global friendly_fire_enabled
    
    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid command", player)
        return
    
    await toggle_friendly_fire()
    
    if friendly_fire_enabled:
        await send_chat_message_to_all("Friendly fire enabled")
    else:
        await send_chat_message_to_all("Friendly fire disabled")
       
async def command_playerlist(args, player):
    args_needed = 0
    
    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid command", player)
        return
    
    chat_message = f"Players online:"
    for p in players.values():
        chat_message += f"\n{str(p)}"
    
    await send_chat_message_to_all(chat_message)






#Couroutine executada com a conexão recebida
async def handler(websocket):

    print("Connection received: ", websocket.remote_address)

    global new_id

    player = Player(websocket, new_id)

    # Acrescenta o player no dictionary. id: player
    players[new_id] = player

    new_id += 1

    try:
        while True: #Fica ouvindo as mensagens recebidas de cada websocket para sempre, mantendo a conexão ligada
            packet = await websocket.recv() #
            #print(packet)
            #print(*packet)

            # Received Packets com o buffer recebido e o Id de quem enviou
            await received_packets(packet, player)

    except websockets.exceptions.ConnectionClosed as e:

            print(f"Player ID {player.id} disconnected", e)
            player_removed_id = player.id
            del players[player_removed_id]

            buffer = MyBuffer()

            buffer.write_u8(Network.OTHER_PLAYER_DISCONNECTED)
            buffer.write_u8(player_removed_id)

            await send_packet_to_all(buffer)


    print("Connection finished")

async def read_input():
    while True:
        msg = await aioconsole.ainput()
        await send_chat_message_to_all(msg)
        await asyncio.sleep(0.1)

async def main():
    global server_ip
    global server_port

    print(f"Listening on {server_ip}:{server_port}...")
    # Websockets.serve, internamente chama um await handler(websocket) 
    # e passa magicamente o socket para ele

    input_task = asyncio.create_task(read_input())

    async with websockets.serve(handler, server_ip, server_port): 
        # Roda pra sempre, quando recebe uma conexão, chama o evento handler(websocket)
        await asyncio.Future() 

asyncio.run(main())


#async for msg in ws:
#        print("Recebido do cliente:", msg)