from Cell import Cell
from typing import List, Dict, Tuple, TypeAlias, Iterable
from abc import ABC, abstractmethod

class CellBuffer(list):
    def put(self, cell: Cell, index: int):
        """Установить клетку на указанный индекс"""
        if index >= len(self):
            exp_size = index - len(self) + 1
            self.extend([None]*exp_size)
        self[index] = cell
    
    def delete(self, index: int):
        """Удаление клетки по её индексу в буфере"""
        self[index] = None
        
    def compress(self):
        """Убрать все разряженые позиции с выравниванием индексов клетки"""
        index = 0
        while index < len(self):
            if self[index] is None:
                last = self.pop()
                if last is None:
                    continue
                self[index] = last
                last.index = index
            else:
                index += 1
                
    def fix(self):
        """Заменить индексы клеток на их индексы в буфере"""
        for index, cell in enumerate(self):
            cell.index = index

POSITION: TypeAlias = Tuple[int, int]
CHUNK: TypeAlias = Dict[POSITION, Cell]    

CHUNK_SIZE: int = 4

class ICellChunk(ABC):
    def __init__(self, row: int, col: int, size: int=CHUNK_SIZE):
        self.position = (row, col)
        self.size = size
    
    @abstractmethod
    def add(self, row: int, col: int, cell: Cell):
        """Добавить клетку в чанк"""
    
    @abstractmethod
    def delete(self, row: int, col: int):
        """Удалить клетку из чанка"""
    
    @abstractmethod
    def select(self, row: int, col: int) -> Cell | None:
        """Выбрать клетк, если существуте """

    @abstractmethod
    def __bool__(self) -> bool:
        """Пустой ли чанк"""

    @abstractmethod
    def __iter__(self) -> Iterable[Cell]:
        """Получить клетки в чанке"""
        
    def __repr__(self):
        return str(list(self))

class ICellMap(ABC):
    @abstractmethod
    def add(self, row: int, col: int, cell: Cell):
        """Добавить клетку на карту"""
    
    @abstractmethod
    def delete(self, row: int, col: int):
        """Удалить клетку с карты"""
    
    @abstractmethod
    def select(self, row: int, col: int) -> Cell | None:
        """Выбрать клетк, если существуте"""
    
    @abstractmethod    
    def chunk(self, chunk_row: int, chunk_col: int) -> ICellChunk | None:
        """Выбрать чанк, если существует"""
    
    def __repr__(self):
        """Все чанки"""           
        
class CellChunk(ICellChunk):
    def __init__(self, row, col, size = CHUNK_SIZE):
        super().__init__(row, col, size)
        self.cells: Dict[POSITION, Cell] = dict()
    
    def add(self, row, col, cell):
        self.cells[(row, col)] = cell
        
    def delete(self, row, col):
        del self.cells[(row, col)]
        
    def select(self, row, col):
        return self.cells.get((row, col))
        
    def __bool__(self):
        return bool(self.cells)
    
    def __iter__(self):
        return iter(self.cells.values())
    
class CellMap(ICellMap):    
    def __init__(self, chunk_size=CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.chunks: Dict[POSITION, ICellChunk] = dict()
    
    def chunk_position(self, row: int, col: int) -> POSITION:
        return row // self.chunk_size, col // self.chunk_size
    
    def add(self, row, col, cell):
        chunk_position = self.chunk_position(row, col)
        chunk = self.chunk(*chunk_position)
        if chunk is None:
            chunk = CellChunk(*chunk_position, self.chunk_size)
            self.chunks[chunk_position] = chunk
        chunk.add(row, col, cell)
    
    def delete(self, row, col):
        chunk_position = self.chunk_position(row, col)
        chunk = self.chunk(*chunk_position)
        if chunk:
            chunk.delete(row, col)
            if not chunk:
                del self.chunks[chunk_position]
            
    def select(self, row, col):
        chunk_position = self.chunk_position(row, col)
        chunk = self.chunk(*chunk_position)
        if chunk:
            return chunk.select(row, col)
            
    def chunk(self, chunk_row, chunk_col):
        return self.chunks.get((chunk_row, chunk_col))

    def __repr__(self):
        return str(self.chunks)
    
class Board:
    buffer: CellBuffer
    map: CellMap
    
    def __init__(self, cells: List[Cell]=None):
        self.buffer = CellBuffer()
        self.map = CellMap()
        
        if cells is None:
            cells = list()
        
        for cell in cells:
            self.buffer.put(cell, cell.index)
            self.map.add(*cell.position, cell)
        
        if cells:
            self.buffer.compress()
            