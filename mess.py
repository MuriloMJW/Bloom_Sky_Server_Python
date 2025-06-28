async def new_handle_request_player_move(buffer, player):
    print("===NEW REQUEST PLAYER MOVE===")
    
    # Lê a posição do player
    new_x = buffer.read_u16()
    new_y = buffer.read_u16()
    
    # Atualiza a posição do player
    player.x = new_x
    player.y = new_y
    
    print(str(player))
    
    # Envia o pacote de movimento para o próprio Player
    buffer.clear()
    
    """     # ====         BITMASK          === #
    BIT_X           = 1 << 0 # 0000 0001
    BIT_Y           = 1 << 1 # 0000 0010
    BIT_IS_ALIVE    = 1 << 2 # 0000 0100
    BIT_HP          = 1 << 3 # 0000 1000
    BIT_TEAM_ID     = 1 << 4 # 0001 0000
    BIT_TEAM_NAME   = 1 << 5 # 0010 0000 """

    mask = 0
    buffer.clear()
    if 'x' in player._changed_stats:
        mask = mask | BIT_X
        player._changed_stats.remove('x')
        buffer.write_u16(player.x)
    if 'y' in player._changed_stats:
        mask = mask | BIT_Y
        player._changed_stats.remove('y')
        buffer.write_u16(player.y)
    if 'is_alive' in player._changed_stats:
        mask = mask | BIT_IS_ALIVE
        player._changed_stats.remove('is_alive')
        buffer.write_u8(player.is_alive)
    if 'hp' in player._changed_stats:
        mask = mask | BIT_HP
        player._changed_stats.remove('hp')
        buffer.write_u8(player.hp)
    if 'team_id' in player._changed_stats:
        mask = mask | BIT_TEAM_ID
        player._changed_stats.remove('team_id')
        buffer.write_u8(player.team_id)
    if 'team' in player._changed_stats:
        mask = mask | BIT_TEAM_NAME
        player._changed_stats.remove('team')
        buffer.write_string(player.team)
    
    player._changed_stats.clear()
    buffer.write_u8(mask)
        