

class Entity():
    def __init__(self, x, y, width, height, rotation, speed):
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._rotation = rotation
        self._speed = speed
    
    @property
    def collision_box_x(self):
        return self._x - self._width/2
    
    @property
    def collision_box_y(self):
        return self._y - self._height/2
    
    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, new_x):
        self._x = new_x
    
    @property
    def y(self):
        return self._y
    
    @y.setter
    def y(self, new_y):
        self._y = new_y
        
    @property
    def width(self):
        return self._width
    
    @property
    def height(self):
        return self._height
    
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, new_rotation):
        self._rotation = new_rotation
    
    @property
    def speed(self):
        return self._speed
    
    @speed.setter
    def speed(self, new_speed):
        self._speed = new_speed

