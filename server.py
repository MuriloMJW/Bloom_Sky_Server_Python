import asyncio
import websockets
import buffer
import traceback
from buffer import MyBuffer
from enum import IntEnum

# Ip onde o servidor ouve

# Local host
server_ip = "0.0.0.0"
# Hamachi
#server_ip = "25.3.218.182"

debug_send_packet = True
debug_received_packet = True

#server_port = 9913
server_port = 8080

# Lista de conexões
sockets = []
players = {}

id = 0

class network(IntEnum):
    player_establish = 0
    player_connect = 1
    player_joined = 2
    player_disconnect = 3
    player_move = 4
    player_chat = 5


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



async def received_packets(packet, id):

    buffer = MyBuffer(packet)

    if(debug_received_packet):
        print("==RECEIVED PACKET==")
        print(buffer.get_data_array())
        print(list(buffer.get_data_array()))
    
    
    msgid = buffer.read_u8()

    match msgid:

        case network.player_establish:
            print("===Player Establish===")
            
            
            
            # Altera no dictionary
            players[id].set_x(400)
            players[id].set_y(400)

            player = players[id]
            
            # 1) Manda o Player Connect e sua posição para o novo Player
            buffer.clear()
            buffer.write_u8(network.player_connect)
            buffer.write_u16(player.x)
            buffer.write_u16(player.y)
            #buffer.write_string(str(player.id))
            await send_packet(player, buffer)
            
            # Avisa TODOS que um novo Player conectou e sua posição
            buffer.clear()
            buffer.write_u8(network.player_joined)
            buffer.write_u16(player.x)
            buffer.write_u16(player.y)
            buffer.write_u8(player.id)
            await send_packet_to_all_except(buffer, player)
            
            # Avisa ao novo Player que conectou a posição de TODOS
            
            for other_player in players.values():
                if other_player.id != player.id: # Não avisa a si mesmo

                    buffer.clear()
                    buffer.write_u8(network.player_joined)
                    buffer.write_u16(other_player.x)
                    buffer.write_u16(other_player.y)
                    buffer.write_u8(other_player.id)

                    await send_packet(player, buffer)


        case network.player_move:
            print("===Player Move===")

            move_x = buffer.read_u16()
            move_y = buffer.read_u16()

            player = players[id]

            buffer.clear()
            buffer.write_u8(network.player_move)
            buffer.write_u16(move_x)
            buffer.write_u16(move_y)
            buffer.write_u8(player.id)

            await send_packet(player, buffer)

            # Após o pacote enviado, atualiza no dict a posição
            players[id].set_x(move_x)
            players[id].set_y(move_y)

            await send_packet_to_all_except(buffer, player)

            #Colocar aqui o X e Y do player
        
        case network.player_chat:
            print("===Player Chat===")


            player = players[id]

            chat_text = "["+str(player.id)+"] "

            chat_text += buffer.read_string()
            print(chat_text)

            buffer.clear()
            buffer.write_u8(network.player_chat)
            buffer.write_string(chat_text)
            
            await send_packet_to_all(buffer)
                    


async def send_packet(player, packet : MyBuffer):
    if(debug_send_packet):
        print("==SENDING PACKET==")
        print(packet.get_data_array())
        print(list(packet.get_data_array()))
    
    await player.websocket.send(packet.get_data_array())
    
async def send_packet_to_all(packet : MyBuffer):
    # Avisa a todos os jogadores o chat
    for other_player in players.values():
        await send_packet(other_player, packet)
        
async def send_packet_to_all_except(packet, player_except):
    for other_player in players.values():
        if(other_player.id != player_except.id):
            await send_packet(other_player, packet)
    

#Couroutine executada com a conexão recebida
async def handler(websocket):
    global id

    print("Connection received: ", websocket.remote_address)

    sockets.append(websocket)


    player = Player(websocket, id)

    # Acrescenta o player no dictionary. id: player
    players[id] = player

    id += 1
    
    buffer = MyBuffer()
    buffer.write_u8(network.player_establish)
    buffer.write_u8(player.id)
    
    await send_packet(player, buffer)

    try:
        while True: #Fica ouvindo as mensagens recebidas de cada websocket para sempre, mantendo a conexão ligada
            packet = await websocket.recv() #
            #print(packet)
            #print(*packet)

            # Received Packets com o buffer recebido e o Id de quem enviou
            await received_packets(packet, player.id)

    except websockets.exceptions.ConnectionClosed as e:
            print("Erro: Jogador desconectado. ", e)
            player_removed_id = player.id
            del players[player_removed_id]

            # Avisar aos outros jogadores a desconexão
            for other_player in players.values():

                    buffer_ = bytearray()
                    myBufferWrite = MyBuffer(buffer_)

                    myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_disconnect)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, player_removed_id)

                    #print("Todos sobre quem entrou: Avisando o player ", p.id, " sobre o ", player.id)
                    await other_player.websocket.send(buffer_)


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