import pyglet
from pyglet.shapes import Rectangle
from util import MouseEvent, rgba
from pyglet.math import Vec4


def lerp_color(start, stop, amount):
    start = Vec4(*start)
    stop = Vec4(*stop)
    return map(int, start.lerp(stop, amount))

class State:
    def __init__(self, master):
        self.master = master
        
    def skip(self, *args, **kwargs):
        return 

class BaseWidget(pyglet.event.EventDispatcher):
    pass

class Panel(MouseEvent, BaseWidget):
    class Hover(State):        
        def on_mouse_move(self, x, y, dx, dy):
            if (x, y) not in self.master.view:
                self.master.state = self.master.Default(self.master)
                self.master.state.timer = self.timer
                
        def update(self, dt):
            self.timer += dt
            if self.timer > self.master.hover_time:
                self.master.view.color = self.master.hover_color
                self.timer = self.master.hover_time
                self.update = self.skip
            else:
                self.master.view.color = lerp_color(self.master.color,self.master.hover_color,self.timer / self.master.hover_time)
                
    class Default(State):
        def on_mouse_move(self, x, y, dx, dy):
            if (x, y) in self.master.view:
                self.master.state = self.master.Hover(self.master)
                self.master.state.timer = self.timer
                
        def update(self, dt):
            self.timer -= dt
            if self.timer < 0:
                self.master.view.color = self.master.color
                self.timer = 0
                self.update = self.skip
            else:
                self.master.view.color = lerp_color(self.master.color,self.master.hover_color,self.timer / self.master.hover_time)
    
    def __init__(self, x, y, w, h, c, hc, ht, batch):
        self.view = pyglet.shapes.Rectangle(x, y, w, h, c, batch=batch)
        self.state = self.Default(self)
        self.state.timer = 0
        self.color = rgba(c)
        self.hover_color = rgba(hc)
        self.hover_time = ht
        
    def update(self, dt):
        self.state.update(dt)
        
    def on_mouse_move(self, x, y, dx=0, dy=0):
        self.state.on_mouse_move(x,y,dx,dy)
        
class PanelButton(Panel):
    def on_mouse_press(self, x, y, button, modifiers):
        if (x, y) in self.view:
            self.dispatch_event('on_widget_click', self)
            return pyglet.event.EVENT_HANDLED

PanelButton.register_event_type('on_widget_click')

class PanelTextButton(PanelButton):
    class Hover(Panel.Hover):        
        def update(self, dt):
            self.timer += dt
            if self.timer > self.master.hover_time:
                self.master.view.color = self.master.hover_color
                self.master.label.color = self.master.text_hover_color
                self.timer = self.master.hover_time
                self.update = self.skip
            else:
                self.master.view.color = lerp_color(self.master.color,self.master.hover_color,self.timer / self.master.hover_time)
                self.master.label.color = lerp_color(self.master.text_color,self.master.text_hover_color,self.timer / self.master.hover_time)
                
    class Default(Panel.Default):
        def update(self, dt):
            self.timer -= dt
            if self.timer < 0:
                self.master.view.color = self.master.color
                self.master.label.color = self.master.text_color
                self.timer = 0
                self.update = self.skip
            else:
                self.master.view.color = lerp_color(self.master.color,self.master.hover_color,self.timer / self.master.hover_time)
                self.master.label.color = lerp_color(self.master.text_color,self.master.text_hover_color,self.timer / self.master.hover_time)
                
    def __init__(self, text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch):
        super().__init__(x, y, w, h, c, hc, ht, batch)
        cx, cy = x + w/2, y + h/2
        self.label = pyglet.text.Label(text, cx,cy,0,anchor_x="center",anchor_y='center', font_size=text_size, color=text_color,batch=batch)
        self.text_color, self.text_hover_color = rgba(text_color), rgba(text_hover_color)
        