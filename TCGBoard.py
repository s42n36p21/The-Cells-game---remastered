from TCGCell import Cell, get_color, Energy, TILE_SIZE, get_side
import pyglet
from Settings import Settings
from random import shuffle
from enum import Enum, auto
from typing import Literal
from pyglet.math import Vec2
from time import time
from itertools import cycle


settings = Settings()
settings.load()

class SoundEffects:
    SoundName = Literal['reaction', 'click', 'warn', 'start', 'game_over']
    
    sounds = {
        'reaction': pyglet.media.load('src/sounds/boom.ogg', streaming=False),
        'click': pyglet.media.load('src/sounds/button.ogg', streaming=False),
        'warn': pyglet.media.load('src/sounds/error.ogg', streaming=False),
        'start': pyglet.media.load('src/sounds/start.ogg', streaming=False),
        'game_over': pyglet.media.load('src/sounds/win.ogg', streaming=False)
    }
    
    sound_enabled = settings.sound_effects
    
    @classmethod
    def play(cls, sound_name: SoundName):
        """Воспроизвести звук по имени"""
        if settings.sound_effects and sound_name in cls.sounds:
            cls.sounds[sound_name].play()
    

class PlayersNode:
    value: Energy
    next: 'PlayersNode'
    immunity: int
    def __init__(self, player):
        self.value = player
        self.next = None
        self.immunity = 1
        
class Players:
    SHUFFLE = False
    def __init__(self, players=None):
        
        self.players = players or list()
    
    def join(self, *args):
        self.players.extend(args)

    def leave(self, *args):
        for p in args:
            self.players.remove(p)
    
    def restart(self):
        if len(self.players) < 2:
            raise ValueError("Игроков должно быть минимум 2")
        
        queue = self.players.copy()
        if self.SHUFFLE:
            shuffle(queue)
        
        self.length = len(queue)
        head = PlayersNode(queue.pop(0))
        prev = head
        while queue:
            current = PlayersNode(queue.pop(0))
            prev.next = current
            prev = current
        prev.next = head
        
        self.ptr = head
        

    def next(self):
        self.ptr.immunity = 0
        self.ptr = self.ptr.next

    def current(self):
        return self.ptr.value
    
    def queue(self):
        lst = []
        
        head = self.ptr
        prev = head
        current = head.next
        
        while True:
            lst.append(current.value)
            prev = current
            current = current.next
            if current is head.next:
                lst.insert(0, lst.pop())
                return lst
        
    
    def kick(self, player):
        if self.length < 2:
            return
        
        head = self.ptr
        prev = head
        current = head.next

        while current.value != player:
            prev = current
            current = current.next
            if current is head.next:  # Элемент не найден
                return
        if current.immunity:
            return
        prev.next = current.next
        if current is head:
            self.ptr = head.next
        self.length -= 1
                
    def has_winner(self):
        return self.length < 2
    
    def winner(self):
        return self.ptr.value
    
    def __repr__(self):
        return str(self.queue())

class Modes(Enum):
    OLD = auto()
    CLASSIC = auto()
    RECHARGED = auto()
    DOUBLING = auto()
    HIDDEN = auto()
    EXTENDED = auto()
    
class GameStateAttribute(Enum):
    DEFAULT = auto()
    READY = auto()
    WATING = auto()
    REACTION = auto()
    FINISH = auto()
    EDIT = auto()
    BUILD = auto()
    
class Saver:
    def __init__(self, cells):
        self.cells = cells
        
    def save_classic(self):
        cell_buffer = []
        cells = []
        links = []
        index = 0
        for pos, cell in self.cells.items():
            cell.model.mark = index
            cell_buffer.append(cell.model)
            row, col = pos
            cells.append(f'{row} {col}')
            index += 1
        index = 0
        for c in cell_buffer:
            out = {i.mark for i in c.outgoing_links}
            in_ = {i.mark for i in c.incoming_links}
            two = out & in_
            out -= two
            in_ -= two
            
            for ol in out:
                if ol < index:
                    continue
                links.append(f'{index} {ol} 0')
            for il in in_:
                if il< index:
                    continue
                links.append(f'{index} {il} 2')
            for tl in two:
                if tl < index:
                    continue
                links.append(f'{index} {tl} 1')
            index += 1
        
        
        
        return  {
    "meta": {
        "version": "0.0.1",
        "name": "",
        "creation_time": 0,
        "description": "",
        "author": None,
        "modes": [Modes.CLASSIC.value],
        "property": None
    },
    "scheme": {
        "scanfmt": "ROW COL \\ CI0 CI1 TL",
        "cells": ' '.join(cells),
        "links": ' '.join(links)
    }
}
from TCGtools import link_cell
class Builder:
    def __init__(self, scheme, batch):
        self.scheme = scheme
        self.batch = batch
        self.build_task = None
        self.product = dict()
    
    def get_product(self):
        return self.product
    
    def build_classic(self):
        self.build_task = self._build_classic()
    
    def _build_classic(self):
        cells_d = dict()
        scheme = self.scheme.get("scheme")
        scanfmt: str = scheme.get("scanfmt")
        cells = iter(scheme.get("cells").split())
        links = iter(scheme.get("links").split())
        cellf, linkf = scanfmt.lower().split('\\')
        cellf = cellf.split()
        linkf = linkf.split()
        
        cell_buffer = []
        
        
        for args in zip(*([cells]*len(cellf))):
            d = self._read_scan_str(cellf, args)
            row, col = int(d.get('row')), int(d.get('col'))
            cell = Cell((row, col), self.batch)
            cell_buffer.append(cell)
            yield
            
        for args in zip(*([links]*len(linkf))):
            d = self._read_scan_str(linkf, args)
            c1, c2, tl = int(d.get('ci0')), int(d.get('ci1')), int(d.get('tl'))
            a, b = cell_buffer[c1], cell_buffer[c2]
            link_cell(a, b, type=tl)
            yield
          
        for cell in cell_buffer:
            cell: Cell
            cell.view.render_sides()
            cell.view.render_sensor()
            cell.view.update()
            cells_d[cell.model.position] = cell
            yield

        self.product = cells_d
        
    @staticmethod
    def _read_scan_str(fmt, args):
        return dict(zip(fmt, args))
    
    def build_old(self):
        self.build_task = self._build_old()
    
    def _build_old(self):
        cells = dict()
        coords = self.scheme.split()
        points = iter(coords)
        for position in zip(points, points):
            position = tuple(map(int, position))
            if position in cells:
                continue
            cell = Cell(position, self.batch)
            cells[position] = cell
            yield
        
        meet = list(cells.values())
        from itertools import combinations
        for a, b in combinations(meet, 2):
            a: Cell
            b: Cell
            if get_side(a.model, b.model):
                a.model.link(b.model)
                b.model.link(a.model)
            yield
        
        for cell in cells.values():
            cell: Cell
            cell.view.render_sides()
            cell.view.render_sensor()
            cell.view.update()
            yield
        
        self.product = cells
    
    def build_recharged(self):
        self.build_task = self._build_recharged()
    
    def _build_recharged(self):
        for _ in self._build_old():
            yield
        
        cells = self.get_product()
        from random import randint
        for cell in cells.values():
            cell: Cell
            cell.model.power = max(0, randint(0, cell.model.lim_power()-1))
            cell.view.update()
            yield
    
    def build(self, work_time):
        now = time()
        while work_time > (time() - now):
            
            try:
                next(self.build_task)
            except StopIteration:
                return True
        
    
class Particle:
    def __init__(self, start, stop, color, batch):
        self.start = Vec2(*start)
        self.stop = Vec2(*stop)
        self.model = pyglet.shapes.Circle(*self.start,4,color=color,batch=batch)
    
    def update(self, v):
        self.model.x, self.model.y = self.start.lerp(self.stop, v)
    
    def destroy(self):
        self.model.delete()
    
class ParticleManager:
    def __init__(self):
        self.contain = []
        
    def progress(self, v):
        for p in self.contain:
            p.update(v)
    
    def add(self, part):
        self.contain.append(part)
        
    def clear(self):
        for p in self.contain:
            p.destroy()
        self.contain.clear()    
    
    
class GameBoardState:
    def __init__(self, master: 'GameBoard'):
        self.master = master
        
    def hit(self, row, col, player=None):
        return
    
    def hover(self, row, col, player=None):
        cell = self.master.cells.get((row, col))
        
        if cell:
            cell: Cell
            if cell.model.hit(owner=self.master.players.current()):
                return cell
    
    def warn(self):
        SoundEffects.play('warn')
    
    def game_over(self):
        SoundEffects.play('game_over')
        self.switch_state(GameBoardStateFinish)

    def phase(self):
        return GameStateAttribute.DEFAULT
    
    def cells(self):
        return self.master.cells.values() 
    
    def on_mouse_press(self, x, y, button, modifiers):
        if button != pyglet.window.mouse.LEFT:
            return
        
        row = y // TILE_SIZE
        col = x // TILE_SIZE

        return self.hit(row, col, None)
        
    def on_mouse_motion(self, x, y, dx, dy):
        row = y // TILE_SIZE
        col = x // TILE_SIZE

        return self.hover(row, col)
    
    def check(self):
        return
    
    def switch_state(self, state):
        self.master.state = state(self.master)

    def kick(self, player):
        return
    
    def draw(self):
        self.master.batch.draw()
    
    def update(self, dt):
        return

class GameBoardStateBuild(GameBoardState):
    def phase(self):
        return GameStateAttribute.BUILD
    
    def update(self, dt):
        if not self.master.builder.build(1/120):
            return
        
        self.master.cells = self.master.builder.get_product()
        self.switch_state(GameBoardStateWating)
        self.master.players.restart()
        SoundEffects.play('start')
    
    def draw(self):
        return
    
class GameBoardStateWating(GameBoardState):
    def phase(self):
        return GameStateAttribute.WATING
    
    def hit(self, row, col, player=None):
        cell: Cell = self.hover(row, col, player)
        if not cell:
            return
        cell = self.master.cells[(row, col)]
        if cell.model.hit(owner=self.master.players.current()):
            cell.model.charge(self.master.players.current())
            cell.model.fill()
            cell.view.update()
            SoundEffects.play('click')
            if cell.model.is_full():
                self.switch_state(GameBoardStateReaction)
            else:
                self.master.players.next()
        else:
            self.master.warn()
        
class GameBoardStateReaction(GameBoardState):
    DELAY = 0.5
    
    def __init__(self, master):
        super().__init__(master)
        
        self.time = 0
        self.combo = 1
        self.batch = pyglet.graphics.Batch()
        self.particles = ParticleManager()
        if settings.chain_reaction:
            self.particle_add()
            SoundEffects.play('reaction')

    def phase(self):
        return GameStateAttribute.REACTION

    def particle_add(self):
        full = filter(lambda cell : cell.model.is_full(), self.cells())
        for fc in full:
            fc: Cell
            row, col = fc.model.position
            start = (col * TILE_SIZE + TILE_SIZE / 2,
                     row * TILE_SIZE + TILE_SIZE / 2)
            for link in fc.model.outgoing_links:
                link: Cell
                row, col = link.position
                stop = (col * TILE_SIZE + TILE_SIZE / 2,
                        row * TILE_SIZE + TILE_SIZE / 2)
    
                self.particles.add(
                    Particle(start, stop, get_color(fc.model.owner), self.batch)
                )

    def draw(self):
        super().draw()
        self.batch.draw()
    
    def update(self, dt):
        self.time += dt
        if not settings.chain_reaction or (self.time >= self.DELAY):
            self.particles.clear()
            for cell in self.cells():
                cell: Cell
                cell.model.reaction()
            f_full = False
            lose = set(self.master.players.queue())
            for cell in self.cells():
                cell: Cell
                cell.model.fill()
                cell.view.update()
                f_full = f_full or cell.model.is_full()
                if cell.model.is_considered():
                    lose.discard(cell.model.owner)
            for loser in lose:
                self.master.players.kick(loser)
            if self.master.players.has_winner():
                self.game_over()
                return
            if f_full:
                self.combo += 1
                if settings.chain_reaction:
                    self.particle_add()
                    SoundEffects.play('reaction')
                self.time = 0
            else:
                prev = self.master.players.current()
                self.master.players.next()
                if prev in lose:
                    self.master.players.kick(loser)
                self.switch_state(GameBoardStateWating)
        else:
            progress = self.time / self.DELAY
            self.particles.progress(progress)
    
class GameBoardStateFinish(GameBoardState):
    def phase(self):
        return GameStateAttribute.FINISH
    
    def hover(self, row, col, player=None):
        return 
    
class Tools(Enum):
    CREATE = auto()
    LINK = auto()
    DELETE = auto()

class GameBoardStateEdit(GameBoardState):
    from TCGCell import CloseCell, VoidCell
    CELL_TYPES = [Cell, CloseCell, VoidCell]
    def __init__(self, master):
        super().__init__(master)

        self._tool = Tools.CREATE
        self._select = None
        self._type = 0

    def phase(self):
        return GameStateAttribute.EDIT
    
    def hit(self, row, col, player=None):
        cell: Cell =  self.master.cells.get((row, col))
        row, col = map(int, [row, col])
        if cell is not None:
            match self._tool:
                case Tools.DELETE:
                    out = [c for out_cell in cell.model.incoming_links if (c:=self.master.cells.get(out_cell.position)) is not None]
                    cell.delete()
                    self.master.cells.pop((row, col))
                    for c in out:
                        c: Cell
                        c.view.render_sides()
                        c.view.render_sensor()
                        c.view.update()
                case Tools.LINK:
                    if self._select is None:
                        self._select = cell
                    elif 1 or get_side(self._select.model, cell.model):
                        
                        self._select.model.link(cell.model)
                        self._select.view.render_sides()
                        self._select.view.render_sensor()
                        self._select.view.update()
                        self._select = None
        else:
            match self._tool:
                case Tools.CREATE:
                    new = self.CELL_TYPES[self._type]((row, col), self.master.batch)
                    new.view.render_sides()
                    new.view.render_sensor()
                    new.view.update()
                    self.master.cells[(row, col)] = new

class GameBoardStateReady(GameBoardState):

    def phase(self):
        return GameStateAttribute.READY
    
class GameBoard:
    def __init__(self, scene):
        self.scene = scene
        self.cells = dict()
        self.batch = pyglet.graphics.Batch()
        self.state = GameBoardState(self)
        self.players = Players()
    
    def join(self, *players):
        self.players.join(*players)

    def leave(self, *players):
        self.players.leave(*players)
    
    def build(self, scheme):
        self.builder = Builder(scheme, self.batch)
    
    def save(self):
        d = Saver(self.cells).save_classic()
        print(d)
        return d
    
    def restart(self, mod=Modes.OLD, ext=None): 
        for cell in self.cells.values():
            cell:Cell
            cell.delete()
        self.cells.clear()
        
        match mod:
            case Modes.CLASSIC:
                self.builder.build_classic()
            case Modes.OLD:
                self.builder.build_old()
            case Modes.RECHARGED:
                self.builder.build_recharged()
            case _:
                raise ValueError("Неизвестный режим игры")
        self.state = GameBoardStateBuild(self)        
        
    def draw(self):
        self.state.draw()
        
    def hit(self, row, col, player=None):
        return self.state.hit(row, col, player)
    
    def hover(self, row, col, player=None):
        return self.state.hover(row, col, player)
    
    def warn(self):
        return self.state.warn()
    
    def game_over(self):
        return self.state.game_over()

    def phase(self):
        return self.state.phase() 
    
    def on_mouse_press(self, x, y, button, modifiers):
        return self.state.on_mouse_press(x, y, button, modifiers)
        
    def on_mouse_motion(self, x, y, dx, dy):
        return self.state.on_mouse_motion(x, y, dx, dy)
    
    def check(self):
        return self.state.check()
    
    def update(self, dt):
        return self.state.update(dt)
    
    def __repr__(self):
        pass
    
from pyglet.event import EventDispatcher
class EventableGameBoard(GameBoard, EventDispatcher):
    pass

EVENTS = [
    'build',
    'game_over',

]
for event in EVENTS:
    EventableGameBoard.register_event_type('on_board_' + event)   
    
