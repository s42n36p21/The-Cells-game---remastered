from enum import Enum, auto
from typing import List, Tuple
from ..Settings import Settings
from pyglet.graphics import Batch, Group
from pyglet.sprite import Sprite
from pyglet.image import load
from pyglet.shapes import Rectangle, Sector, Box
from pyglet import gl
from pyglet.text import Label
from colorsys import hsv_to_rgb
from collections import deque
import pyglet
from ..Settings import ASSET_DIR
#from TCGBoard import GameBoard


class RULES: # ЗАДЕЛ НА БУДУЩЕЕ
    _context = None
    
    BLOCK_SURROUNDED = 0
    BLOCK_INSULAR = 1
    HIDE_MODE = 0
    FOG_OF_WAR = 1
    ONLINE_MODE = 0
    WALLS = 1
    
    @classmethod
    def context(cls, ctx=None):
        cls._context = ctx
    
    @classmethod
    def is_hide(cls, cell):
        a_factor = b_factor = c_factor = False
        try:
            owner = RULES._context.this if cls.ONLINE_MODE else RULES._context.players.ptr.value
        except:
            owner = Energy.NEUTRAL
        a_factor = cls.HIDE_MODE and (cell.owner not in [owner, Energy.NEUTRAL]) 
        b_factor = cls.FOG_OF_WAR and cls.BLOCK_INSULAR and (not RULES.reachable(cell, owner))

        return a_factor or b_factor

    @classmethod
    def reachable(cls, cell, owner):
        if not cls.BLOCK_INSULAR:
            return True
        try:
            if cls._context.players.ptr.immunity:
                return True
        except:
            return True
        if cell.owner == owner:
            return True
        
        visited = set()
        queue = deque([cell])
        visited.add(cell)
        
        while queue:
            current = queue.popleft()
            for next in current.incoming_links:
                if (next not in visited):
                    if next.owner == owner:
                        return True
                    if next.owner == Energy.NEUTRAL:
                        visited.add(next)
                        queue.append(next)
    @classmethod
    def surrounded(cls, cell):
        if not cls.BLOCK_SURROUNDED or cell.owner != Energy.NEUTRAL:
            return 
        
        sur = {en.owner for en in cell.outgoing_links}
        
        if (len(sur) == 1):
            return sur.pop()
        
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


img_body = load_pixel_texture(ASSET_DIR / 'cell.png')
img_magic_body = load_pixel_texture(ASSET_DIR / 'magic_cell.png')
img_close_body = load_pixel_texture(ASSET_DIR / 'close_cell.png')

img_n = load_pixel_texture(ASSET_DIR / 'N.png')
img_e = load_pixel_texture(ASSET_DIR / 'E.png')
img_s = load_pixel_texture(ASSET_DIR / 'S.png')
img_w = load_pixel_texture(ASSET_DIR / 'W.png')
img_side = [img_n,img_e,img_s,img_w]

img_2n = load_pixel_texture(ASSET_DIR / '2N.png')
img_2e = load_pixel_texture(ASSET_DIR / '2E.png')
img_2s = load_pixel_texture(ASSET_DIR / '2S.png')
img_2w = load_pixel_texture(ASSET_DIR / '2W.png')
img_2side = [img_2n,img_2e,img_2s,img_2w]

img_n2n = load_pixel_texture(ASSET_DIR / 'N2N.png')
img_e2e = load_pixel_texture(ASSET_DIR / 'E2E.png')
img_s2s = load_pixel_texture(ASSET_DIR / 'S2S.png')
img_w2w = load_pixel_texture(ASSET_DIR / 'W2W.png')
img_D2side = [img_n2n,img_e2e,img_s2s,img_w2w]

TILE_SIZE = 64
PAD = 16

N = 1 << 0
E = 1 << 1
S = 1 << 2
W = 1 << 3
ALL = N | E | S | W

_2N = 1 << 4
_2E = 1 << 5
_2S = 1 << 6
_2W = 1 << 7

N2N = N | _2N
E2E = E | _2E
S2S = S | _2S
W2W = W | _2W

SIDES = [N, E, S, W, # CLASSIC
         _2N, _2E, _2S, _2W, # DOUBLE
        N2N, E2E, S2S, W2W, # SPLIT
        ]
IMG = img_side + img_2side + img_D2side


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
    
P_ENERGY = [
    Energy.P1,
    Energy.P2,
    Energy.P3,
    Energy.P4,
    Energy.P5,
    Energy.P6,
    Energy.P7,
    Energy.P8
]

S_ENERGY = [
    Energy.NEUTRAL,
    Energy.OTHER 
]


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
    input_owner: Energy
    power: int
    input_power: int
    outgoing_links: List['CellModel']
    incoming_links: List['CellModel']
    
    def __init__(self, position):
        self.position = tuple(position)
        self.owner = Energy.NEUTRAL
        self.power = 0
        self.input_owner = None
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
        
        if (pl := RULES.surrounded(self)):
            if (pl != Energy.NEUTRAL) and pl != owner:
                return
        
        if not RULES.reachable(self, owner):
            return

        return self.position == position and (self.owner in (owner, Energy.NEUTRAL))
    
    def link(self, other: 'CellModel'):
        self.outgoing_links.append(other)
        other.incoming_links.append(self)
        
    def charge(self, owner, amount=1):
        self.input_power += amount
        self.input_owner = owner if self.input_owner in [None, owner] else Energy.NEUTRAL
    
    def fill(self):
        self.power += self.input_power
        self.input_power = 0
        self.owner = (self.owner if self.input_owner is None else self.input_owner) if self.power else Energy.NEUTRAL
        self.input_owner = None
        
    def reaction(self):
        if self.is_full():
            self.power = 0
            for cell in self.outgoing_links:
                cell.charge(self.owner)
                #self.owner = Energy.NEUTRAL
            
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
    
def get_side(cell:CellModel, other: CellModel, dist=1):
    r1, c1 = cell.position
    r2, c2 = other.position
    dx = (c2-c1)
    dy = (r2-r1)

    if dx == 0:
        if dy == dist:
            return N
        elif dy == -dist:
            return S
    elif dy == 0:
        if dx == dist:
            return E
        elif dx == -dist:
            return W
    
    return 0    
    
from pyglet.gl import *

blend_src: int = GL_SRC_ALPHA
blend_dest: int = GL_ONE_MINUS_SRC_ALPHA
GOAST = 0
OPACITY = 192

class CellView:
    SENSOR_GROUP = Group(order=0)
    BODY_GROUP = Group(order=1)
    PARTICLE_GROUP = Group(order=2)
    
    SENSOR_TYPE = settings.sensor_type
    
    
    
    def __init__(self, cell_model: CellModel, batch=None):
        self.model = cell_model
        self.batch = batch or Batch()
        
        self._setup()
        
        row, col = cell_model.position
        
        self.display = Rectangle(PAD*2,PAD*2, 2*(TILE_SIZE-PAD-PAD), 2*(TILE_SIZE-PAD-PAD),
                                 color=(0,0,0), batch=self.render_batch , group=self.SENSOR_GROUP, 
                                 blend_dest=blend_dest, blend_src=blend_src)
        
        self.body = Sprite(img_body, 0, 0, batch=self.render_batch, group=self.BODY_GROUP,
                          blend_dest=blend_dest, blend_src=blend_src)
        self.body.scale = 2
        self.sides = []
        self.sensor = None
        
        self.result = None
        
        
    
    def _setup(self):
        self.render_batch = Batch()
        self.texture = pyglet.image.Texture.create(TILE_SIZE*2, TILE_SIZE*2,)# min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo = pyglet.image.Framebuffer()
        self.fbo.attach_texture(self.texture)
        self.result = None
    
    def render_sides(self):
        for side in self.sides:
            side.delete()
        self.sides.clear()
        
        f_side = 0
        
        for cell in self.model.outgoing_links:
            f_side |= get_side(self.model, cell)
        for cell in self.model.outgoing_links:
            f_side |= get_side(self.model, cell, 2) << 4
        
        row, col = self.model.position
        
        x, y = TILE_SIZE * col, TILE_SIZE * row
        xx, yy = x + TILE_SIZE , y + TILE_SIZE,

        blend_dest = GL_ONE_MINUS_SRC_ALPHA
        blend_src = GL_SRC_ALPHA

        self.sides = [Sprite(IMG[index], 0,0,
                              batch=self.render_batch, group=self.PARTICLE_GROUP,
                              blend_dest=blend_dest, blend_src=blend_src) \
            for index, side in enumerate(SIDES) if (side & f_side) == side]
        if RULES.WALLS:
            WALL_COLOR = (48,24,7)
            self.walls = []
            pad = PAD / 2
            if not (N2N & f_side):
                self.walls.append(Rectangle(x-pad, yy-pad, TILE_SIZE+2*pad, pad*2, batch=self.batch, color=WALL_COLOR))
            if not E2E & f_side:
                self.walls.append(Rectangle(xx-pad, y-pad, pad*2, TILE_SIZE+2*pad, batch=self.batch, color=WALL_COLOR))
            if not S2S & f_side:
                self.walls.append(Rectangle(x-pad, y-pad, TILE_SIZE+2*pad, pad*2, batch=self.batch, color=WALL_COLOR))
            if not W2W & f_side:
                self.walls.append(Rectangle(x-pad, y-pad, pad*2, TILE_SIZE+2*pad, batch=self.batch, color=WALL_COLOR))
            
        for s in self.sides:
                s.scale = 2
                
    def goast(self):
        if not GOAST:
            return
        
        for s in self.sides:
            s.opacity = OPACITY
        self.body.opacity = OPACITY
        if self.sensor:
            self.sensor.opacity = OPACITY
        self.display.opacity = OPACITY        
           
    def render_sensor(self):

        if self.sensor is not None:
            self.sensor.delete()
        
        row, col = self.model.position
        cx, cy = col*TILE_SIZE + TILE_SIZE/2, row*TILE_SIZE + TILE_SIZE/2
        
        blend_dest = GL_ONE_MINUS_SRC_ALPHA
        blend_src = GL_SRC_ALPHA
        
        if settings.sensor_type:
            lim_power = self.model.lim_power() or float('inf')
            progress = self.model.power / lim_power
            self.sensor = Sector(32*2,32*2, TILE_SIZE/3*2, None,-360*progress, start_angle=90,
                                color=(*get_color(self.model.owner)[:3], 255), 
                                group=self.SENSOR_GROUP, batch=self.render_batch,
                                blend_dest=blend_dest, blend_src=blend_src)
            
        else:
            self.sensor = Label(str(self.model.power), 32*2,32*2+2, anchor_x='center', anchor_y='center', 
                               color=(*get_color(self.model.owner)[:3], 255), font_size=11*2, weight='bold',dpi=96,
                               group=self.SENSOR_GROUP, batch=self.render_batch)
    
    def update(self):
        if self.sensor is None:
            return
        self.goast()
        if RULES.is_hide(self.model):
            if settings.sensor_type:
                self.sensor.angle = -360
            else:
                self.sensor.text = '?'
            self.sensor.color = (*get_color(Energy.OTHER)[:3], 255)
        else:
            if settings.sensor_type:
                lim_power = self.model.lim_power() or float('inf')
                progress = self.model.power / lim_power
                self.sensor.angle = -360*progress
            else:
                self.sensor.text = str(self.model.power)
            self.sensor.color = (*get_color(self.model.owner)[:3], 255)
            
        # Устанавливаем opacity для всех элементов

        self.render()

    def render(self):
        self.fbo.bind()
        glClearColor(0,0,0,0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.render_batch.draw()
        self.fbo.unbind()
        row, col = self.model.position
        
        if self.result:
            self.result.delete()
        self.result = Sprite(self.texture,col*TILE_SIZE, row*TILE_SIZE, batch=self.batch, )
        self.result.scale = 1/2
        self.result.opacity = 255
        
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
            
    def is_considered(self):
        return 

class CloseCellView(CellView):
    def __init__(self, cell_model, batch=None):
        self.model = cell_model
        self.batch = batch or Batch()
        
        self._setup()
        
        row, col = 2,2
        self.display = Rectangle(2*PAD, 2*PAD, 2*TILE_SIZE-PAD*4, 2*TILE_SIZE-PAD*4,
                                 color=(0,0,0,255), batch=self.render_batch, group=self.SENSOR_GROUP)
        self.body = Sprite(img_close_body,0,0, batch=self.render_batch, group=self.BODY_GROUP)
        self.body.scale=2
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
        
        row, col = 0,0
        cx, cy = col*TILE_SIZE + TILE_SIZE/2, row*TILE_SIZE + TILE_SIZE/2
        
        if settings.sensor_type:
            lim_power = self.model.lim_power() or float('inf')
            progress = self.model.power / lim_power
            self.sensor = Sector(32*2,32*2, TILE_SIZE/3*2, None, 0, start_angle=90,color=VOID_COLOR, group=self.SENSOR_GROUP, batch=self.render_batch)
        else:
            self.sensor = Label("X", 32*2,32*2+2, anchor_x='center', anchor_y='center', 
                               color=VOID_COLOR, font_size=11*2, weight='bold',dpi=96,
                               group=self.PARTICLE_GROUP, batch=self.render_batch)
            
    def update(self):
        self.goast()
        self.render()
    
    
        
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
        

class ProtectedCellModel(CellModel):
    def __init__(self, position):
        super().__init__(position)
        self.owner = Energy.OTHER

    def hit(self, position=None, owner=None):
        owner = owner or self.owner
        position = position or self.position
        return self.position == position and (self.owner in (owner,))

    def fill(self):
        super().fill()
        if not self.power:
            self.owner = Energy.OTHER
            

class ProtectedCell(Cell):
    def __init__(self, position, batch):
        self.model = ProtectedCellModel(position)
        self.view = CellView(self.model, batch)

class MagicCellModel(CellModel):
    port = dict()
    origin: CellModel

    def __init__(self, position, port=0):
        self.origin = self.port.get(port)
        if self.origin is None:
            self.origin = CellModel(position)
            self.origin.shadow = []
            self.port[port] = self.origin            
        super().__init__(position)
        self.origin = self.port.get(port)
        self.origin.shadow.append(self)
        self.reacted = False
    
    @property
    def owner(self):
        return self.origin.owner
    
    @property
    def power(self):
        return self.origin.power
    
    @owner.setter
    def owner(self, value):
        self.origin.owner = value
        
    @power.setter
    def power(self, value):
        self.origin.power = value
    
    def fill(self):
        self.reacted = False
        self.power += self.input_power
        self.input_power = 0
        if not any([cell.reacted for cell in self.origin.shadow]):
            self.owner = (self.owner if self.input_owner is None else self.input_owner) if self.power else Energy.NEUTRAL
            self.input_owner = None
    
    def reaction(self):
        self.reacted = True
        if self.is_full():
            if all([cell.reacted for cell in self.origin.shadow]):
                self.power = 0 
            for cell in self.outgoing_links:
                cell.charge(self.owner)
            
    
    def lim_power(self):
        return sum([len(out.outgoing_links) for out in self.origin.shadow])
    
    def delete(self):
        super().delete()
        self.origin.shadow.remove(self)
            

class MagicCellView(CellView):
    port = dict()
    
    def __init__(self, cell_model, batch=None, port=0):
        self.model = cell_model
        self.batch = batch or Batch()
        
        self._setup()
        
        row, col = 0,0
        self.display = Rectangle(col*TILE_SIZE+PAD*2, row*TILE_SIZE+PAD*2, TILE_SIZE*2-PAD*2*2, TILE_SIZE*2-PAD*2*2,
                                 color=(0,0,0,255), batch=self.render_batch, group=self.SENSOR_GROUP)
        self.body = Sprite(img_magic_body, col*TILE_SIZE, row*TILE_SIZE, batch=self.render_batch, group=self.BODY_GROUP)
        self.body.scale = 2
        GAP = 2 * 4
        self.port_color = Box(PAD*2 - GAP, PAD*2- GAP, (TILE_SIZE-PAD*2)*2 +  2*GAP, (TILE_SIZE-PAD*2)*2+  2*GAP, thickness=20,
                                 color=self.get_port_color(port), batch=self.render_batch, group=self.SENSOR_GROUP)
        self.sides = []
        self.sensor = None
        
        self.my_port = port
        origin = self.port.get(port)
        if origin is None:
            self.port[port] = [self]
        else:
            self.port[port].append(self)

    def destroy(self):
        super().destroy()
        self.port_color.delete()
        self.port[self.my_port].remove(self)
        
    def update(self):
        #return super().update()
        for cell in self.port[self.my_port]:
            CellView.update(cell)
    
    @staticmethod
    def get_port_color(port):
        r, g, b = hsv_to_rgb(port/255, .9, 1)
        return int(r * 255), int(g * 255), int(b * 255)

class MagicCell(Cell):   
    def __init__(self, position, batch, port=0):
        self.model = MagicCellModel(position, port)
        self.view = MagicCellView(self.model, batch, port)

class MagicCellPortA(MagicCell):
    def __init__(self, position, batch, port=0):
        super().__init__(position, batch, port)
        
class MagicCellPortB(MagicCell):
    def __init__(self, position, batch, port=85):
        super().__init__(position, batch, port)

class MagicCellPortC(MagicCell):
    def __init__(self, position, batch, port=170):
        super().__init__(position, batch, port)

class MagicCellPortD(MagicCell):
    def __init__(self, position, batch, port=42):
        super().__init__(position, batch, port)
        
class MagicCellPortE(MagicCell):
    def __init__(self, position, batch, port=128):
        super().__init__(position, batch, port)

class MagicCellPortF(MagicCell):
    def __init__(self, position, batch, port=213):
        super().__init__(position, batch, port)

class LogicCellModel(CellModel):
    def is_full(self):
        return self.owner != Energy.NEUTRAL and self.power != 0
    
    def reaction(self):
        if self.power >= self.lim_power():
            self.power = 0
            for cell in self.outgoing_links:
                cell.charge(self.owner)
        else:
            self.power = 0
            
class LogicCell(Cell):
    def __init__(self, position, batch):
        self.model = LogicCellModel(position)
        self.view = CellView(self.model, batch)
    

TYPE_CELL = [Cell, CloseCell, VoidCell, ProtectedCell,
             MagicCellPortA, MagicCellPortB, MagicCellPortC, MagicCellPortD, MagicCellPortE,MagicCellPortF, LogicCell]
