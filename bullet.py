import math
import random
from entity import Entity


class Bullet(Entity):
    def __init__(self, x, y, rotation, shooter_id) -> None:
        _x = x
        _y = y
        _rotation = rotation
       
        _speed = 555
        _width = 8
        _height = 30
        
        super().__init__(_x, _y, _width, _height, _rotation, _speed)
        
        self._shooter_id = shooter_id
        
    @property
    def shooter_id(self):
        return self._shooter_id


    
    def move(self, DELTA):
        # O seno do angulo informa porcentagem de x correta
        # o cosseno do angulo informa a porcentagem de y
        rotation_in_radians = math.radians(self.rotation)


        
        deslocamento_x = math.sin(rotation_in_radians) 
        deslocamento_y = -math.cos(rotation_in_radians) 

        
        self.x += deslocamento_x * self.speed * DELTA
        self.y += deslocamento_y * self.speed * DELTA
    
    def collided_with_bullet(self, bullet):
        if self.shooter_id == bullet.shooter_id:
            return False
        
        collision_x = (self.collision_box_x < bullet.collision_box_x + bullet.width) and (self.collision_box_x + self.width > bullet.collision_box_x)
        collision_y = (self.collision_box_y < bullet.collision_box_y + bullet.height) and (self.collision_box_y + self.height > bullet.collision_box_y)
        
        if(collision_x and collision_y):
            return True
        else:
            return False

        
        