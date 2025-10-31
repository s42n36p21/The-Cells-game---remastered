from pyglet.window.mouse import MouseStateHandler, LEFT
from pyglet.window.key import KeyStateHandler
from TCGCell import TILE_SIZE, TYPE_CELL
from TCGtools import Hover, link_cell
from Camera import Camera

def _world_position(mouse, camera: Camera):
    x, y = mouse.data.get('x'), mouse.data.get('y')
    if x is None or y is None:
        return
    return camera.screen_to_world(x, y)

def _tile(x, y):
    return int(y // TILE_SIZE), int(x // TILE_SIZE)

def _auto_link(cell, pos, cells, out, in_):
    type = out + (in_ << 1) - 1
    x, y = pos

    for dx, dy in [(1,0),(0,1),(-1,0),(0,-1)]:
        other = x+dx, y+dy
        if other in cells:
            other_cell = cells[other]
            link_cell(cell, other_cell, type=type)
            other_cell.render()

class ToolBox:
    AUTO_LINK = True
    REPLACE = True

    OUT_LINK = True
    IN_LINK = True

    NO_REPEAT = True
    ONLY_NEIGHBORING = True

    TYPE_CELL = 0


class EditTool:
    def __init__(self, editor):
        self.editor: Editor = editor

    def use(self, tool):
        self.editor._tool = tool(self.editor)

    @property
    def key(self):
        return self.editor.key
    
    @property
    def mouse(self):
        return self.editor.mouse
    
    @property
    def cells(self):
        return self.editor._master.master.cells
    
    @property
    def batch(self):
        return self.editor._master.master.batch

    def update(self, dt):
        pass

    @classmethod
    def name(cls):
        return cls.__name__
    
    def clear_select(self):
        self.editor._select.clear()

    def inspect(self):
        return [str(cell) for cell in self.editor._select.values()]


class CreateCell(EditTool):
    def create_cell(self, w_pos, repalce=None, auto_link=None):
        repalce = self.editor.tool_box.REPLACE if repalce is None else repalce
        auto_link = self.editor.tool_box.AUTO_LINK if auto_link is None else auto_link
        if not w_pos:
            return
        
        if w_pos in self.cells:
            if repalce:
                pass
        else:
            cell = TYPE_CELL[self.editor.tool_box.TYPE_CELL](w_pos, self.batch)
            self.cells[w_pos] = cell
            
            if auto_link:
                _auto_link(cell, w_pos, self.cells, 
                            self.editor.tool_box.OUT_LINK,
                            self.editor.tool_box.IN_LINK)
            cell.render()

    def update(self, dt):
        if not self.mouse.data.get(LEFT):
            return
        w_pos = self.editor.world_position()
        self.create_cell(w_pos)
        

class DeleteCell(EditTool):
    def update(self, dt):
        if not self.mouse.data.get(LEFT):
            return
        w_pos = self.editor.world_position()
        self.delete_cell(w_pos)
    
    def delete_cell(self, w_pos):
        if not w_pos:
            return
        cell = self.cells.get(w_pos)
        if cell:
            render = [in_cell.position for in_cell in cell.model.incoming_links]
            cell.delete()
            self.cells.pop(w_pos)
            for r in render:
                self.cells[r].render()

class ClearLink(EditTool):
    pass

class Link(EditTool):
    pass

class UnLink(EditTool):
    pass

class FlexLink(EditTool):
    pass

class Select(EditTool):
    pass

class RectSelect(EditTool):
    pass

class Editor:
    def __init__(self, master):
        self._master = master
        scene = self._master.master.scene

        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        scene.push_handlers(self.key, self.mouse, self)

        self._tool = EditTool(self)
        self._select = dict()
        self.tool_box = ToolBox()

    def update(self, dt):
        self._tool.update(dt)

    def world_position(self):
        w_pos = _world_position(self.mouse, self._master.master.scene.camera)
        if w_pos:
            return _tile(*w_pos)
        
    def debug(self):
        return f'Tool: {self._tool.name()}\n'
    
    def use(self, tool):
        self._tool = tool(self)
            
    
