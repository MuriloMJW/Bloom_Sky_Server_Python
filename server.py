import asyncio
import websockets
import traceback
from buffer import MyBuffer
from enum import IntEnum, auto

# Ip onde o servidor ouve

# Local host
server_ip = "0.0.0.0"
# Hamachi
#server_ip = "25.3.218.182"

debug_send_packet = True
debug_received_packet = True

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
    
    CHAT_MESSAGE = 100

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
    
    CHAT_RECEIVED = 200
    
    
    
SPAWN_POSITIONS = {
    "SKY": {"x": 100, "y": 100},
    "BLOOM": {"x": 100, "y": 500}
}

class Player:

    def __init__(self, websocket, id):
        
        self._websocket = websocket
        self._ip = websocket.remote_address
        
        self._id = id
        
        self._team = "SKY" if self._id % 2 == 0 else "BLOOM"
        
        self._x = SPAWN_POSITIONS[self.team]["x"]
        self._y = SPAWN_POSITIONS[self.team]["y"]
        
        self._is_alive = True
        
        self._hp = 100  # HP inicial do jogador
    
    # --- Getters --- #
    
    @property
    def websocket(self):    
        return self._websocket
    
    @property
    def ip(self):
        return self._ip
        
    @property
    def id(self) -> int:
        return self._id
        
    @property
    def team(self):
        return self._team
    
    @property
    def x(self):
        return self._x
    
    @property
    def y(self):
        return self._y
    
    @property
    def is_alive(self):
        return self._is_alive
    
    @property
    def hp(self):
        return self._hp
    
    # --- Setters --- #
    
    @x.setter
    def x(self, new_x):
        self._x = new_x
        
    @y.setter
    def y(self, new_y):
        self._y = new_y  
        
    def __str__(self):
        status = "Vivo" if self._is_alive else "Morto"
        return (
            f"Jogador {self._id} | "
            f"Time: {self._team} | "
            f"Posição: (x={self._x}, y={self._y}) | "
            f"Status: {status}"
        )
    
    # --- Métodos --- #
    def take_damage(self, damage):
        if self._is_alive:
            self._hp -= damage
            if self._hp <= 0:
                self.kill()
    
    def kill(self):
        self._hp = 0
        self._is_alive = False
        
    def respawn(self):
        self._hp = 100
        self._is_alive = True
        self._x = SPAWN_POSITIONS[self.team]["x"]
        self._y = SPAWN_POSITIONS[self.team]["y"]
        
       
     
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
        
        case Network.CHAT_MESSAGE:
            await _handle_chat_message(buffer, player)
        
        case _:
            print("UNKNOWN PACKET ID: ", msgid)
            
                    
# ----- [ PEDIDOS DO CLIENT] ----- #

async def handle_request_connect(buffer, player):
    print("===REQUEST CONNECT===")

    print(str(player))
    print(str(players[player.id]))
    
    # 1) Manda o Player Connect e sua posição para o novo Player
    buffer.clear()
    buffer.write_u8(Network.PLAYER_CONNECTED)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.id)
    buffer.write_string(player.team)
    buffer.write_u8(player.is_alive)
    buffer.write_u8(player.hp)
    
    await send_packet(buffer, player)
    
    # Avisa TODOS que um novo Player conectou e sua posição
    buffer.clear()
    buffer.write_u8(Network.OTHER_PLAYER_CONNECTED)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.id)
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
            buffer.write_u16(other_player.x)
            buffer.write_u16(other_player.y)
            buffer.write_u8(other_player.id)
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
    
    # Envia o pacote de movimento para o próprio Player
    buffer.clear()
    buffer.write_u8(Network.PLAYER_MOVED)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    
    await send_packet(buffer, player)
    
    # Envia o pacote de movimento para todos os outros Players
    buffer.clear()
    buffer.write_u8(Network.OTHER_PLAYER_MOVED)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.id)
    
    await send_packet_to_all_except(buffer, player)  

async def handle_request_player_shoot(buffer, player):
    print("===REQUEST PLAYER SHOOT===")

    # Avisa a si mesmo que atirou
    buffer.clear()
    buffer.write_u8(Network.PLAYER_SHOOT)
    await send_packet(buffer, player)
    
    # Avisa todos (exceto eu mesmo) que atirei
    buffer.clear()
    buffer.write_u8(Network.OTHER_PLAYER_SHOOT)
    buffer.write_u8(player.id)
    await send_packet_to_all_except(buffer, player)

async def handle_request_player_damage(buffer, player):
    print("===REQUEST PLAYER DAMAGE===")
    player_damaged_id = buffer.read_u8()
    player_damager_id = buffer.read_u8()
    damage = buffer.read_u8()
    
    player.take_damage(damage) # Aplica o dano ao player

    
    buffer.clear()
    
    if player.is_alive:
        buffer.write_u8(Network.PLAYER_DAMAGED)
        buffer.write_u8(player_damaged_id)
        buffer.write_u8(player_damager_id)
        buffer.write_u8(damage)
        await send_packet_to_all(buffer)
    else: # Se o player morreu, avisa que ele foi morto
        buffer.write_u8(Network.PLAYER_KILLED)
        buffer.write_u8(player_damaged_id)
        buffer.write_u8(player_damager_id)
        await send_packet_to_all(buffer)
        
        chat_text = f"[color=red]< PLAYER {player_damager_id} MATOU O PLAYER {player_damaged_id} >[/color]"
        if player_damager_id == 123:
            chat_text = f"[color=red]< PLAYER {player_damaged_id} SE MATOU PQ A TIFA REVELOU QUE DA >[/color]"
        await send_chat_message_to_all(chat_text)
        print(chat_text)

async def handle_request_player_respawn(buffer, player):
    print("===REQUEST PLAYER RESPAWN===")
     
    respawned_id = buffer.read_u8()
    
    player.respawn()  # Reseta o player
    
    buffer.clear()
    buffer.write_u8(Network.PLAYER_RESPAWNED)
    buffer.write_u8(respawned_id)
    buffer.write_u16(player.x)
    buffer.write_u16(player.y)
    buffer.write_u8(player.is_alive)
    buffer.write_u8(player.hp)
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

async def main():
    global server_ip
    global server_port

    print(f"Listening on {server_ip}:{server_port}...")
    # Websockets.serve, internamente chama um await handler(websocket) 
    # e passa magicamente o socket para ele
    async with websockets.serve(handler, server_ip, server_port): 
        # Roda pra sempre, quando recebe uma conexão, chama o evento handler(websocket)
        await asyncio.Future() 


asyncio.run(main())


#async for msg in ws:
#        print("Recebido do cliente:", msg)