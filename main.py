import pyglet
pyglet.options['debug_gl'] = False
from Background import Background
from pyglet.window.key import KeyStateHandler, symbol_string
from pyglet.window.mouse import MouseStateHandler
from Camera import ControllableCamera as Camera
from Settings import Settings
from Actor import Player
from Debuger import Debuger
from TCGCell import Energy, get_color
from TCGBoard import GameStateAttribute as GSA, GameBoard
from TCGtools import Cursor, HoverInspector
from TCGBoard import Modes
import json

from TCGBoard import GameBoardStateEdit, GameBoardStateWating, GameBoardStateReaction

class IGame(pyglet.window.Window):
    def __init__(self, *args, tps=60, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_event_type('on_update')

        self.setup()
        pyglet.clock.schedule_interval(self.loop, 1/tps)

    def update(self, dt):
        self.dispatch_event('on_update', dt)

    def setup(self):
        pass

    def loop(self, dt):
        pass


class Scene(pyglet.event.EventDispatcher):
    def __init__(self, master):
        super().__init__()
        self._master = master
        
        self.setup()

    def setup(self):
        pass

settings = Settings()
settings.load()

class HotKeys:
    def __init__(self, master):
        self.master = master
        master.push_handlers(self)

    def on_key_press(self, key, mod):        
        tool = [pyglet.window.key._1, pyglet.window.key._2, pyglet.window.key._3]
        if key == pyglet.window.key._9:
            self.master.set_fullscreen(True)
        elif key == pyglet.window.key._0:
            self.master.set_fullscreen(False)
        elif key == pyglet.window.key.R:
            game: GameBoard  = self.master.game
            s = game.save()
            
            game.build(s)
            self.master.game.restart(Modes.CLASSIC)   
        
        elif key == pyglet.window.key.P:
            game: GameBoard  = self.master.game
            s = game.save()
            from time import time
            with open(f'{time()}.json', 'w', encoding='utf-8') as file:
                json.dump(s, file, ensure_ascii=False, indent=4)
                     
        elif key == pyglet.window.key.B:
            bg = [f'b{i}' for i in range(1, 9)]
            idx = bg.index(settings.background) + 1
            if idx >= 8:
                idx = 0
            settings.background = bg[idx]
            settings.save()
            self.master.back_ground = Background(settings.background, self.master)
            self.master.push_handlers(self.master.back_ground)
        elif key == pyglet.window.key.V:
            if settings.sensor_type:
                settings.sensor_type = 0
            else:
                settings.sensor_type = 1
            settings.save()

            for cell in self.master.game.cells.values():
                cell.view.render_sensor()
                cell.view.update()
                
        elif key == pyglet.window.key.C:
            if settings.chain_reaction:
                settings.chain_reaction = False
            else:
                settings.chain_reaction = True
            settings.save()
        
        elif key == pyglet.window.key.X:
            if settings.sound_effects:
                settings.sound_effects = False
            else:
                settings.sound_effects = True
                
            settings.save()
            
        elif key == pyglet.window.key.E:
            
            if self.master.game.phase() == GSA.EDIT:
                self.master.game.state = GameBoardStateWating(self.master.game)
            elif self.master.game.phase() == GSA.WATING:
                self.master.game.state = GameBoardStateEdit(self.master.game)

        elif key in tool:
            if self.master.game.phase() == GSA.EDIT:
                from TCGBoard import Tools
                self.master.game.state._tool = [Tools.CREATE, Tools.LINK, Tools.DELETE][tool.index(key)]
                self.master.game.state._select = None
                
        elif key == pyglet.window.key._4:
            if self.master.game.phase() == GSA.EDIT:
                self.master.game.state._type = (self.master.game.state._type + 1) % len(self.master.game.state.CELL_TYPES)

        elif key == pyglet.window.key.Z:
            if self.master.game.phase() == GSA.WATING:
                c = self.master.game.players.current()   
                self.master.game.players.kick(c)

        elif key == pyglet.window.key.Q:
            
            self.master.game.players.players.clear()
            self.master.game.join(*get_players(3))
            
        elif key == pyglet.window.key.Y:
            self.master.game.state = GameBoardStateReaction(self.master.game)

def create_simple_scheme(r, c):
    scheme = ''
    mr, mc = r//2, c//2
    for row in range(-mr, r-mr):
        for col in range(-mc, c-mc):
            scheme += f"{row} {col} "
    return scheme

def get_players(count):
    from TCGCell import Energy
    from random import shuffle
    p = [Energy.P1,
            Energy.P2,
            Energy.P3,
            Energy.P4,
            Energy.P5,
            Energy.P6,
            Energy.P7,
            Energy.P8,
            ]
    shuffle(p)
    return p[:count]


SCHEME = create_simple_scheme(3, 3)
with open('scheme.json', 'r', encoding='utf-8') as file:
    SCHEME = json.load(file)
PLAYERS = get_players(2)



class Game(IGame):
    def setup(self):
        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        self.push_handlers(self.key, self.mouse)

        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(self)
        self.back_ground = Background(settings.background, self)
        self.push_handlers(self.back_ground, self.camera)

        self.debuger = Debuger(self)
        self.debuger.active = True

        self.game = game = GameBoard(self)
        game.build(SCHEME)
        game.join(*PLAYERS)
        game.restart(Modes.CLASSIC)
        self.camera._zoom = 2

        self.cursor = Cursor(self)
        self.hot_keys = HotKeys(self)
        self.hover = HoverInspector(self, self.game, self.batch)

        self.player = Player(name="Kell", speed=250, img='src/actor.png', batch=self.batch)
        self.push_handlers(self.player)

        self.player.attach_camera(self.camera)
        
        with open('server.json', 'r', encoding='utf-8') as file:
            server = json.load(file)
            
       # self.network = NetworkManager(self)
       # self.network.connect(host=server.get("ip"),
       #                      port=server.get("port"),
       #                      player_name=server.get("name"))
       # 
        
    def on_mouse_press(self, x, y, button, modifiers):
        x, y = self.camera.screen_to_world(x, y)
        self.game.on_mouse_press(x, y, button, modifiers)
        
    #def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    #    x, y = self.camera.screen_to_world(x, y)
    #    self.game.on_mouse_press(x, y, buttons, modifiers)

    def debug(self):
        x ,y = self.camera.screen_to_world(self.mouse.data.get('x',0), self.mouse.data.get('y',0))
        game = f'Phase: {self.game.phase().name}\n' + (f'Tool: {self.game.state._tool.name}\nSelect: {self.game.state._select}\nCellType: {self.game.state._type}' if self.game.phase() == GSA.EDIT else '')
        return f'Cursor world position: x={x} y={y}\n' + game

    def on_draw(self):
        self.clear()
        with self.camera:
            self.back_ground.draw()
            self.game.draw()
            self.batch.draw()
        self.debuger.draw()
        self.cursor.draw()

    def loop(self, dt):
        self.update(dt)
        self.player.update(dt)
        self.game.update(dt)
        if self.game.phase() == GSA.WATING:
            self.cursor.color = self.game.players.current()
            self.player.color = self.cursor.color



if __name__ == "__main__":
    app = Game(tps=60, caption="The Cells game - remastered", resizable=True)
    pyglet.app.run()

    