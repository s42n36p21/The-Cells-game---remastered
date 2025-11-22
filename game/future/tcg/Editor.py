from Assembler import Assembler, Board, Cell
from abc import ABC, abstractmethod
from typing import Type, List

class Command(ABC):
    """Комады для удобного редактирования игрового поля"""
    
    def __init__(self, assembler: Assembler, *args, **kwargs):
        self.assembler = assembler
        self._args = args
        self.kwargs = kwargs
    
    @abstractmethod
    def execute(self):
        """Исполнить команду"""
    
    def undo(self):
        """Выпонить отмену команды (откат). Если вернёт True, значит откат невозможен"""
        return True
    
    def redo(self):
        """Повторить команду, при условии что она до этого была выполнена и отменена. По умолчанию просто повторяет execute"""
        self.execute()
    
class MultiCommand(Command):
    """Выполняет за один такт и одно дейтсвие несколько команд"""
        
    def __init__(self, assembler, *args: Command, **kwargs):
        super().__init__(assembler, *args, **kwargs)
    
    def execute(self):
        for cmd in self._args:
            cmd: Command
            cmd.execute()
            
    def undo(self):
        for cmd in reversed(self._args):
            cmd: Command
            cmd.undo()
            
    def redo(self):
        for cmd in self._args:
            cmd: Command
            cmd.redo()
    
class CreateCellCommand(Command):
    def __init__(self, assembler: Assembler, row: int, col: int, cell_type: Type[Cell]):
        super().__init__(assembler, row, col, cell_type)    

    def execute(self):
        self.created_cell = self.assembler.create(*self._args)
    
    def undo(self):
        self.assembler.delete(self.created_cell)

class DeleteCellCommand(Command):
    def __init__(self, assembler, cell: Cell):
        super().__init__(assembler)
        self.cell = cell
    
    def execute(self):
        self.assembler.delete(self.cell)
    
    def undo(self):
        row, col, index = *self.cell.position, self.cell.index
        board = self.assembler.board
        board.buffer.put(self.cell, index)
        board.map.add(row, col, self.cell)
        self.assembler.SIB.pop()
        
class LinkCellCommand(Command):
    def __init__(self, assembler, out_cell: Cell, inc_cell: Cell):
        super().__init__(assembler)
        self.out_cell = out_cell
        self.inc_cell = inc_cell
        
    def execute(self):
        self.assembler.link(self.out_cell, self.inc_cell)
    
    def undo(self):
        self.assembler.unlink(self.out_cell, self.inc_cell)
        
class UnlinkCellCommand(Command):
    def __init__(self, assembler, out_cell: Cell, inc_cell: Cell):
        super().__init__(assembler)
        self.out_cell = out_cell
        self.inc_cell = inc_cell
        
    def execute(self):
        self.assembler.unlink(self.out_cell, self.inc_cell)
    
    def undo(self):
        self.assembler.link(self.out_cell, self.inc_cell)
        
class Editor:
    def __init__(self):
        self.board = Board()
        self.asm = Assembler(self.board)
        self.cmd_history: List[Command] = list()
        self.undo_history: List[Command] = list()
        
    def undo(self):
        if not self.cmd_history:
            return
        
        cmd = self.cmd_history.pop()
        if cmd.undo():
            self.cmd_history.clear()
        else:
            self.undo_history.append(cmd)
    
    def redo(self):
        if not self.undo_history:
            return
        
        cmd = self.undo_history.pop()
        cmd.redo()
        self.cmd_history.append(cmd)