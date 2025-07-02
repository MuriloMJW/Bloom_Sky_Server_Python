
SPAWN_POSITIONS = {
    "SKY": {"x": 100, "y": 100},
    "BLOOM": {"x": 100, "y": 500}
}

player_bitmask_layout = [
    # attr          bitmask, data_type
    ('x',              1 << 0, 'float'),
    ('y',              1 << 1, 'float'),
    ('is_alive',       1 << 2, 'u8'),
    ('hp',             1 << 3, 'u8'),
    ('team_id',        1 << 4, 'u8'),
    ('team',           1 << 5, 'string'),
    ('total_kills',    1 << 6, 'u16'),
    ('speed',          1 << 7, 'float'),
    ('shoot_cooldown', 1 << 8, 'float')

    ]

class Player:

    def __init__(self, websocket, id):

        self._websocket = websocket
        self._ip = websocket.remote_address

        self._id = id

        self._team_id = id%2
        self._team = "SKY" if self._team_id == 0 else "BLOOM"

        self._x = SPAWN_POSITIONS[self.team]["x"]
        self._y = SPAWN_POSITIONS[self.team]["y"]

        self._input_direction_x = 0
        self._input_direction_y = 0


        self._is_alive = True
        self._hp = 100  # HP inicial do jogador



        #self.is_sonic

        self._total_kills = 0

        self._speed = 500

        self._shoot_cooldown = 0.1

        # --- Atributos exclusivos do Player no servidor --- #
        self.total_deaths = 0

        self._changed_attributes = set() # Conjunto para armazenar quais stats foram alterados

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
            self._changed_attributes.add("x")

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, new_y):
        if (new_y != self._y):
            self._y = new_y
            self._changed_attributes.add("y")


    @property
    def input_direction_x(self):
        return self._input_direction_x

    @input_direction_x.setter
    def input_direction_x(self, new_input_direction_x):
        if (new_input_direction_x != self._input_direction_x):
            self._input_direction_x = new_input_direction_x
            self._changed_attributes.add("input_direction_x")

    @property
    def input_direction_y(self):
        return self._input_direction_y

    @input_direction_y.setter
    def input_direction_y(self, new_input_direction_y):
        if (new_input_direction_y != self._input_direction_y):
            self._input_direction_y = new_input_direction_y
            self._changed_attributes.add("input_direction_y")


    # --- is_alive e hp --- #
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

    # --- Team ID e Team --- #
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


    # --- Speed --- #
    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, new_speed):
        if (new_speed != self._speed):
            self._speed = new_speed
            self._changed_attributes.add("speed")

    # --- Shoot --- #
    @property
    def shoot_cooldown(self):
        return self._shoot_cooldown

    @shoot_cooldown.setter
    def shoot_cooldown(self, new_shoot_cooldown):
        if (new_shoot_cooldown != self._shoot_cooldown):
            self._shoot_cooldown = new_shoot_cooldown
            self._changed_attributes.add("shoot_cooldown")


    # --- String Representation --- #

    def __str__(self):
        status = "Vivo" if self._is_alive else "Morto"
        return (
            f"Player {self._id} | "
            f"Time: {self._team} | "
            f"Posição: (x={self._x}, y={self._y}) | "
            f"Status: {status}"
            f" | HP: {self._hp} | "
            f"Kills: {self._total_kills} | "
            f"Deaths: {self.total_deaths} | "
            f"IP: {self._ip[0]}:{self._ip[1]}"
            f" | Team ID: {self._team_id}"
            f" | Changed Stats: {self._changed_attributes}"
            f" | Speed: {self._speed}"
            f" | Shoot Cooldown: {self._shoot_cooldown}"
        )

    # --- Métodos do Player --- #

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
