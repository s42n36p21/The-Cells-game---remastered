from Cell import Cell
from Board import Board
from typing import Type


class Assembler:
    def __init__(self, board):
        self.board: Board = board
        self.SIB = list()
    
    def create(self, row: int, col: int, cell_type: Type[Cell]):
        cell = cell_type()
        index = len(self.board.buffer)
        if self.SIB:
            index = self.SIB.pop()
            self.board.buffer.put(cell, index)
        else:
            self.board.buffer.append(cell)
            
        self.board.map.add(row, col, cell)
        cell.position = (row, col)
        cell.index = index 
        return cell
        
    def delete(self, cell: Cell):
        index, row, col = cell.index, *cell.position
        self.board.buffer.delete(index)
        self.board.map.delete(row, col)
        self.SIB.append(index)
        
    def link(self, out_cell: Cell, inc_cell: Cell):
        out_cell.model.links._outgoing_links.append(inc_cell)
        inc_cell.model.links._incoming_links.append(out_cell)
        
    def unlink(self, out_cell: Cell, inc_cell: Cell):
        out_cell.model.links._outgoing_links.remove(inc_cell)
        inc_cell.model.links._incoming_links.remove(out_cell)
        
        
