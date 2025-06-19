import asyncio
import ssl
import tempfile
import os
import datetime
import ipaddress
import logging
import websockets
import buffer
from buffer import MyBuffer
from enum import IntEnum

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.oid import NameOID

# Ip onde o servidor ouve
server_ip = "25.3.218.182"
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





async def received_packets(buff, id):

    myBufferRead = MyBuffer(buff)

    msgid = myBufferRead.buffer_read(buffer.BUFFER_U8)

    match msgid:

        case network.player_establish:
            print("===Player Establish===")
            buffer_ = bytearray()
            myBufferWrite = MyBuffer(buffer_)

            # Altera no dictionary
            players[id].set_x(300)
            players[id].set_y(300)

            player = players[id]

            myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_connect)
            myBufferWrite.buffer_write(buffer.BUFFER_U8, player.id)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, player.x)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, player.y)
            myBufferWrite.buffer_write(buffer.BUFFER_STRING, str(player.id))

            await player.websocket.send(buffer_)

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

                    await player.websocket.send(buffer_)

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
                    await other_player.websocket.send(buffer_)


        case network.player_move:
            print("===Player Move===")

            buffer_ = bytearray()
            myBufferWrite = MyBuffer(buffer_)

            move_x = myBufferRead.buffer_read(buffer.BUFFER_U16)
            move_y = myBufferRead.buffer_read(buffer.BUFFER_U16)


            player = players[id]

            myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_move)
            myBufferWrite.buffer_write(buffer.BUFFER_U8, player.id)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, move_x)
            myBufferWrite.buffer_write(buffer.BUFFER_U16, move_y)

            await player.websocket.send(buffer_)

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
                    await other_player.websocket.send(buffer_)

            #Colocar aqui o X e Y do player

        case network.player_chat:
            print("===Player Chat===")

            buffer_ = bytearray()
            myBufferWrite = MyBuffer(buffer_)

            player = players[id]

            chat_text = "["+str(player.id)+"] "

            try:
                
                chat_text += myBufferRead.buffer_read(buffer.BUFFER_STRING)
                print(chat_text)

                # Avisa a todos os jogadores o chat
                for other_player in players.values():

                    buffer_ = bytearray()
                    myBufferWrite = MyBuffer(buffer_)

                    myBufferWrite.buffer_write(buffer.BUFFER_U8, network.player_chat)
                    myBufferWrite.buffer_write(buffer.BUFFER_U8, player.id)
                    myBufferWrite.buffer_write(buffer.BUFFER_STRING, chat_text)
                    print("ENVIANDO: ", buffer_)
                    await other_player.websocket.send(buffer_)
            except:
                print("Erro provavel de non ascii")

#Couroutine executada com a conexão recebida
async def handler(websocket):
    global id

    print("Connection received: ", websocket.remote_address)

    sockets.append(websocket)


    player = Player(websocket, id)

    # Acrescenta o player no dictionary. id: player
    players[id] = player

    id += 1

    send_buffer = bytearray()
    myBuffer_2 = MyBuffer(send_buffer)


    #myBuffer_2.buffer_write(buffer.BUFFER_U8, network.player_establish)
    #myBuffer_2.buffer_write(buffer.BUFFER_U8, player.id)


    await websocket.send(send_buffer)

    try:
        while True: #Fica ouvindo as mensagens recebidas de cada websocket para sempre, mantendo a conexão ligada
            _buffer = await websocket.recv() #
            print(_buffer)
            print(*_buffer)

            # Received Packets com o buffer recebido e o Id de quem enviou
            await received_packets(_buffer, player.id)

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

# -----------------------------------------------------------------------------
# Gera ou reutiliza um certificado autoassinado com SAN para IP ou DNS
# -----------------------------------------------------------------------------
def get_cert_and_key(common_name: str):
    # Gera chave privada RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Define subject e issuer
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.utcnow()

    # Constrói certificado
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(issuer)
    cert_builder = cert_builder.not_valid_before(now - datetime.timedelta(days=1))
    cert_builder = cert_builder.not_valid_after(now + datetime.timedelta(days=365))
    cert_builder = cert_builder.serial_number(x509.random_serial_number())
    cert_builder = cert_builder.public_key(private_key.public_key())

    # Adiciona SAN (IP ou DNS)
    try:
        ip = ipaddress.ip_address(common_name)
        san = x509.SubjectAlternativeName([x509.IPAddress(ip)])
    except ValueError:
        san = x509.SubjectAlternativeName([x509.DNSName(common_name)])
    cert_builder = cert_builder.add_extension(san, critical=False)

    # Assina o certificado
    certificate = cert_builder.sign(
        private_key=private_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )

    # Persiste em arquivos temporários
    temp_dir = tempfile.mkdtemp(prefix="wss_cert_")
    cert_path = os.path.join(temp_dir, "server.crt")
    key_path = os.path.join(temp_dir, "server.key")

    with open(cert_path, "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    logging.info(f"Certificado gerado em {cert_path}, chave em {key_path}")
    return cert_path, key_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Escolha de interface
    opcao = input("1 - Localhost\n2 - Hamachi\nEscolha: ")
    if opcao.strip() == "1":
        bind_host = "0.0.0.0"
        common_name = "localhost"
    else:
        bind_host = "0.0.0.0"
        common_name = "25.3.218.182"
    server_port = 8080

    # Gera e carrega contexto SSL
    cert_file, key_file = get_cert_and_key(common_name)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    logging.info(f"Iniciando WSS em wss://{common_name}:{server_port}/ (bind {bind_host})")

    async def main():
        # Bind em todas as interfaces, mas URL pública é common_name
        async with websockets.serve(handler, bind_host, server_port, ssl=ssl_context):
            await asyncio.Future()  # roda indefinidamente

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Servidor WSS interrompido pelo usuário.")
