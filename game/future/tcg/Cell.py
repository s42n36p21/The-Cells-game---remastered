from typing import Tuple, Set, Iterable, List
from enum import IntEnum, auto, Enum
from abc import ABC, abstractmethod
from collections import Counter

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

Energy_SYSTEM = {Energy.NEUTRAL, Energy.OTHER}
Energy_PLAYER = {Energy.P1, Energy.P2, Energy.P3, Energy.P4, Energy.P5, Energy.P6, Energy.P7, Energy.P8}

class CellLink:
    _outgoing_links: List['CellModel']
    _incoming_links: List['CellModel']
    
    __slots__ = (
        '_outgoing_links',
        '_incoming_links'
    )
    
    def outgoing_links(self):
        return self._outgoing_links
    
    def incoming_links(self):
        return self._incoming_links
    
    def __init__(self):
        self._outgoing_links = list()
        self._incoming_links = list()
        
    def two_way_links(self):
        two_way_link = Counter(self.incoming_links) & Counter(self.outgoing_links)
        return two_way_link.elements()
        
class CellModel:
    index: int | None
    position: Tuple[int, int] | None
    owner: Energy
    power: int
    input_owner: Energy | None
    input_power: int
    links: CellLink

    __slots__ = (
        'index', 
        'position', 
        'owner', 
        'power', 
        'input_owner', 
        'input_power', 
        'links'
    )
    
    def __init__(self):
        self.index = None
        self.position = None
        self.owner = Energy.NEUTRAL
        self.power: int
        self.input_owner = None
        self.input_power = 0
        self.links = CellLink()    

class Cell:
    def __init__(self):
        self.model = CellModel()
        
    @property
    def index(self):
        return self.model.index
    
    @property
    def position(self):
        return self.model.position
    
    @index.setter
    def index(self, value):
        self.model.index = value
        
    @position.setter
    def position(self, value):
        self.model.position = value