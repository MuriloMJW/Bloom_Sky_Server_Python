import asyncio
import websockets
import traceback
from buffer import MyBuffer
from enum import IntEnum, auto
import aioconsole

# Ip onde o servidor ouve

# Local host
server_ip = "0.0.0.0"
# Hamachi
#server_ip = "25.3.218.182"

debug_send_packet = False
debug_received_packet = False

server_port = 9913
#server_port = 8080

# Lista de conexões
players = {}

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
    CHAT_RECEIVED = 200
    PONG = 255


SPAWN_POSITIONS = {
    "SKY": {"x": 100, "y": 100},
    "BLOOM": {"x": 100, "y": 500}
}

class Player:

    def __init__(self, websocket, id):

        self._websocket = websocket
        self._ip = websocket.remote_address

        self._id = id

        self._team_id = id%2
        self._team = "SKY" if self._team_id == 0 else "BLOOM"

        self._x = SPAWN_POSITIONS[self.team]["x"]
        self._y = SPAWN_POSITIONS[self.team]["y"]

        self._is_alive = True
        self._hp = 100  # HP inicial do jogador



        #self.is_sonic

        self._total_kills = 0

        # --- Atributos exclusivos do Player no servidor --- #
        self.total_deaths = 0
        self._changed_stats = set() # Conjunto para armazenar quais stats foram alterados

    # --- Getters & Setters --- #

    # --- ID, Websocket e IP --- #
    @property
    def websocket(self):    
        return self._websocket

    @property
    def ip(self):
        return self._ip

    @property
    def id(self) -> int:
        return self._id

    # --- X e Y --- #
    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, new_x):
        if (new_x != self._x):
            self._x = new_x
            self._changed_stats.add("x")

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, new_y):
        if (new_y != self._y):
            self._y = new_y
            self._changed_stats.add("y")


    # --- is_alive e hp --- #
    @property
    def is_alive(self):
        return self._is_alive

    @is_alive.setter
    def is_alive(self, new_is_alive):
        if (new_is_alive != self._is_alive):
            self._is_alive = new_is_alive
            self._changed_stats.add("is_alive")

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, new_hp):
        if (new_hp != self._hp):
            self._hp = new_hp
            self._changed_stats.add("hp")

    # --- Team ID e Team --- #
    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, new_team_id):
        if (new_team_id != self._team_id):
            self._team_id = new_team_id
            self._changed_stats.add("team_id")

    @property
    def team(self):
        return self._team

    @team.setter
    def team(self, new_team):
        if (new_team != self._team):
            self._team = new_team
            self._changed_stats.add("team")

    # --- Total Kills e Total Deaths --- #
    @property
    def total_kills(self):
        return self._total_kills

    @total_kills.setter
    def total_kills(self, new_total_kills):
        if (new_total_kills != self._total_kills):
            self._total_kills = new_total_kills
            self._changed_stats.add("total_kills")

    # --- String Representation --- #

    def __str__(self):
        status = "Vivo" if self._is_alive else "Morto"
        return (
            f"Jogador {self._id} | "
            f"Time: {self._team} | "
            f"Posição: (x={self._x}, y={self._y}) | "
            f"Status: {status}"
            f" | HP: {self._hp} | "
            f"Kills: {self._total_kills} | "
            f"Deaths: {self.total_deaths} | "
            f"IP: {self._ip[0]}:{self._ip[1]}"
            f" | Team ID: {self._team_id}"
            f" | Changed Stats: {self._changed_stats}"
        )

    # --- Métodos --- #

    def take_damage(self, damage):
        if self.is_alive:
            self.hp -= damage
            if self.hp <= 0:
                self.kill()

    def kill(self):
        self.hp = 0
        self.is_alive = False
        self.total_deaths += 1

    def respawn(self):
        self.hp = 100
        self.is_alive = True
        self.x = SPAWN_POSITIONS[self.team]["x"]
        self.y = SPAWN_POSITIONS[self.team]["y"]

    def change_team_id(self):
        self.team = "BLOOM" if self._team_id == 0 else "SKY"
        self.team_id = 0 if self._team_id == 1 else 1



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

        case Network.REQUEST_PLAYER_MOVE:#
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
async def send_player_updated(buffer, player):
    print("===NEW REQUEST PLAYER UPDATE===")

    print(str(player))

    # Envia o pacote de movimento para o próprio Player

    # ====        BITMASK         === #
    BIT_X            = 1 << 0 # 0000 0001
    BIT_Y            = 1 << 1 # 0000 0010
    BIT_IS_ALIVE     = 1 << 2 # 0000 0100
    BIT_HP           = 1 << 3 # 0000 1000
    BIT_TEAM_ID      = 1 << 4 # 0001 0000
    BIT_TEAM         = 1 << 5 # 0010 0000
    BIT_TOTAL_KILLS  = 1 << 6 # 0100 0000
    
    
    player_stats_schema = [
    ('x', 1 << 0, 'u16'),
    ('y', 1 << 1, 'u16'),
    ('is_alive', 1 << 2, 'u8'),
    ('hp', 1 << 3, 'u8'),
    ('team_id', 1 << 4, 'u8'),
    ('team', 1 << 5, 'string'),
    ('total_kills', 1 << 6, 'u8')
    ]
    
    mask = 0
    payload_to_write = []
    
    #buffer.write_u16(player.x)
    
    # Criar a mascara e a lista de payloads
    for stat, bitmask, data_type in player_stats_schema:
        if stat in player._changed_stats:
            mask |= bitmask
            payload_to_write.append( (data_type, getattr(player, stat)) )
            

    # Eu acho que da pra eu otimizar isso, se eu usar uma fila fifo para o changed_stats
    # e acho que um unico loop do tamanho tamanho do conjunto de stats alterados daria conta

    # Cria a máscara de bits para os stats alterados
    # Se o player alterou algum stat, adiciona o bit correspondente à máscara
    mask = 0
    if 'x'           in player._changed_stats: mask |= BIT_X
    if 'y'           in player._changed_stats: mask |= BIT_Y
    if 'is_alive'    in player._changed_stats: mask |= BIT_IS_ALIVE
    if 'hp'          in player._changed_stats: mask |= BIT_HP
    if 'team_id'     in player._changed_stats: mask |= BIT_TEAM_ID
    if 'team'        in player._changed_stats: mask |= BIT_TEAM
    if 'total_kills' in player._changed_stats: mask |= BIT_TOTAL_KILLS

    print("MASCARA: " + bin(mask))  # Exibe a máscara em binário

    buffer.clear()
    buffer.write_u8(Network.PLAYER_UPDATED)
    buffer.write_u8(player.id)
    buffer.write_u8(mask)
    
    # Escreve os stats alterados no buffer
    if(mask & BIT_X):
        buffer.write_u16(player.x)
    if(mask & BIT_Y):
        buffer.write_u16(player.y)
    if(mask & BIT_IS_ALIVE):
        buffer.write_u8(player.is_alive)
    if(mask & BIT_HP):
        buffer.write_u8(player.hp)
    if(mask & BIT_TEAM_ID):
        buffer.write_u8(player.team_id)
    if(mask & BIT_TEAM):
        buffer.write_string(player.team)
    if(mask & BIT_TOTAL_KILLS):
        buffer.write_u8(player.total_kills)

    player._changed_stats.clear()  # Limpa o conjunto de stats alterados

    await send_packet_to_all(buffer)


async def handle_request_connect(buffer, player):
    print("===REQUEST CONNECT===")

    print(str(player))
    print(str(players[player.id]))

    # 1) Manda o Player Connect e sua posição para o novo Player
    buffer.clear()
    buffer.write_u8(Network.PLAYER_CONNECTED)
    buffer.write_u8(player.id)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.team_id)
    buffer.write_string(player.team)
    buffer.write_u8(player.is_alive)
    buffer.write_u8(player.hp)


    await send_packet(buffer, player)

    # Avisa TODOS que um novo Player conectou e sua posição
    buffer.clear()
    buffer.write_u8(Network.OTHER_PLAYER_CONNECTED)
    buffer.write_u8(player.id)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.team_id)
    buffer.write_string(player.team)
    buffer.write_u8(player.is_alive)
    buffer.write_u8(player.hp)
    await send_packet_to_all_except(buffer, player)

    await send_chat_message_to_all(f"[color=green]< PLAYER {player.id} CONECTOU! >[/color]")
    # Avisa ao novo Player que conectou a posição de TODOS

    for other_player in players.values():
        if other_player.id != player.id: # Não avisa a si mesmo

            buffer.clear()
            buffer.write_u8(Network.OTHER_PLAYER_CONNECTED)
            buffer.write_u8(other_player.id)
            buffer.write_u16(other_player.x)
            buffer.write_u16(other_player.y)
            buffer.write_u8(other_player.team_id)
            buffer.write_string(other_player.team)
            buffer.write_u8(other_player.is_alive)
            buffer.write_u8(other_player.hp)

            await send_packet(buffer, player)

async def handle_request_player_move(buffer, player):
    print("===REQUEST PLAYER MOVE===")

    # Lê a posição do player
    new_x = buffer.read_u16()
    new_y = buffer.read_u16()

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

    player.take_damage(damage) # Aplica o dano ao player

    chat_text = ''

    buffer.clear()

    if player.is_alive:
        #chat_text = f"[color=blue]< PLAYER {player_damager_id} DANOU O PLAYER {player_damaged_id} COM {damage} DE DANO >[/color]"
        #await send_chat_message_to_all(chat_text)
        #print(chat_text)
        pass

    else: # Se o player morreu, avisa que ele foi morto

        if(player_damager_id != 123):
            
            players[player_damager_id].total_kills += 1 
            
            chat_text =  f"[color=red][PLAYER {player_damager_id} MATOU O PLAYER {player_damaged_id}] "
            chat_text += f"[KILLS: {players[player_damager_id].total_kills} | "
            chat_text += f"DEATHS: {players[player_damager_id].total_deaths}][/color]"
            
        else:
            chat_text = f"[color=red]< PLAYER {player_damaged_id} SE MATOU PQ A TIFA REVELOU QUE DA >[/color]"

        await send_chat_message_to_all(chat_text)

    await send_player_updated(buffer, player)
    
    if(player_damager_id != 123):
        await send_player_updated(buffer, players[player_damager_id])
   
    print(chat_text)

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

    chat_text = "["+str(player.id)+"] "

    chat_text += buffer.read_string()
    print(chat_text)

    buffer.clear()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet_to_all(buffer)

async def _handle_ping(buffer, player):
    print("===PING===")

    time_stamp = buffer.read_u64()  # Lê o PING enviado pelo cliente

    buffer.clear()
    buffer.write_u8(Network.PONG)
    buffer.write_u64(time_stamp)

    await send_packet(buffer, player)


async def send_chat_message_to_all(chat_text):
    buffer = MyBuffer()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet_to_all(buffer) 


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