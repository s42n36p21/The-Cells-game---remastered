import pyglet
pyglet.options['debug_gl'] = False
#pyglet.options.text_antialiasing = False
#pyglet.options.text_shaping = False
from Background import Background
from pyglet.window.key import KeyStateHandler, symbol_string
from pyglet.window.mouse import MouseStateHandler
from Camera import ControllableCamera as Camera
from Settings import Settings
from Actor import Player, MoveableActor as Actor
from Debuger import Debuger
from TCGCell import Energy, get_color
from TCGBoard import GameStateAttribute as GSA, GameBoard
from TCGtools import Cursor, HoverInspector
from TCGBoard import Modes
from Scene import Scene
from server import net, Protocol
import json
from widgets import Panel, PanelButton, PanelTextButton
from time import time
from TCGBoard import GameBoardStateEdit, GameBoardStateWating, GameBoardStateReaction
from TCGCell import TILE_SIZE

import random
with open('server.json', 'r', encoding='utf-8') as file:
    NET = json.load(file)
    
NAME = NET.get('name')
if NAME is None:
    NAME = 'Player' + str(random.randint(1, 99))

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
            self.master._master.set_fullscreen(True)
        elif key == pyglet.window.key.L:
            self.master._master.set_fullscreen(False)
        elif key == pyglet.window.key.R:
            game: GameBoard  = self.master.game
            s = game.save()
            
            game.build(s)
            self.master.game.restart(Modes.EXTENDED)   
        
        elif key == pyglet.window.key.SPACE:
            self.master.ready()
        
        elif key == pyglet.window.key.P:
            game: GameBoard  = self.master.game
            s = game.save(mod=Modes.CLASSIC)
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
            self.master.game.join(*get_players(settings.amount_players))
            
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
with open('3x3.json', 'r', encoding='utf-8') as file:
    SCHEME = json.load(file)
PLAYERS = get_players(settings.amount_players)


class TCGGame(Scene):
    def setup(self):
        #self.ui_batch = pyglet.graphics.Batch()

        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(self._master)
        self.back_ground = Background(settings.background, self._master)
        self.push_handlers(self.back_ground, self.camera)

        self.debuger = Debuger(self._master)
        self.debuger.active = 1

        self.game = game = GameBoard(self)
        game.build(SCHEME)
        game.join(*PLAYERS)
        game.restart(Modes.EXTENDED)
        self.camera._zoom = 2

        self.cursor = Cursor(self)
        self.hot_keys = HotKeys(self)
        self.hover = HoverInspector(self, self.game, self.batch)
        
        self.player = Player(name="Kell", speed=250, img='src/actor.png', batch=self.batch)
        self.push_handlers(self.player)

        self.player.attach_camera(self.camera)
        self.camera.update_projection()
 
        #self.panel = PanelTextButton('Кнопка', (30, 150,30), (30, 250,30), 20, 50, 50, 160, 100, (32,32,32, 128), (0,0,0, 128), 0.5, self.ui_batch)
        #self.panel.push_handlers(self) 
        
        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        self.push_handlers(self.key, self.mouse)
        self.flag = False
        
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.flag:
            return
        x, y = self.camera.screen_to_world(x, y)
        self.game.on_mouse_press(x, y, button, modifiers)
        
    #def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    #    x, y = self.camera.screen_to_world(x, y)
    #    self.game.on_mouse_press(x, y, buttons, modifiers)

    def on_widget_click(self, button):
        self.flag=True
        print("Нажата панельная кнопка")
    
    def on_mouse_release(self, *a):
        self.flag = False
    
    def debug(self):
        x ,y = self.camera.screen_to_world(self.mouse.data.get('x',0), self.mouse.data.get('y',0))
        game = f'Phase: {self.game.phase().name}\n' + '' if self.game.state.phase() != GSA.EDIT else self.game.state._editor.debug()
        return f'Cursor world position: x={x} y={y}\n' + game #+ f"Panel state = {type(self.panel.state)}"

    def draw(self):
        with self.camera:
            self.back_ground.draw()
            self.game.draw()
            
            self.batch.draw()
            
#        self.ui_batch.draw()
        self.debuger.draw()
        self.cursor.draw()

    def update(self, dt):
        
        self.player.update(dt)
        self.game.update(dt)
        #self.panel.update(dt)  
        
        if self.game.phase() == GSA.WATING:
            self.cursor.color = self.game.players.current()
            self.player.color = self.cursor.color
            

class TCGNetWorkGame(Scene):
    def setup(self):
        self.tps_count = 0
        
        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(self._master)
        self.back_ground = Background(settings.background, self._master)
        self.push_handlers(self.back_ground, self.camera)

        self.debuger = Debuger(self._master)
        self.debuger.active = 1

        self.game = game = GameBoard(self)
        self.camera._zoom = 2
        
        self.tasks = []

        self.cursor = Cursor(self)
        self.hot_keys = HotKeys(self)
        self.hover = HoverInspector(self, self.game, self.batch)

        self.player = Player(name=NAME, speed=250, img='src/actor.png', batch=self.batch)
        self.push_handlers(self.player)
        
        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        self.push_handlers(self.key, self.mouse)
        
        self.remote_players = {}

        HOST, PORT = NET.get('ip', 'localhost'), int(NET.get('port',12345))
        self.hits = []
        self.flag = False
        
        self.client = net.Client(HOST, PORT)
        self.client.push_handlers(self)
        message = {"code": Protocol.CODE.HELLO.value, "name": NAME, "password":NET.get('password')}
        message_bytes = json.dumps(message).encode()
        self.camera.update_projection()
        self.client.send(message_bytes)
        
        self.player.attach_camera(self.camera)
        
    def on_receive(self, connection, message):
        """Event for received messages."""
        
        try:
            message = json.loads(message.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Ошибка декодирования сообщения: {e}")
            return
        
        code = Protocol.CODE(message.get('code'))
        #print(message)
        match code:
            case Protocol.CODE.WELCOME:
                self.game.build(message.get('scheme'))
                self.game.restart(Modes.EXTENDED)
                rp = message.get('players')
                print(rp)
                def f():
                    for p in rp.values():
                        name = p.get('name')
                        position = p.get('position')
                        print(name, position)
                        self.remote_players.update({name: Actor(name=name, position=position, batch=self.batch, img='src/actor.png')})
                self.tasks.append(f)

            case Protocol.CODE.NEW_PLAYER:
                name = message.get('name')
                self.tasks.append(lambda: self.remote_players.update({name: Actor(name=name, batch=self.batch, img='src/actor.png')}))

            case Protocol.CODE.PLAYER_MOVE:
                name = message.get('name')
                pos = message.get('move')
                time_ = message.get('time')
                try:
                    self.remote_players[name].goto(*pos, time() - time_) 
                except Exception as e:
                    print(e)
                    
            case Protocol.CODE.START:
                print(message)
                pl = [p for p in message.get('players')]
                for n, p in pl:
                    if n == self.player.name:
                        self.player.color = get_color(Energy(p))
                        self.player.energy = Energy(p)
                        self.cursor.color = Energy(p)
                        continue
                    self.remote_players[n].color = get_color(Energy(p))
                self.game.join(*[Energy(p) for n, p in pl]) 
                self.game.restart(Modes.EXTENDED)
               
                
            case Protocol.CODE.PLAYER_HIT:
                print('этот пидор походил')
                self.hits.append(message.get('hit'))
            
    def on_disconnect(self, connection):
        """Event for disconnection. """

    def debug(self):
        x ,y = self.camera.screen_to_world(self.mouse.data.get('x',0), self.mouse.data.get('y',0))
        game = f'Phase: {self.game.phase().name}\n' + '' if self.game.state.phase() != GSA.EDIT else self.game.state._editor.debug()
        return f'Cursor world position: x={x} y={y}\n' + game + str(self.remote_players)

    def draw(self):
        with self.camera:
            self.back_ground.draw()
            self.game.draw()
            self.batch.draw()
            
            
        self.debuger.draw()
        self.cursor.draw()

    def ready(self):
        message = {"code": Protocol.CODE.READY.value, "name": self.player.name}
        message_bytes = json.dumps(message).encode()
        
        self.client.send(message_bytes)

    def on_mouse_press(self, x, y, button, modifiers):

        try:
            if self.player.energy != self.game.players.current():
                return
        except:
            return
        
        if self.flag or self.game.phase() != GSA.WATING:
            return
        
        x, y = self.camera.screen_to_world(x, y)
        
        row = y // TILE_SIZE
        col = x // TILE_SIZE
        
        
        cell = self.game.cells.get((row, col))
        if cell:
            if cell.model.hit(owner=self.player.energy):
                message = {"code": Protocol.CODE.HIT.value, "name": self.player.name, 'hit': (row, col)}
                message_bytes = json.dumps(message).encode()
                print('ПОХОДИЛ СУКА')
                self.client.send(message_bytes)
                self.flag = True

    def update(self, dt):
        self.tps_count = (self.tps_count + 1) % 3
        self.player.update(dt)
        self.game.update(dt)
        
        message = {"code": Protocol.CODE.MOVE.value, "name": self.player.name, 'move': self.player.position, 'time': time()}
        message_bytes = json.dumps(message).encode()
        
        if self.tps_count:
            self.client.send(message_bytes)
        
        for t in self.tasks:
            t()
        self.tasks.clear()
        
        for p in self.remote_players.values():
            p.update(dt)
        
        try:
            if self.player.energy != self.game.players.current():
                self.hover.view.hide()
        except:
            pass
        
        if self.hits and self.game.phase() == GSA.WATING:
            r,c = self.hits.pop(0)
            self.game.hit(r, c)
            self.flag = False

class Menu(Scene):
    def setup(self):
        self.batch = pyglet.graphics.Batch()

        #self.camera = Camera(self._master)
        self.back_ground = Background(settings.background, self._master)
        self.push_handlers(self.back_ground)

        w, h = self._master.size
        px, py = 340, 300
        bg = [(32,32,32, 128),(0,0,0, 128) ]
        self.ui = [
            PanelTextButton('Локальная игра', (50,50, 150), (50, 50, 250), 24, px, h-py/2-50, w-px*2, h/3-100, *bg, .5,batch=self.batch),
            PanelTextButton("Сетевая игра", (50,150, 50), (50, 250, 50), 24, px, h-py/2-h/3-50, w-px*2, h/3-100, *bg, .5,batch=self.batch),
            PanelTextButton("Выйти",(150,50, 50), (250, 50, 50), 24, px, h-py/2-h/3-h/3-50, w-px*2, h/3-100, *bg, .5,batch=self.batch ),
        ]

        for ui in self.ui:
            ui.push_handlers(self)
            self.push_handlers(ui)
    
    def draw(self):
        self.back_ground.draw()
        #   with self.camera:
        self.batch.draw()

    def on_widget_click(self, button):
        print("FFFFFF")
        cmd =  button.label.text
        match cmd:
            case 'Локальная игра':
                self._master._scene = TCGGame(self._master)
            case "Сетевая игра":
                self._master._scene = TCGNetWorkGame(self._master)
            case "Выйти":
                pyglet.app.exit()

    def update(self, dt):
        print("Запущена пидорская сцена")
        for ui in self.ui:
            ui.update(dt)


class Game(IGame):
    def setup(self):
        #self._scene = TCGGame(self)
        self._scene = Menu(self)

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

    