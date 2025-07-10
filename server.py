import asyncio
import websockets
import traceback
from buffer import MyBuffer
from player import Player, player_bitmask_layout
from bullet import Bullet
from network import Network
from enum import IntEnum, auto
import aioconsole
import time
import pygame
import random

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
pending_connections = {}
players = {}
new_id = 0

SKY_COLOR = (99, 255, 255)
BLOOM_COLOR = (255, 102, 250)

bullets = []
friendly_fire_enabled = False

CONNECTION_LOCK = asyncio.Lock()
DISCONNECTION_LOCK = asyncio.Lock()
TEST_LOCK = asyncio.Lock()

# --- Constantes do loop do jogo no servidor --- #
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
TICK_RATE = 60 # 20 atualizações por segundo
DELTA = 1.0/TICK_RATE # O tempo fixo de cada tick



async def game_loop():
    
    
    
    pygame.init()
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    font = pygame.font.Font(None, 36)
    

    
    # É melhor usar o relógio do próprio event loop do asyncio para consistência
    loop = asyncio.get_event_loop()
    # Define a hora exata em que o próximo tick deve acontecer
    next_tick_time = loop.time()
    
    # Variáveis para depuração
    ticks_this_second = 0
    second_timer = loop.time()
    fps = 0
    
    match_start_time = loop.time()
    match_duration = 60*3
    
    sent_2_min_warning = False
    sent_1_min_warning = False
    sent_30_sec_warning = False
    sent_10_sec_warning = False
    
    # Loop do jogo
    while True:
        
        # ===== MAIN LOOP DO JOGO ====== #
        ticks_this_second += 1
        
        # Preenche a tela com tudo preto
        window.fill((0, 0, 0))
        
        # Eventos do pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
                asyncio.get_event_loop().stop()
                

        # Desenha os players
        for player in players.values():
                if(player.is_alive):
                    color = (99, 255, 255) if player.team_id == 0 else (255, 102, 250)
                    player_rect = pygame.Rect(player.collision_box_x, player.collision_box_y, player.width, player.height)
                    pygame.draw.rect(window, color, player_rect)
        
        # Desenha os tiros
        for bullet in list(bullets):
            
            bullet.move(DELTA)
            
            color = (255, 0, 0)
            bullet_rect = pygame.Rect(bullet.collision_box_x, bullet.collision_box_y, bullet.width, 30)
           
            pygame.draw.rect(window, color, bullet_rect)
            
            # Remover a bullet ao sair da tela
            if bullet.x < 0 or bullet.x > WINDOW_WIDTH or bullet.y < 0 or bullet.y > WINDOW_HEIGHT:
                bullets.remove(bullet)
                continue
                      
        # Checa as colisões de bullet com player
        for player in players.values():
            if player.is_alive:
                for bullet in list(bullets):
                    if player.collided_with_bullet(bullet):
                        bullets.remove(bullet)
                        await handle_request_player_damage(player.id, bullet.shooter_id, 20)
        
        
        # Checa as colisões de bullet com bullet
        for bullet in list(bullets):
            for bullet2 in list(bullets):
                if bullet.collided_with_bullet(bullet2) and bullet in bullets and bullet2 in bullets:
                    bullets.remove(bullet)
                    bullets.remove(bullet2)
                        
        # Checa se já pode respawnar o player
        for player in players.values():
            if player.is_alive == False:
                if time.time() >= player.death_time + player.respawn_time:
                    await respawn_id(player.id)

            
        match_end_time = match_start_time + match_duration
            
        

        # --- Dentro do seu loop principal ---

        # Lógica para 2 minutos
        if(loop.time() >= match_end_time - 120 and not sent_2_min_warning):
            await send_chat_message_to_all("[color=yellow]Faltam 2 minutos para o fim da partida![/color]")
            sent_2_min_warning = True

        # Lógica para 1 minuto
        elif(loop.time() >= match_end_time - 60 and not sent_1_min_warning):
            await send_chat_message_to_all("[color=yellow]Falta 1 minuto para o fim da partida![/color]")
            sent_1_min_warning = True

        # Lógica para 30 segundos
        elif(loop.time() >= match_end_time - 30 and not sent_30_sec_warning):
            await send_chat_message_to_all("[color=yellow]Faltam 30 segundos para o fim da partida![/color]")
            sent_30_sec_warning = True

        # Lógica para 10 segundos
        elif(loop.time() >= match_end_time - 10 and not sent_10_sec_warning):
            await send_chat_message_to_all("[color=yellow]Faltam 10 segundos para o fim da partida![/color]")
            sent_10_sec_warning = True  
        
        # MATCH
        if(loop.time() >= match_start_time + match_duration):
            
            # Ordena os jogadores por total_kills
            
            if len(players) > 0:
            
                players_ranked = sorted(players.values(), key=lambda p: p.total_kills, reverse=True)
                player_winner = players_ranked[0]
                
                popup_text = str(player_winner.id)+ " "+ player_winner.username+ " IS THE BEST!"
                
                for player in list(players.values()):
                    if player in players.values():
                        player.total_kills = 0
                        player.total_deaths = 0

                    
                await send_ranking_updated()
                await send_popup_message(popup_text)
                
                
                sent_2_min_warning = False
                sent_1_min_warning = False
                sent_30_sec_warning = False
                sent_10_sec_warning = False
                await send_chat_message_to_all("[color=yellow]Iniciando nova partida de 3 minutos![/color]")
                match_start_time = loop.time()
            
            
            
                
        
        


        
        # Calcula os ticks por segundo
        if loop.time() - second_timer >= 1.0:
            #print(f"Ticks no último segundo: {ticks_this_second}")
            fps = ticks_this_second
            ticks_this_second = 0
            second_timer = loop.time()
            
            
        # Exibe informações na tela do servidor
        texto_surface = font.render(f"Players: {len(players)} Bullets: {len(bullets)} FPS: {fps} ", True, (255, 255, 255))
        window.blit(texto_surface, (10, 10)) 
            
        # Atualiza a tela do Pygame (vira página)
        pygame.display.flip() 

        # Calcula a hora exata em que o PRÓXIMO tick deveria acontecer,
        # somando o delta ao horário agendado anterior.
        next_tick_time += DELTA

        # Calcula quanto tempo precisamos "dormir" para chegar até essa hora agendada.
        sleep_duration = next_tick_time - loop.time()
        #print(f'{next_tick_time} {loop.time()} {sleep_duration}')
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)


'''
next     loop.time     sleep
 0
 0.16     0.10         0.16 - 0.10 = 0.06
 0.32     0.90         0.32 - 0.90 = -0.58 (Não dorme)
 0.48     0.91         0.48 - 0.91 = -0.43 (Não dorme)
 0.64     0.92         0.64 - 0.92 = -0.28 (Não dorme)
 0.80     0.93         0.80 - 0.93 = -0.13 (Não dorme)
 0.96     0.94         0.96 - 0.94 = 0.02 
 1.12     0.99         1.12 - 0.99 = 0.17
 '''


# ----- [ MÉTODOS DE TRATAMENTO DE PACKETS ] ----- #

async def send_packet(packet : MyBuffer, player : Player):
    connection_state = type(player.websocket.state)

    if player.websocket.state != connection_state.OPEN:
        print(f"==FAILED TO SEND PACKET TO {player.id} STATE: {player.websocket.state.name}===")
        await disconnect_player(player)
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
    for other_player in list(players.values()):
        await send_packet(packet, other_player)

async def send_packet_to_all_except(packet, player_except):
    for other_player in list(players.values()):
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
            await damage_id(player.id, 20)

        case Network.REQUEST_PLAYER_RESPAWN:
            #await handle_request_player_respawn(buffer, player)
            pass

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
    #print("===SENDING PLAYER UPDATED TO ALL===")

    #print(str(player))


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
    #print("===REQUEST PLAYER MOVE===")

    # Lê a posição do player
    new_x = buffer.read_float()
    new_y = buffer.read_float()
    # Se clicou fora da area de jogo

    # Atualiza a posição do player
    new_x = player.x + new_x * player.speed * 1.0/60.0
    new_y = player.y + new_y * player.speed * 1.0/60.0

    if new_x < 0 or new_x > WINDOW_WIDTH or new_y < 0 or new_y > WINDOW_HEIGHT or new_y > 500:
        return
    
    player.x = new_x
    player.y = new_y
    
    if(player.y > 500):
        player.y = 500


    await send_player_updated(player)
    

async def handle_request_player_shoot(buffer, player):
    #print("===REQUEST PLAYER SHOOT===")
    
    
    bullet = player.shoot()
    
    if not bullet:
        return
    
    bullets.append(bullet)
    
    
    buffer.clear()
    buffer.write_u8(Network.PLAYER_SHOOT)
    buffer.write_u8(player.id)
    buffer.write_u16(bullet.speed)
    buffer.write_u16(bullet.rotation)



    await send_packet_to_all(buffer)

async def handle_request_player_damage(player_damaged_id, player_damager_id, damage):
    #print("===REQUEST PLAYER DAMAGE===")



    if (player_damaged_id != player_damager_id                                   # Se quem causou dano foi outro player E
    and players[player_damaged_id].team_id == players[player_damager_id].team_id # Não são do mesmo time E
    and not friendly_fire_enabled):                                              # O friendly fire está desativado
        return                                                                   # Não faz nada  

    if (players[player_damaged_id].is_alive == False):
        return

    await damage_id(player_damaged_id, damage)  # Aplica o dano ao player

    chat_text = ''


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
    
    
    player.power_up_sonic()
    
    '''
    if player.has_sonic_power_up:
        player.reset_attributes()
    else:
        player.power_up_sonic()
    '''

    await send_player_updated(player)


async def _handle_chat_message(buffer, player):
    print("===CHAT MESSAGE===")

    message_received = buffer.read_string()

    if message_received[0] == "/":
        await commands(message_received, player)
        return

    username_text = ""
    
    if player.team == "SKY":
        #Formatação                        # R                #G                #B         [1]           [usuario]
        username_text = f"[color=#{SKY_COLOR[0]:02x}{SKY_COLOR[1]:02x}{SKY_COLOR[2]:02x}][{player.id}][{player.username}][/color] "
    else:
        username_text = f"[color=#{BLOOM_COLOR[0]:02x}{BLOOM_COLOR[1]:02x}{BLOOM_COLOR[2]:02x}][{player.id}][{player.username}][/color] "
    
    
    

    chat_text = username_text
    chat_text += message_received
    
    print(chat_text)

    buffer.clear()
    buffer.write_u8(Network.CHAT_RECEIVED)
    buffer.write_string(chat_text)

    await send_packet_to_all(buffer)

    # Easter Egg
    if message_received == "RAT ATTACK":
        await rat_attack(player)

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

async def send_popup_message(popup_text):
    buffer = MyBuffer()
    buffer.write_u8(Network.POPUP_RECEIVED)
    buffer.write_string(popup_text)

    await send_packet_to_all(buffer) 


async def send_ranking_updated():
    #print("===SENDING RANKING UPDATED===")

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
    players[player_to_kill_id].die()

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

async def change_speed_id(player_to_change_speed_id, new_speed):
    players[player_to_change_speed_id].speed = new_speed
    
    await send_player_updated(players[player_to_change_speed_id])

async def rat_attack(player):
    print("===RAT ATTACK===")
    await kill_all_except(player.id)

    buffer_rat = MyBuffer()
    buffer_rat.clear()
    buffer_rat.write_u8(Network.RAT_ATTACKED)
    await send_packet_to_all(buffer_rat)
    
    message = ""
    
    for i in range(100):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        message += f"[color={hex_color}]RAT ATTACK[/color] "
        
    message += f"\nPLAYER {player.id} MANDOU OS RATO MATAR VCS TUDO"

    await send_chat_message_to_all(message) # Envia mensagem de chat para todos os players



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
    elif command_name == "speedid" or command_name == "sid":
            await command_speed_id(args, player)
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

async def command_speed_id(args, player):
    args_needed = 2

    player_to_change_speed_id = None
    new_speed = None
    
    if(len(args) != args_needed):
        await send_chat_message_to_player("Argumentos inválidos. Use: /speedid [player_id] [speed]", player)
        return
    
    try:
        target_id = int(args[0])
        new_speed = float(args[1])
    except ValueError:
        await send_chat_message_to_player("Argumentos inválidos. ID deve ser um número e speed um número.", player)
        return

    if target_id not in players:
        await send_chat_message_to_player("ID de jogador inválido.", player)
        return

    #if new_speed <= 0:
    #    await send_chat_message_to_player("A velocidade deve ser um valor positivo.", player)
    #    return

    await change_speed_id(players[target_id].id, new_speed)
    #await send_chat_message_to_all(f"A velocidade do Player {target_id} foi alterada para {new_speed}.")


async def disconnect_player(player):
    if player is None or player.id not in players:
        return
    
    async with DISCONNECTION_LOCK:
        
        if player.id in players:
            print(f"Desconectando Player {player.id}")
            del players[player.id]
            
            # Avisa aos outros jogadores que este saiu
            buffer_disconnect = MyBuffer()
            buffer_disconnect.write_u8(Network.OTHER_PLAYER_DISCONNECTED)
            buffer_disconnect.write_u8(player.id)
            await send_packet_to_all(buffer_disconnect)
            print(f"Player {player.id} removido. Total de players: {len(players)}")


#Couroutine executada com a conexão recebida
async def handler(websocket):
    print(f"Nova conexão de {websocket.remote_address}. Aguardando pedido de autenticação...")
    username = None
    player = None
    try:
        async for packet in websocket:
            
            buffer = MyBuffer(packet)
    
            msgid = buffer.read_u8()
            
            # ESTADO 1: ESPERANDO AUTENTICAÇÃO
            if username is None:
            
                if msgid == Network.REQUEST_AUTH:
                    username = buffer.read_string()
                    # Teste de exemplo de falha na autenticação
                    if username == "admin":
                        buffer.clear()
                        buffer.write_u8(Network.AUTH_FAIL)
                        username = None
                        await websocket.send(buffer.get_data_array())
                    else: # Sucesso na autenticação
                        buffer.clear()
                        buffer.write_u8(Network.AUTH_SUCCESS)
                        await websocket.send(buffer.get_data_array())
                        pending_connections[websocket] = username
                else:
                    # Protocolo violado: pacote inesperado antes da autenticação.
                    print("Protocolo violado: pacote inesperado antes da autenticação: ", msgid)
                    await websocket.close(code=1003, reason="Authentication required")
                    break
            
            # ESTADO 2: AUTENTICADO, ESPERANDO ENTRAR NO JOGO
            elif player is None:  
                if msgid == Network.REQUEST_CONNECTS:
                    async with CONNECTION_LOCK:
                        global new_id
                        # Cria o objeto player e o associa ao websocket e a um novo ID
                        player = Player(websocket, new_id, username)
                        players[new_id] = player  # Adiciona ao dicionário global
                        print(f"Lock adquirido. Criando Player com ID: {new_id}")
                        new_id += 1
                    
                    del pending_connections[websocket]
                    
                    await handle_request_connect(player)
                else:
                    # Protocolo violado: o cliente está autenticado, mas enviou um
                    # pacote inválido (ex: movimento) antes de entrar no jogo.
                    print("Protocolo violado: o cliente está autenticado, mas enviou um pacote inválido: ", msgid)
                    await websocket.close(code=1003, reason="Request connect required")
                    break
                    
            # ESTADO 3: NO JOGO
            else:
                # Processa os pacotes normais do jogo (movimento, tiro, etc.)
                await received_packets(packet, player)
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Conexão com {websocket.remote_address} fechada.", e)
        await disconnect_player(player)
                         
    except Exception as e:
        # Se a conexão cair em qualquer ponto do processo...
        print(f"Conexão com {websocket.remote_address} fechada.", e)
        await disconnect_player(player)
        
    finally:
        print(f"Handler para a conexão de {websocket.remote_address} foi finalizado.")
        if websocket in pending_connections:
            del pending_connections[websocket]


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