from pyglet.window.mouse import MouseStateHandler, LEFT
from pyglet.window.key import KeyStateHandler
from TCGCell import TILE_SIZE, TYPE_CELL, get_side
from TCGtools import Hover, link_cell
from Camera import Camera
from pyglet.graphics import Batch

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
            
def _default(value, default):
    return default if value is None else value

class ToolBox:
    AUTO_LINK = True
    REPLACE = True

    OUT_LINK = True
    IN_LINK = True

    NO_REPEAT = True
    ONLY_NEIGHBORING = 0#True

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
        repalce = _default(repalce, self.editor.tool_box.REPLACE)
        auto_link = _default(auto_link, self.editor.tool_box.AUTO_LINK)
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
    def update(self, dt):
        if not self.mouse.data.get(LEFT):
            return
        w_pos = self.editor.world_position()
        self.clear_cell_link(w_pos)
        
    def clear_cell_link(self, w_pos, out=None, in_=None):
        if not w_pos:
            return
        cell = self.cells.get(w_pos)
        if cell:
            render = [in_cell.position for in_cell in cell.model.incoming_links]            
            
            if _default(in_, self.editor.tool_box.IN_LINK):
                for icell in cell.model.incoming_links:
                    icell.outgoing_links.remove(cell.model)
                cell.model.incoming_links.clear()
            
            
            if _default(out, self.editor.tool_box.OUT_LINK):
                for icell in cell.model.outgoing_links:
                    icell.incoming_links.remove(cell.model)
                cell.model.outgoing_links.clear()
                
            for r in render:
                self.cells[r].render()
            cell.render()
            
class Link(EditTool):
    def __init__(self, editor):
        super().__init__(editor)
        self._select = None
        self._flag = False
        
    def update(self, dt):
        click = self.mouse.data.get(LEFT)
        
        if not click:
            self._flag = False
            return
        if self._flag:
            return
        
        w_pos = self.editor.world_position()
        
        if not w_pos:
            return
        cell = self.cells.get(w_pos)
        if not cell:
            return
        
        if self._select is None:
            self._select = w_pos
            self._flag = True
        else:
            self.link_cells(self._select, w_pos)
            self._flag = True
            self._select = None
            
    def link_cells(self, a, b, out=None, in_=None, no_repeat=None, only_neighboring=None):
        par = self.editor.tool_box
        only_neighboring = _default(only_neighboring, par.ONLY_NEIGHBORING)
        
        cell_a, cell_b = self.cells.get(a), self.cells.get(b)
        
        if only_neighboring:
            if not get_side(cell_a.model, cell_b.model):
                return
        
        no_repeat = not _default(no_repeat, par.NO_REPEAT)
        out = _default(out, par.OUT_LINK) and (no_repeat or (cell_b.model not in cell_a.model.outgoing_links))
        in_ = _default(in_, par.IN_LINK) and (no_repeat or (cell_b.model not in cell_a.model.incoming_links))
        
        type = out + (in_ << 1) - 1
        
        link_cell(cell_a, cell_b, type=type)
        cell_a.render()
        cell_b.render()
        
class UnLink(Link):
    def link_cells(self, a, b, out=None, in_=None, no_repeat=None, only_neighboring=None):
        par = self.editor.tool_box
        
        out = _default(out, par.OUT_LINK)
        in_ = _default(in_, par.IN_LINK) 
        
        cell_a, cell_b = self.cells.get(a), self.cells.get(b)
        
        if out:
            if cell_b.model in cell_a.model.outgoing_links:
                cell_a.model.outgoing_links.remove(cell_b.model)
                cell_b.model.incoming_links.remove(cell_a.model)

        if in_:
            if cell_b.model in cell_a.model.incoming_links:
                cell_a.model.incoming_links.remove(cell_b.model)
                cell_b.model.outgoing_links.remove(cell_a.model)
        cell_a.render()
        cell_b.render()   

class FlexLink(Link):
    def link_cells(self, a, b, out=None, in_=None, no_repeat=None, only_neighboring=None):
        par = self.editor.tool_box
        assert _default(no_repeat, par.NO_REPEAT), "В режиме мультиграфа запрещено использовать данный режим"
        
        cell_a, cell_b = self.cells.get(a), self.cells.get(b)
        
        _out = _default(out, par.OUT_LINK) and (cell_b.model not in cell_a.model.outgoing_links)
        _in_ = _default(in_, par.IN_LINK) and (cell_b.model not in cell_a.model.incoming_links)
    
        type = _out + (_in_ << 1) - 1
        if type != -1:
            super().link_cells(a, b, out, in_, no_repeat, only_neighboring)
        else:
            UnLink(self.editor).link_cells(a, b, out, in_, no_repeat, only_neighboring)

class Select(EditTool):
    pass

class RectSelect(EditTool):
    pass


class Editor:
    def __init__(self, master):
        self._master = master
        self.batch = Batch()
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
        
        return _get_tool(self._tool, CreateCell) + '1 - Создать клетку\n' + \
               _get_tool(self._tool, DeleteCell) +  '2 - Удалить клетку\n' + \
               _get_tool(self._tool, Link) +  '3 - Связать клетку\n' + \
               _get_tool(self._tool, UnLink) +  '4 - Отвязать клетку\n' + \
               _get_tool(self._tool, FlexLink) +  '5 - Гибкая связка\n' + \
               _get_tool(self._tool, ClearLink) +  '6 - Отчистить связи\n' + \
               _get_par_(self.tool_box.AUTO_LINK) +  '7 - Авто-связка\n' + \
               _get_par_(self.tool_box.OUT_LINK) +  '8 - Выходящии связи\n' + \
               _get_par_(self.tool_box.IN_LINK) +  '9 - Входящие связи\n' + \
               TYPE_CELL[self.tool_box.TYPE_CELL].__name__ + " : " +  '0 - Тип клетки\n'
    
    def use(self, tool):
        self._tool = tool(self)
            
    def draw(self):
        self.batch.draw()

def _get_par_(par):
    return '>' if par else ' '

def _get_tool(curent, tool):
    return _get_par_(isinstance(curent, tool))

