import pyglet
from pyglet.window.mouse import MouseStateHandler
from TCGCell import get_color, TILE_SIZE, Cell, PAD
from TCGBoard import GameStateAttribute as GSA

class Hover:
    def __init__(self, tile_size, padding, thickness=3, batch=None):
        self._batch = batch or pyglet.graphics.Batch()
        self._tile_size = tile_size
        self._padding = min(padding, tile_size/2)
        self._view = pyglet.shapes.Box(0, 0, tile_size-padding, tile_size-padding, thickness, color=[250,250,10], batch=self._batch)
        self._view.anchor_position = [-self._padding / 2] * 2
        self.hide()
        
    def draw(self):
        self._batch.draw()    
    
    def show(self):
        self._view.visible = True
        
    def hide(self):
        self._view.visible = False
    
    @property
    def color(self):
        return self._view.color
    
    @color.setter
    def color(self, value):
        self._view.color = value
    
    @property
    def position(self):
        self._view.position
        
    @position.setter    
    def position(self, value):        
        x, y = value
        self._view.position = x // self._tile_size * self._tile_size, y // self._tile_size * self._tile_size
        
    @property
    def tile_position(self):
        self._view.position // self._tile_size
        
    @position.setter    
    def tile_position(self, value):        
        row, col = value
        self._view.position = col * self._tile_size, row * self._tile_size
        
class Cursor:
    def __init__(self, window, batch=None):
        self._batch = batch or pyglet.graphics.Batch()
        self.pos = MouseStateHandler()
        self.window = window
        self.window.push_handlers(self.pos, self)
        
        self.cursor = pyglet.shapes.Circle(0, 0, radius=10, color=(255, 255, 255, 127), batch=self._batch)
        
    def on_mouse_enter(self, x, y):
        """Событие когда курсор входит в окно"""
        self.cursor.visible = True
    
    def on_mouse_leave(self, x, y):
        """Событие когда курсор покидает окно"""
        self.cursor.visible = False
    
    @property
    def visible(self):
        """Возвращает текущее состояние видимости курсора"""
        return self.cursor.visible
    
    @visible.setter
    def visible(self, value):
        """Устанавливает видимость курсора"""
        self.cursor.visible = value
    
    @property
    def color(self):
        """Возвращает текущий цвет курсора (без альфа-канала)"""
        return self.cursor.color[:3]
    
    @color.setter
    def color(self, value):
        """Устанавливает цвет курсора с автоматической прозрачностью 50%"""
        r, g, b, *a = get_color(value)
        self.cursor.color = (r, g, b, 127)
    
    def on_update(self, dt):
        """Обновление позиции курсора"""
        self.cursor.x = self.pos['x']
        self.cursor.y = self.pos['y']

    def draw(self):
        self._batch.draw()

def select(board, row, col):
    return board.cells.get((row, col))


class HoverInspector:
    def __init__(self, window, game, batch=None):
        self._batch = batch or pyglet.graphics.Batch()
        self.pos = MouseStateHandler()
        self.window = window
        self.game = game
        self.window.push_handlers(self.pos, self)
        self.view = Hover(TILE_SIZE, PAD-4, 3, batch=self._batch)

    def on_update(self, dt):
        x, y = self.window.camera.screen_to_world(self.pos['x'], self.pos['y'])
        row = y // TILE_SIZE
        col = x // TILE_SIZE
        cell: Cell = select(self.game, row, col)
        if self.game.phase() == GSA.EDIT:
            self.view.color = get_color(self.game.players.current())
            self.view.position = x, y
            self.view.show()
        elif cell:
            if cell.model.hit(owner=self.game.players.current()):
                self.view.color = get_color(self.game.players.current())
                self.view.position = x, y
                self.view.show()
            else:
                self.view.hide()
        else:
            self.view.hide()

    def draw(self):
        self._batch.draw()
        
def link_cell(a, b, type=0):
    match type:
        case 0: # a --> b
            a.model.link(b.model)
        case 1: # a <-- b
            link_cell(b, a)
        case 2: # a <-> b
            link_cell(b, a)
            link_cell(a, b)