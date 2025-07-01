import asyncio
import websockets
import traceback
from buffer import MyBuffer
from player import Player, player_bitmask_layout
from enum import IntEnum, auto
import aioconsole
import time

# Ip onde o servidor ouve

# Local host
server_ip = "0.0.0.0"
# Hamachi
#server_ip = "25.3.218.182"

debug_send_packet = False
debug_received_packet = False

#server_port = 9913
server_port = 8080

# Lista de conexões
players = {}
new_id = 0

CONNECTION_LOCK = asyncio.Lock()
DISCONNECTION_LOCK = asyncio.Lock()
TEST_LOCK = asyncio.Lock()

# --- Constantes do loop do jogo no servidor --- #

TICK_RATE = 30.0 # 20 atualizações por segundo
DELTA = 1.0/TICK_RATE # O tempo fixo de cada tick


friendly_fire_enabled = False
tick_count = 0
last_print_time = time.time()


async def game_loop():
    global tick_count, last_print_time
    i=0
    
    last_tick_time = time.time()
    while True:
        now_time = time.time()
        
        real_delta = now_time - last_tick_time
        last_tick_time = now_time
        
        tick_count +=1
        tick_start_time = time.time()
        # INICIO
        
        # Lógica para imprimir o contador a cada segundo
        current_time = time.time()
        if current_time - last_print_time >= 1.0:
            print("------ PYTHON UPDATES POR SEGUNDO: ", tick_count)
            tick_count = 0 # Reseta o contador
            last_print_time = current_time

        for p in players.values():
            if(p.input_direction_x != 0 or p.input_direction_y != 0):
                print("@@@@@@@@@@MOVENDO PLAYER@@@@@@@@@@@@@@@@@@ ")
                print(p.input_direction_x)
                print(p.input_direction_y)
                p.x += p.input_direction_x * p.speed * real_delta
                p.y += p.input_direction_y * p.speed * real_delta
                if(p.y > 500):
                    p.y = 500
                await send_player_updated(p)


            #   await send_player_updated(p)


        #print(i)

        # FIM

        tick_end_time = time.time()
        #sleep_duration = DELTA - (tick_end_time - tick_start_time)
        #if sleep_duration > 0:
        await asyncio.sleep(0.0001)



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
    connection_state = type(player.websocket.state)

    if player.websocket.state != connection_state.OPEN:
        print(f"==FAILED TO SEND PACKET TO {player.id} STATE: {player.websocket.state.name}===")
        return

    if(debug_send_packet):
        print(f"==SENDING PACKET TO {player.id}==")
        #print(packet.get_data_array())
        print(list(packet.get_data_array()))

    try:
        await player.websocket.send(packet.get_data_array())

    except websockets.exceptions.ConnectionClosed as e:
        print(f"==FAILED TO SEND PACKET TO {player.id} ==")

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
        elif data_type == 's16':
            buffer.write_s16(player_attribute)
        elif data_type == 'u32':
            buffer.write_u32(player_attribute)
        elif data_type == 'u64':
            buffer.write_u64(player_attribute)
        elif data_type == 'float':
            buffer.write_float(player_attribute)
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

        #case Network.REQUEST_CONNECT:
        #    await handle_request_connect(buffer, player)

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

async def handle_request_connect(player):
    print("===REQUEST CONNECT===")

    print(str(player))


    # Lista de tuplas ex ('u16', player.x)
    payload_to_write = []

    # Monta a lista do payload com cada atributo e seu valor 
    for attribute, _, data_type in player_bitmask_layout:
        payload_to_write.append( (data_type, getattr(player, attribute)) )
        # Resultado = ("u8", pegar atributo (classe, valor do atributo))
        # Ex:       [ ("u8", 100), ("u16", 500) ... ]

    # Montagem do Header (evento, quem conectou (eu ou outro player), player.id)
    buffer = MyBuffer()
    buffer.clear()
    buffer.write_u8(Network.PLAYER_CONNECTED)
    buffer.write_u8(Network.PLAYER_CONNECTED) 
    buffer.write_u8(player.id)

    # Monta o buffer com payload
    await write_payload_to_buffer(buffer, payload_to_write)

    # Avisa a si mesmo que foi conectado
    print(f"SENDING PLAYER CONNECTED {player.id} to {player.id} SELF")
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
    print(f"SENDING OTHER PLAYER CONNECTED: {player.id} to ALL")
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

        print(f"SENDING OTHER PLAYER CONNECTED OTHER:{other_player.id} to {player.id}")
        await send_packet(buffer_other, player)

async def send_player_updated(player):
    print("===SENDING PLAYER UPDATED TO ALL===")
    print(str(player))

    if len(player._changed_attributes) == 0:
        print("==NO CHANGED ATTRIBUTES TO SEND==")
        return

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
    buffer = MyBuffer()
    buffer.clear()
    buffer.write_u8(Network.PLAYER_UPDATED)
    buffer.write_u8(player.id)
    buffer.write_u16(mask)

    # Payload
    await write_payload_to_buffer(buffer, payload_to_write)

    await send_packet_to_all(buffer)

async def handle_request_player_move(buffer, player):
    print("===REQUEST PLAYER MOVE===")

    # Lê a posição do player
    input_direction_x = buffer.read_float()
    input_direction_y = buffer.read_float()
    # Se clicou fora da area de jogo

    player.input_direction_x = input_direction_x
    player.input_direction_y = input_direction_y

    # Atualiza a posição do player
    #player.x += int(new_x * player.speed * 1.0/30.0)
    #player.y += int(new_y * player.speed * 1.0/30.0)

    #if(player.y > 500):
    #    player.y = 500

    #print(f'{player.x} {player.y} @@@@@@@@@@@@@@@@')

    print(str(player))


    #await send_player_updated(player)

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

    if (players[player_damaged_id].is_alive == False):
        return

    await damage_id(player_damaged_id, damage)  # Aplica o dano ao player

    chat_text = ''

    buffer.clear()

    # Se o player morreu
    if players[player_damaged_id].is_alive == False: 

        # Se foi suicídio
        if(player_damaged_id == player_damager_id):
            chat_text = f"[color=red]< PLAYER {player_damaged_id} SE MATOU PQ A TIFA REVELOU QUE DA >[/color]"
            await send_chat_message_to_all(chat_text)
            #await send_player_updated(players[player_damaged_id])
            return


        players[player_damager_id].total_kills += 1

        await send_player_updated(players[player_damaged_id])  # Envia o player danificado atualizado
        await send_player_updated(players[player_damager_id])  # Envia o player que causou o dano atualizado

        chat_text =  f"[color=red][PLAYER {player_damager_id} MATOU O PLAYER {player_damaged_id}] [/color] "

        await send_chat_message_to_all(chat_text)
        await send_ranking_updated()  # Atualiza o ranking

    else: 

        pass
        #await send_player_updated(players[player_damaged_id])   # Envia o player danificado atualizado

async def handle_request_player_respawn(buffer, player):
    print("===REQUEST PLAYER RESPAWN===")

    respawned_id = buffer.read_u8()

    player.respawn()  # Reseta o player

    await send_player_updated(player)

async def handle_request_player_change_team(buffer, player):
    print("===REQUEST PLAYER CHANGE TEAM===")

    player.change_team_id()

    await send_player_updated(player)

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

async def damage_id(player_to_damage_id, damage):
    players[player_to_damage_id].take_damage(damage)

    await send_player_updated(players[player_to_damage_id])

async def kill_id(player_to_kill_id):
    players[player_to_kill_id].kill()

    await send_player_updated(players[player_to_kill_id])

async def kill_all():
    for p in players.values():
        await kill_id(p.id)

async def kill_all_except(player_to_ignore_id):
    for p in players.values():
        if p.id != player_to_ignore_id:
            await kill_id(p.id)

async def respawn(player_to_respawn_id):
    players[player_to_respawn_id].respawn()

    await send_player_updated(players[player_to_respawn_id])

async def respawn_id(player_to_respawn_id):
    players[player_to_respawn_id].respawn()

    await send_player_updated(players[player_to_respawn_id])

async def respawn_all():
    for p in players.values():
        await respawn_id(p.id)

async def respawn_all_dead():
    for p in players.values():
        if not p.is_alive:
            await respawn_id(p.id)

async def move_all():
    # Ordena os jogadores por id
    players_sorted = sorted(players.values(), key=lambda p: p.id, reverse=False)

    i = 0
    j = 200
    pos_x = 100
    pos_y = 100

    index = 0
    for i in range(4):
        for j in range(4):
            if(index >= len(players_sorted)):
                break

            players_sorted[index].x = pos_x
            players_sorted[index].y = pos_y
            pos_x += 50
            await send_player_updated(players_sorted[index])
            index += 1
        pos_x = 100
        pos_y += 50



#  ----- [ COMANDOS ] ----- #

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
    elif command_name == "damageid" or command_name == "di":
            await command_damage_id(args, player)
    elif command_name == "killid" or command_name == "ki":
            await command_kill(args, player)
    elif command_name == "killall" or command_name == "kia":
            await command_kill_all(args, player)
    elif command_name == "killallexcept" or command_name == "kiae":
            await command_kill_all_except(args, player)
    elif command_name == "respawn" or command_name == "re":
            await command_respawn(args, player)
    elif command_name == "respawnid" or command_name == "rei":
            await command_respawn_player_w_id(args, player)
    elif command_name == "respawnall" or command_name == "rea":
            await command_respawn_all(args, player)
    elif command_name == "respawnalldead" or command_name == "read":
            await command_respawn_all_dead(args, player)
    elif command_name == "moveall" or command_name == "ma":
            await command_move_all(args, player)
    else:
        await send_chat_message_to_player("Invalid command", player)

async def command_friendly_fire(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    global friendly_fire_enabled

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

async def command_damage_id(args, player):
    args_needed = 2


    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return
    try:
        player_to_damage_id = int(args[0])
        damage = int(args[1])
    except:
        await send_chat_message_to_player("Invalid arguments", player)
        return
    if player_to_damage_id not in players:
        await send_chat_message_to_player("Invalid player id", player)
        return
    if (damage <= 0):
        await send_chat_message_to_player("Invalid damage", player)


    await damage_id(player_to_damage_id, damage)

    await send_chat_message_to_all("Player " + str(player_to_damage_id) + "took " + str(damage) + " damage")

async def command_kill(args, player):
    args_needed = 1

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return
    try:
        player_to_kill_id = int(args[0])
    except:
        await send_chat_message_to_player("Invalid arguments", player)
        return
    if player_to_kill_id not in players:
        await send_chat_message_to_player("Invalid player id", player)
        return


    await kill_id(player_to_kill_id)

    await send_chat_message_to_all("Player " + str(player_to_kill_id) + " was killed")

async def command_kill_all(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    await kill_all()

    await send_chat_message_to_all("Player " + str(player.id) + " killed all players")

async def command_kill_all_except(args, player):
    args_needed = 1

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return
    try:
        player_to_ignore_id = int(args[0])
    except:
        await send_chat_message_to_player("Invalid arguments", player)
        return
    if  player_to_ignore_id not in players:
        await send_chat_message_to_player("Invalid player id", player)
        return

    await kill_all_except(player_to_ignore_id)

    await send_chat_message_to_all("Player " + str(player.id) + " killed everyone except player " + str(player_to_ignore_id))

async def command_respawn(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    await respawn(player.id)

    await send_chat_message_to_all("Player " + str(player.id) + " respawned")

async def command_respawn_player_w_id(args, player):
    args_needed = 1

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return
    try:
        player_to_respawn_id = int(args[0])
    except:
        await send_chat_message_to_player("Invalid arguments", player)
        return
    if player_to_respawn_id not in players:
        await send_chat_message_to_player("Invalid player id", player)
        return

    await respawn_id(player_to_respawn_id)

    await send_chat_message_to_all("Player " + str(player_to_respawn_id) + " respawned")

async def command_respawn_all(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    await respawn_all()

    await send_chat_message_to_all("Player " + str(player.id) + " respawned all players")

async def command_respawn_all_dead(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    await respawn_all_dead()

    await send_chat_message_to_all("Player " + str(player.id) + " respawned all dead players")

async def command_move_all(args, player):
    args_needed = 0

    if(len(args) != args_needed):
        await send_chat_message_to_player("Invalid arguments", player)
        return

    await move_all()

    await send_chat_message_to_all("Player " + str(player.id) + " moved all players")




#Couroutine executada com a conexão recebida
async def handler(websocket):

    print("Connection received: ", websocket.remote_address)

    player = None

    async with CONNECTION_LOCK:

        global new_id

        player = Player(websocket, new_id)

        # Acrescenta o player no dictionary. id: player
        players[new_id] = player

        new_id += 1

        print(f"Player {player.id} entrou na seção crítica. Total de players: {len(players)}")

        await handle_request_connect(player)



    try:
        while True: #Fica ouvindo as mensagens recebidas de cada websocket para sempre, mantendo a conexão ligada
            packet = await websocket.recv() #
            #print(packet)
            #print(*packet)

            # Received Packets com o buffer recebido e o Id de quem enviou
            await received_packets(packet, player)

    except websockets.exceptions.ConnectionClosed as e:

            print(f"Player ID {player.id} disconnected", e)

            async with DISCONNECTION_LOCK:

                player_removed_id = player.id

                if (player_removed_id in players):
                    # Futuramente fazer uma def pra matar e desconectar o player
                    #await kill_id(player_removed_id) 
                    del players[player_removed_id]

                print(f"Player {player.id} removido da lista. Total de players: {len(players)}")

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

    game_loop_task = asyncio.create_task(game_loop())


    async with websockets.serve(handler, server_ip, server_port): 
        # Roda pra sempre, quando recebe uma conexão, chama o evento handler(websocket)
        await asyncio.Future() 

asyncio.run(main())


#async for msg in ws:
#        print("Recebido do cliente:", msg)