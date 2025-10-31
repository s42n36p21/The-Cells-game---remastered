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
from Scene import Scene
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




settings = Settings()
settings.load()

class HotKeys:
    def __init__(self, master):
        self.master = master
        master.push_handlers(self)

    def on_key_press(self, key, mod):        
        tool = [pyglet.window.key._1, pyglet.window.key._2, pyglet.window.key._3, pyglet.window.key._4, pyglet.window.key._5, pyglet.window.key._6]
        par = [pyglet.window.key._7, pyglet.window.key._8,pyglet.window.key._9, pyglet.window.key._0]
        if key == pyglet.window.key.K:
            self.master.set_fullscreen(True)
        elif key == pyglet.window.key.L:
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
            self.master.back_ground = Background(settings.background, self.master._master)
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
                
        elif key == pyglet.window.key.F:
            if self.master.player.camera is None:
                self.master.player.attach_camera(self.master.camera)        
            else:
                self.master.player.detach_camera()
                
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
                from TCGEditor import CreateCell, DeleteCell, Link, UnLink, FlexLink, ClearLink

                self.master.game.state._editor.use([CreateCell, DeleteCell, Link, UnLink, FlexLink, ClearLink][tool.index(key)])
                #self.master.game.state._select = None
        
        elif key in par:
            
            from TCGEditor import ToolBox, TYPE_CELL
            p = par.index(key)
            t: ToolBox  = self.master.game.state._editor.tool_box
            match p:
                case 0:
                    t.AUTO_LINK = not t.AUTO_LINK                    
                
                case 1:
                    t.OUT_LINK = not t.OUT_LINK
                
                case 2:
                    t.IN_LINK = not t.IN_LINK
                
                case 3:
                    t.TYPE_CELL = (t.TYPE_CELL + 1) % len(TYPE_CELL)
                
         
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


class TCGGame(Scene):
    def setup(self):
        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        self.push_handlers(self.key, self.mouse)

        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(self._master)
        self.back_ground = Background(settings.background, self._master)
        self.push_handlers(self.back_ground, self.camera)

        self.debuger = Debuger(self._master)
        self.debuger.active = 1

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
        
       # with open('server.json', 'r', encoding='utf-8') as file:
       #     server = json.load(file)
            
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
        game = f'Phase: {self.game.phase().name}\n' + '' if self.game.state.phase() != GSA.EDIT else self.game.state._editor.debug()
        return f'Cursor world position: x={x} y={y}\n' + game

    def draw(self):
        with self.camera:
            self.back_ground.draw()
            self.game.draw()
            self.batch.draw()
        self.debuger.draw()
        self.cursor.draw()

    def update(self, dt):
        self.player.update(dt)
        self.game.update(dt)
        if self.game.phase() == GSA.WATING:
            self.cursor.color = self.game.players.current()
            self.player.color = self.cursor.color


class Game(IGame):
    def setup(self):
        self._scene = TCGGame(self)

    def on_draw(self):
        self.clear()
        self._scene.draw()

    def debug(self):
        return self._scene.debug()

    def loop(self, dt):
        self.update(dt)
        self._scene.update(dt)


if __name__ == "__main__":
    app = Game(tps=120, caption="The Cells game - remastered", resizable=True)
    pyglet.app.run(1/120)

    