import websockets
from entity import Entity
from bullet import Bullet
import random
import time
# EITA LASKERA
class Player (Entity):
    
    def __init__(self, websocket, id, username):

        # Identidade
        self._websocket = websocket # Conexão
        self._ip = str(self._get_real_ip(websocket))
        self._id = id
        
        self._is_authenticated = False
        self._username = username
        
        # Time
        self._team_id = id % 2
        self._team = "SKY" if self._team_id == 0 else "BLOOM"

        # Entity
        _x = SPAWN_POSITIONS[self.team]["x"]
        _y = SPAWN_POSITIONS[self.team]["y"]
        _width = 64
        _height = 22
        _rotation = 180 if self._team_id == 0 else 0
        
        _speed = 500
        
        super().__init__(_x, _y, _width, _height, _rotation, _speed)

        # Vida
        self._is_alive = True
        self._hp = 100

        # Tiro
        self._shoot_cooldown = 0.3
        self.last_shoot_time = 0

        # K/D
        self._total_kills = 0  # Server only
        self.total_deaths = 0  # Server only
        self._death_time = 0   # Server only
        self._respawn_time = 5 # Server only
          
        # Powerups
        self._has_sonic_power_up = False

        
        # Conjunto para armazenar quais atributos foram alterados
        self._changed_attributes = set()  
        


    # Este método auxiliar é chamado pelo construtor para pegar o ip verdadeiro
    def _get_real_ip(self, websocket) -> str:
        """
        Obtém o endereço de IP real, verificando os cabeçalhos do handshake.
        """
        headers = websocket.request.headers

        forwarded_for = headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        return websocket.remote_address[0]

    # --- Getters & Setters --- #

    # --- Identidade --- #
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
    def is_authenticated(self):
        return self._is_authenticated

    @is_authenticated.setter
    def is_authenticated(self, new_is_authenticated):
        if (new_is_authenticated != self._is_authenticated):
            self._is_authenticated = new_is_authenticated
            
    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, new_username):
        if (new_username != self._username):
            self._username = new_username

    
    # --- Transform --- #

    @Entity.x.setter
    def x(self, new_x):
        if (new_x != self._x):
            self._x = new_x
            self._collision_box_x = self.x - self._width/2
            self._changed_attributes.add("x")

    @Entity.y.setter
    def y(self, new_y):
        if (new_y != self._y):
            self._y = new_y
            self._collision_box_y = self.y - self._height/2
            self._changed_attributes.add("y")
            
    # Enviar para o client ou ta bom assim?
    @Entity.rotation.setter
    def rotation(self, new_rotation):
        if (new_rotation != self._rotation):
            self._rotation = new_rotation
            #self._changed_attributes.add("rotation")

    # --- Speed --- #
    @Entity.speed.setter
    def speed(self, new_speed):
        if (new_speed != self._speed):
            self._speed = new_speed
            self._changed_attributes.add("speed")


    # --- Vida --- #
    @property
    def is_alive(self):
        return self._is_alive

    @is_alive.setter
    def is_alive(self, new_is_alive):
        if (new_is_alive != self._is_alive):
            self._is_alive = new_is_alive
            self._changed_attributes.add("is_alive")

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, new_hp):
        if (new_hp != self._hp):
            self._hp = new_hp
            self._changed_attributes.add("hp")

    # --- Tiro --- #
    @property
    def shoot_cooldown(self):
        return self._shoot_cooldown

    @shoot_cooldown.setter
    def shoot_cooldown(self, new_shoot_cooldown):
        if (new_shoot_cooldown != self._shoot_cooldown):
            self._shoot_cooldown = new_shoot_cooldown
            self._changed_attributes.add("shoot_cooldown")

    # --- Time --- #
    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, new_team_id):
        if (new_team_id != self._team_id):
            self._team_id = new_team_id
            self._changed_attributes.add("team_id")

    @property
    def team(self):
        return self._team

    @team.setter
    def team(self, new_team):
        if (new_team != self._team):
            self._team = new_team
            self._changed_attributes.add("team")

    # --- Total Kills e Total Deaths --- #
    @property
    def total_kills(self):
        return self._total_kills

    @total_kills.setter
    def total_kills(self, new_total_kills):
        if (new_total_kills != self._total_kills):
            self._total_kills = new_total_kills
            self._changed_attributes.add("total_kills")

    @property
    def death_time(self):
        return self._death_time
    
    @ death_time.setter
    def death_time(self, new_death_time):
        if (new_death_time != self._death_time):
            self._death_time = new_death_time
    
    @property
    def respawn_time(self):
        return self._respawn_time

    # --- Power-ups ---#
    @property
    def has_sonic_power_up(self):
        return self._has_sonic_power_up

    @has_sonic_power_up.setter
    def has_sonic_power_up(self, new_has_sonic_power_up):
        if (new_has_sonic_power_up != self._has_sonic_power_up):
            self._has_sonic_power_up = new_has_sonic_power_up
            self._changed_attributes.add("has_sonic_power_up")

            
    # --- String Representation --- #

    def __str__(self):
        status = "Vivo" if self._is_alive else "Morto"
        return (f"Player {self._id} | "
                f"Time: {self._team} | "
                f"Posição: (x={self._x}, y={self._y}) | "
                f"Status: {status}"
                f" | HP: {self._hp} | "
                f"Kills: {self._total_kills} | "
                f"Deaths: {self.total_deaths} | "
                f"IP: {self._ip}"
                f" | Team ID: {self._team_id}"
                f" | Changed Stats: {self._changed_attributes}"
                f" | Speed: {self._speed}"
                f" | Shoot Cooldown: {self._shoot_cooldown}")

    # --- Métodos do Player --- #

    def authenticate(self, username):
        self.is_authenticated = True
        self.username = username
    
    def take_damage(self, damage):
        if self.is_alive:
            self.hp -= damage
            if self.hp <= 0:
                self.die()

    def die(self):
        self.hp = 0
        self.is_alive = False
        self.total_deaths += 1
        self.death_time = time.time()
        self.reset_attributes()

    def respawn(self):
        self.hp = 100
        self.is_alive = True
        self.x = SPAWN_POSITIONS[self.team]["x"]
        self.y = SPAWN_POSITIONS[self.team]["y"]

    def reset_attributes(self):
        self.rotation = 180 if self._team_id == 0 else 0
        self.speed = 500
        self.shoot_cooldown = 0.3
        self.has_sonic_power_up = False

    def change_team_id(self):
        self.team = "BLOOM" if self._team_id == 0 else "SKY"
        self.team_id = 0 if self._team_id == 1 else 1
        self.rotation = 180 if self._team_id == 0 else 0

        
    def shoot(self):
        
        if(time.time() - self.last_shoot_time < self.shoot_cooldown):
            return
        
        self.last_shoot_time = time.time()
        
        
        if (self.has_sonic_power_up):
            if (self.rotation >= 360):
                self.rotation = 0
                
            self.rotation += 10
        

        elif (self.rotation != 0):
            self.rotation = 180 if self._team_id == 0 else 0
         
        shot_angle = self.rotation
            
        bullet = Bullet(self.x, self.y, shot_angle, self.id)
        return bullet
    
    
    def power_up_sonic(self):
        self.has_sonic_power_up = True
        self.shoot_cooldown = 0.00001
        

# Colisao
    def collided_with_bullet(self, bullet):
    
        if self.id == bullet.shooter_id:
            return False
        
        collision_x = (self.collision_box_x < bullet.collision_box_x + bullet.width) and (self.collision_box_x + self.width > bullet.collision_box_x)
        collision_y = (self.collision_box_y < bullet.collision_box_y + bullet.height) and (self.collision_box_y + self.height > bullet.collision_box_y)
        
        if(collision_x and collision_y):
            return True
        else:
            return False



player_bitmask_layout = [
    # attr                  bitmask, data_type
    ('x',                   1 << 0, 'float'),
    ('y',                   1 << 1, 'float'),
    ('is_alive',            1 << 2, 'u8'),
    ('hp',                  1 << 3, 'u8'),
    ('team_id',             1 << 4, 'u8'),
    ('team',                1 << 5, 'string'),
    ('total_kills',         1 << 6, 'u16'),
    ('speed',               1 << 7, 'float'),
    ('shoot_cooldown',      1 << 8, 'float'),
    ('username',            1 << 9, 'string'),
    ('has_sonic_power_up',  1 << 10, 'u8')
]




SPAWN_POSITIONS = {"SKY": {"x": 100, "y": 100}, "BLOOM": {"x": 100, "y": 500}}

