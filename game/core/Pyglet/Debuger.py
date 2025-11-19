import pyglet
from pyglet.window.key import KeyStateHandler, symbol_string
from pyglet.window.mouse import MouseStateHandler, buttons_string
from pyglet.window import FPSDisplay
from time import time

class Debuger:
    PAD = 30

    def __init__(self, window, batch=None):
        self.active = True
        self.window = window
        self.key = KeyStateHandler()
        self.mouse = MouseStateHandler()
        self.fps = FPSDisplay(window)
        window.push_handlers(self.key, self.mouse, self)
        self.run_time = time()

        self.batch = batch or pyglet.graphics.Batch()
        self.lable = pyglet.text.Label('', self.PAD, self.window.height - self.PAD,
                    width= self.window.width, height=self.window.height,
                    anchor_y='top', batch=self.batch, font_size=16, multiline=True,)

    def on_resize(self, x, y):
        self.lable.width, self.lable.height = self.window.size
        self.lable.y = y - self.PAD

    def draw(self):
        if not self.active:
            return
        self.batch.draw()

    def on_update(self, dt):
        if not self.active:
            return
        run = time()-self.run_time
        if run < 60:
            time_str = f'{run:.2f}s'
        elif run < 3600:
            time_str = f'{run/60:.1f}m'
        else:
            time_str = f'{run/3600:.1f}h'
        fps = self.fps.label.text
        mouse = self.mouse.data
        x, y = mouse.get('x'), mouse.get('y')
        mk = str([buttons_string(key) for key, pressed in mouse.items() if key not in list('xy') and pressed])[1:-1]
        kk = str([symbol_string(key) for key, pressed in self.key.data.items() if pressed])[1:-1]

        self.lable.text = f'FPS: {fps}\nRun time: {time_str}\nMouse: x={x} y={y} buttons={{{mk}}}\nKeys: {{{kk}}}\n' + self.window.debug()

    