import asyncio
import websockets
import buffer
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
sockets = []
players = {}

new_id = 0

class Network(IntEnum):
    # Client -> Server
    REQUEST_CONNECT = 0
    
    REQUEST_PLAYER_MOVE = 1
    
    REQUEST_PLAYER_SHOOT = 2
    
    CHAT_MESSAGE = 100

    # Server -> Client
    PLAYER_CONNECTED = 100
    OTHER_PLAYER_CONNECTED = 101
    OTHER_PLAYER_DISCONNECTED = 102
    
    PLAYER_MOVED = 103          
    OTHER_PLAYER_MOVED = 104
    
    PLAYER_SHOOT = 105
    OTHER_PLAYER_SHOOT = 106
    
    CHAT_RECEIVED = 200
    
    


class Player():

    def __init__(self, websocket, id):
        self.websocket = websocket
        self.id = id

    def set_ip(self, ip):
        self.ip = ip

    def set_x(self, x):
        self.x = x

    def set_y(self, y):
        self.y = y

async def send_packet(packet : MyBuffer, player : Player):
    if(debug_send_packet):
        print("==SENDING PACKET==")
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

async def received_packets(packet, id):

    buffer = MyBuffer(packet)

    if(debug_received_packet):
        print("==RECEIVED PACKET==")
        print(buffer.get_data_array())
        print(list(buffer.get_data_array()))
    
    
    msgid = buffer.read_u8()

    match msgid:

        case Network.REQUEST_CONNECT:
            
            
            
            # Altera no dictionary
            players[id].set_x(100)
            players[id].set_y(100)

            player = players[id]
            
            # 1) Manda o Player Connect e sua posição para o novo Player
            buffer.clear()
            buffer.write_u8(Network.PLAYER_CONNECTED)
            buffer.write_u16(player.x)
            buffer.write_u16(player.y)
            buffer.write_u8(player.id)
            #buffer.write_string(str(player.id))
            
            await send_packet(buffer, player)
            
            # Avisa TODOS que um novo Player conectou e sua posição
            buffer.clear()
            buffer.write_u8(Network.OTHER_PLAYER_CONNECTED)
            buffer.write_u16(player.x)
            buffer.write_u16(player.y)
            buffer.write_u8(player.id)
            await send_packet_to_all_except(buffer, player)
            
            # Avisa ao novo Player que conectou a posição de TODOS
            
            for other_player in players.values():
                if other_player.id != player.id: # Não avisa a si mesmo

                    buffer.clear()
                    buffer.write_u8(Network.OTHER_PLAYER_CONNECTED)
                    buffer.write_u16(other_player.x)
                    buffer.write_u16(other_player.y)
                    buffer.write_u8(other_player.id)

                    await send_packet(buffer, player)


        case Network.REQUEST_PLAYER_MOVE:
            print("===REQUEST PLAYER MOVE===")
            player = players[id]
            
            move_x = buffer.read_u16()
            move_y = buffer.read_u16()

            
            # Atualiza no dict a posição
            players[id].set_x(move_x)
            players[id].set_y(move_y)

            buffer.clear()
            buffer.write_u8(Network.PLAYER_MOVED)
            buffer.write_u16(move_x)
            buffer.write_u16(move_y)
            buffer.write_u8(player.id)

            await send_packet(buffer, player)

            

            # Avisa todos (exceto eu mesmo) que me movi
            buffer.clear()
            buffer.write_u8(Network.OTHER_PLAYER_MOVED)
            buffer.write_u16(move_x)
            buffer.write_u16(move_y)
            buffer.write_u8(player.id)
            await send_packet_to_all_except(buffer, player)
        
        case Network.REQUEST_PLAYER_SHOOT:
            print("===REQUEST PLAYER SHOOT===")
            player = players[id]
            
            buffer.clear()
            buffer.write_u8(Network.PLAYER_SHOOT)
            
            await send_packet(buffer, player)
            
            
            # Avisa todos (exceto eu mesmo) que atirei
            buffer.clear()
            buffer.write_u8(Network.OTHER_PLAYER_SHOOT)
            buffer.write_u8(player.id)
            await send_packet_to_all_except(buffer, player)
            
            
            
            
        
        case Network.CHAT_MESSAGE:
            print("===Player Chat===")


            player = players[id]

            chat_text = "["+str(player.id)+"] "

            chat_text += buffer.read_string()
            print(chat_text)

            buffer.clear()
            buffer.write_u8(Network.CHAT_MESSAGE)
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
            await received_packets(packet, player.id)

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