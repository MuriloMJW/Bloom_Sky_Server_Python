import math

class Bullet:
    def __init__(self, x, y, rotation, shooter_id) -> None:
        self._x = x
        self._y = y
        self._rotation = rotation
        self._shooter_id = shooter_id
        self._speed = 500
        self._rotation = 0
        
        self._width = 8
        self._height = 30
        self._collision_box_x = self.x - self._width/2
        self._collision_box_y = self.y - self._height/2
        


    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, new_x):
        self._x = new_x
        self._collision_box_x = new_x - self._width/2


    @property
    def y(self):
        return self._y
    
    @y.setter
    def y(self, new_y):
        self._y = new_y
        self._collision_box_y = new_y - self._height/2


    @property
    def rotation(self):
        return self._rotation
    

    @property
    def shooter_id(self):
        return self._shooter_id

    @property
    def speed(self):
        return self._speed
    
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height
    
    @property
    def collision_box_x(self):
        return self._collision_box_x
    
    @property
    def collision_box_y(self):
        return self._collision_box_y
    
    
    def move(self, DELTA):
        # O seno do angulo informa porcentagem de x correta
        # o cosseno do angulo informa a porcentagem de y
        rotation_in_radians = math.radians(self.rotation)

        
        deslocamento_x = math.sin(rotation_in_radians) 
        deslocamento_y = -math.cos(rotation_in_radians) 

        
        self.x += deslocamento_x * self.speed * DELTA
        self.y += deslocamento_y * self.speed * DELTA
        
    def collision(self, obj):
        return