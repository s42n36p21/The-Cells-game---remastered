import pyglet
from pyglet.window.mouse import MouseStateHandler
from TCGCell import get_color, TILE_SIZE, Cell, PAD

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
        self.view = pyglet.shapes.Box(0,0,TILE_SIZE-PAD+4, TILE_SIZE-PAD+4, 3, color=[250,250,10], batch=self._batch)
        self.view.anchor_x = -PAD/2 + 2
        self.view.anchor_y = -PAD/2 + 2

    def on_update(self, dt):
        x, y = self.window.camera.screen_to_world(self.pos['x'], self.pos['y'])
        row = y // TILE_SIZE
        col = x // TILE_SIZE
        cell: Cell = select(self.game, row, col)
        if cell:
            
            if cell.model.hit(owner=self.game.players.current()):
                self.view.color = get_color(self.game.players.current())
                self.view.x, self.view.y = (TILE_SIZE * col, TILE_SIZE * row)
                self.view.visible = True
            else:
                self.view.visible = False
        else:
            self.view.visible = False

    def draw(self):
        self._batch.draw()