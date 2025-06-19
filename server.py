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

    msgid = buffer.read_u8()

    match msgid:

        case network.player_establish:
            print("===Player Establish===")
            
            buffer.clear()
            
            # Altera no dictionary
            players[id].set_x(400)
            players[id].set_y(400)

            player = players[id]
            
            buffer.write_u8(network.player_connect)
            buffer.write_u16(player.x)
            buffer.write_u16(player.y)
            buffer.write_string(str(player.id))

            await send_packet(player, buffer)
            '''

            # Avisar a quem se conectou (new_player) a posição dos outros os jogadores
            for other_player in players.values():
                if other_player.id != player.id: # Não avisa a si mesmo

                    buffer_ = bytearray()
                    myBufferWrite = MyBuffer(buffer_)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_joined)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, other_player.id)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, other_player.x)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, other_player.y)
                    myBufferWrite.buffer_write(buffer.BUFFER_STRING, str(other_player.id))

                    #print("Quem entrou sobre todos: Avisando o player ", player.id, " sobre o ", p.id)

                    await send_packet(player, buffer_)

            # Avisar aos outros jogadores a posição de quem se conectou (new_player)
            for other_player in players.values():
                if other_player.id != player.id: # Não avisa a si mesmo

                    buffer_ = bytearray()
                    myBufferWrite = MyBuffer(buffer_)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_joined)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, player.id)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, player.x)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, player.y)
                    myBufferWrite.buffer_write(buffer.BUFFER_STRING, str(player.id))

                    print("Todos sobre quem entrou: Avisando o player ", other_player.id, " : ", player.id, " conectou-se")

                    await send_packet(other_player, buffer_)

            '''
            '''
        case network.player_move:
            print("===Player Move===")

            buffer_ = bytearray()
            myBufferWrite = MyBuffer(buffer_)

            move_x = myBufferRead.buffer_read(buffer.BUFFER_U16)
            move_y = myBufferRead.buffer_read(buffer.BUFFER_U16)


            player = players[id]

            myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_move)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, move_x)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, move_y)

            await send_packet(player, buffer_)

            # Após o pacote enviado, atualiza no dict a posição
            players[id].set_x(move_x)
            players[id].set_y(move_y)

            # Avisar aos outros jogadores a sua nova posição
            for other_player in players.values():
                if other_player.id != player.id: # Não avisa a si mesmo

                    buffer_ = bytearray()
                    myBufferWrite = MyBuffer(buffer_)

                    myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_move)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, player.id)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, move_x)
                    myBufferWrite.buffer_write(buffer.BUFFER_U16, move_y)

                    #print("Todos sobre quem entrou: Avisando o player ", p.id, " sobre o ", player.id)
                    await send_packet(other_player, buffer_)

            #Colocar aqui o X e Y do player
            '''    
        case network.player_chat:
            print("===Player Chat===")


            player = players[id]

            chat_text = "["+str(player.id)+"] "

            chat_text += buffer.read_string()
            print(chat_text)

            # Avisa a todos os jogadores o chat
            for other_player in players.values():

                buffer.clear()

                buffer.write_u8(network.player_chat)
                buffer.write_string(chat_text)
                
                await send_packet(other_player, buffer)
                    


async def send_packet(player, packet : MyBuffer):
    await player.websocket.send(packet.get_data_array())
    

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
            print(packet)
            print(*packet)

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

    print("Listening...")
    # Websockets.serve, internamente chama um await handler(websocket) 
    # e passa magicamente o socket para ele
    async with websockets.serve(handler, server_ip, server_port): 
        # Roda pra sempre, quando recebe uma conexão, chama o evento handler(websocket)
        await asyncio.Future() 


asyncio.run(main())


#async for msg in ws:
#        print("Recebido do cliente:", msg)