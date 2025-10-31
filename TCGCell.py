from enum import Enum, auto
from typing import List, Tuple
from Settings import Settings
from pyglet.graphics import Batch, Group
from pyglet.sprite import Sprite
from pyglet.image import load
from pyglet.shapes import Rectangle, Sector
from pyglet import gl
from pyglet.text import Label

settings = Settings()
settings.load()

def load_pixel_texture(filename):
    """Загружает текстуру с пиксельной фильтрацией"""
    image = load(filename)
    texture = image.get_texture()
    
    gl.glBindTexture(texture.target, texture.id)
    gl.glTexParameteri(texture.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(texture.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
    
    return texture


img_body = load_pixel_texture('src/cell.png')
img_close_body = load_pixel_texture('src/close_cell.png')

img_n = load_pixel_texture('src/N.png')
img_e = load_pixel_texture('src/E.png')
img_s = load_pixel_texture('src/S.png')
img_w = load_pixel_texture('src/W.png')
img_side = [img_n,img_e,img_s,img_w]


TILE_SIZE = 64
PAD = 16

N = 1 << 0
E = 1 << 1
S = 1 << 2
W = 1 << 3
ALL = N | E | S | W

class Energy(Enum):
    NEUTRAL = auto()
    OTHER = auto()

    P1 = auto()
    P2 = auto()
    P3 = auto()
    P4 = auto()
    P5 = auto()
    P6 = auto()
    P7 = auto()
    P8 = auto()

def get_color(energy):
    return {
        Energy.NEUTRAL: (250,250,250),
        Energy.OTHER: (132,132,132),
            
        
        Energy.P1: (255, 150, 150),    # Теплый розовый
        Energy.P2: (150, 255, 150),    # Светло-лаймовый
        Energy.P3: (150, 150, 255),    # Лавандово-синий
        Energy.P4: (255, 255, 150),    # Солнечный желтый
        Energy.P5: (255, 150, 255),    # Орхидея
        Energy.P6: (150, 255, 255),    # Аквамарин
        Energy.P7: (255, 200, 100),    # Апельсиновый
        Energy.P8: (100, 115, 255) 
        }[energy]


class CellModel:
    position: Tuple[int, int]
    owner: Energy
    power: int
    input_power: int
    outgoing_links: List['CellModel']
    incoming_links: List['CellModel']
    
    def __init__(self, position):
        self.position = tuple(position)
        self.owner = Energy.NEUTRAL
        self.power = 0
        self.input_power = 0
        self.outgoing_links = []   # ссылки на другие клетки
        self.incoming_links = []   # ссылки от других клеток
        
    def __eq__(self, other: 'CellModel'):
        return self.position == other.position

    def __hash__(self):
        return hash(self.position)
    
    def is_full(self):
        return self.owner != Energy.NEUTRAL and self.power >= self.lim_power()
    
    def is_considered(self):
        return self.owner != Energy.NEUTRAL
    
    def lim_power(self):
        return len(self.outgoing_links)
    
    def hit(self, position=None, owner=None):
        owner = owner or self.owner
        position = position or self.position
        return self.position == position and (self.owner in (owner, Energy.NEUTRAL))
    
    def link(self, other: 'CellModel'):
        self.outgoing_links.append(other)
        other.incoming_links.append(self)
        
    def charge(self, owner, amount=1):
        self.input_power += amount
        self.owner = owner
    
    def fill(self):
        self.power += self.input_power
        self.input_power = 0
    
    def reaction(self):
        if self.is_full():
            self.power = 0
            for cell in self.outgoing_links:
                cell.charge(self.owner)
            self.owner = Energy.NEUTRAL
            
    def copy(self):
        cell = CellModel(self.position)
        
        cell.owner = self.owner
        cell.power = self.power
        cell.input_power = self.input_power
        cell.incoming_links = self.incoming_links.copy()
        cell.outgoing_links = self.outgoing_links.copy()
        
    def delete(self):
        for cell in self.incoming_links:
            cell: CellModel
            cell.outgoing_links.remove(self)
            
        for cell in self.outgoing_links:
            cell: CellModel
            cell.incoming_links.remove(self)
        
        self.outgoing_links.clear()
        self.incoming_links.clear()
    
    def __repr__(self):
        row, col = self.position
        
        return f'<Cell row={row} col={col} power={self.power} owner={self.owner.name}>'
    
def get_side(cell:CellModel, other: CellModel):
    r1, c1 = cell.position
    r2, c2 = other.position
    dx = (c2-c1)
    dy = (r2-r1)

    if dx == 0:
        if dy == 1:
            return N
        elif dy == -1:
            return S
    elif dy == 0:
        if dx == 1:
            return E
        elif dx == -1:
            return W
    
    return 0    
     

class CellView:
    SENSOR_GROUP = Group(order=0)
    BODY_GROUP = Group(order=1)
    PARTICLE_GROUP = Group(order=2)
    
    SENSOR_TYPE = settings.sensor_type
    
    def __init__(self, cell_model: CellModel, batch=None):
        self.model = cell_model
        self.batch = batch or Batch()
        
        row, col = cell_model.position
        self.display = Rectangle(col*TILE_SIZE+PAD, row*TILE_SIZE+PAD, TILE_SIZE-PAD*2, TILE_SIZE-PAD*2,
                                 color=(0,0,0,255), batch=batch, group=self.SENSOR_GROUP)
        self.body = Sprite(img_body, col*TILE_SIZE, row*TILE_SIZE, batch=batch, group=self.BODY_GROUP)
        self.sides = []
        self.sensor = None
        
    def render_sides(self):
        for side in self.sides:
            side.delete()
        self.sides.clear()
        
        f_side = 0
        
        for cell in self.model.outgoing_links:
            f_side |= get_side(self.model, cell)
        
        row, col = self.model.position
        self.sides = [Sprite(img_side[index], col*TILE_SIZE, row*TILE_SIZE, batch=self.batch, group=self.PARTICLE_GROUP) \
            for index, side in enumerate([N, E, S, W]) if side & f_side]
                   
    def render_sensor(self):
        if self.sensor is not None:
            self.sensor.delete()
        
        row, col = self.model.position
        cx, cy = col*TILE_SIZE + TILE_SIZE/2, row*TILE_SIZE + TILE_SIZE/2
        
        if settings.sensor_type:
            lim_power = self.model.lim_power() or float('inf')
            progress = self.model.power / lim_power
            self.sensor = Sector(cx, cy, TILE_SIZE/3, None,-360*progress, start_angle=90,color=get_color(self.model.owner), group=self.SENSOR_GROUP, batch=self.batch)
        else:
            self.sensor = Label(str(self.model.power), cx, cy+1, anchor_x='center', anchor_y='center', color=get_color(self.model.owner), font_size=12, weight='bold', group=self.SENSOR_GROUP, batch=self.batch)
    
    def update(self):
        if self.sensor is None:
            return
        if settings.sensor_type:
            lim_power = self.model.lim_power() or float('inf')
            progress = self.model.power / lim_power
            self.sensor.angle = -360*progress
        else:
            self.sensor.text = str(self.model.power)
        self.sensor.color = get_color(self.model.owner)
        
    def destroy(self):
        self.body.delete()
        self.display.delete()
        if self.sensor is not None:
            self.sensor.delete()
        for side in self.sides:
            side.delete()

    def draw(self):
        self.batch.draw()
    
class Cell:
    def __init__(self, position, batch):
        self.model = CellModel(position)
        self.view = CellView(self.model, batch)
        
    def delete(self):
        self.model.delete()
        self.view.destroy()

    def render(self):
        self.view.render_sides()
        self.view.render_sensor()
        self.view.update()
        
    def __repr__(self):
        return str(self.model)

    
class CloseCellModel(CellModel):
    def hit(self, position=None, owner=None):
        return None
        
    def reaction(self):
        if self.is_full():
            self.power = 0
            for cell in self.outgoing_links:
                cell.charge(self.owner)
            self.owner = Energy.NEUTRAL
            
    def is_considered(self):
        return 

class CloseCellView(CellView):
    def __init__(self, cell_model, batch=None):
        self.model = cell_model
        self.batch = batch or Batch()
        
        row, col = cell_model.position
        self.display = Rectangle(col*TILE_SIZE+PAD, row*TILE_SIZE+PAD, TILE_SIZE-PAD*2, TILE_SIZE-PAD*2,
                                 color=(0,0,0,255), batch=batch, group=self.SENSOR_GROUP)
        self.body = Sprite(img_close_body, col*TILE_SIZE, row*TILE_SIZE, batch=batch, group=self.BODY_GROUP)
        self.sides = []
        self.sensor = None
        

class CloseCell(Cell):
    def __init__(self, position, batch):
        self.model = CloseCellModel(position)
        self.view = CloseCellView(self.model, batch)
        
class VoidCellView(CellView):
    def render_sensor(self):
        VOID_COLOR = [31]*3
        
        if self.sensor is not None:
            self.sensor.delete()
        
        row, col = self.model.position
        cx, cy = col*TILE_SIZE + TILE_SIZE/2, row*TILE_SIZE + TILE_SIZE/2
        
        if settings.sensor_type:
            lim_power = self.model.lim_power() or float('inf')
            progress = self.model.power / lim_power
            self.sensor = Sector(cx, cy, TILE_SIZE/3, None, 0, start_angle=90,color=VOID_COLOR, group=self.SENSOR_GROUP, batch=self.batch)
        else:
            self.sensor = Label("X", cx, cy+1, anchor_x='center', anchor_y='center', color=VOID_COLOR, font_size=12, weight='bold', group=self.SENSOR_GROUP, batch=self.batch)
    
        
    def update(self):
        return 
        
class VoidCellModel(CloseCellModel):
    def charge(self, owner, amount=1):
        return 
    def is_full(self):
        return 
    def link(self, other):
        return 
    
class VoidCell(Cell):
    def __init__(self, position, batch):
        self.model = VoidCellModel(position)
        self.view = VoidCellView(self.model, batch)
        
TYPE_CELL = [Cell, CloseCell, VoidCell]