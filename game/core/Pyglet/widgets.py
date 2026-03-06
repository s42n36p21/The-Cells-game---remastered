import pyglet
from pyglet.shapes import Rectangle, Line
from core.Pyglet.util import MouseEvent, rgba
from typing import Literal
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
    
    def __init__(self, x, y, w, h, c, hc, ht, batch, custom_name=None, visible=True):
        self.view = pyglet.shapes.Rectangle(x, y, w, h, c, batch=batch)
        self.view.visible = visible
        self.custom_name = custom_name
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
                
    def __init__(self, text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch, custom_name=None, visible=True, anchor: Literal['left', 'center', 'right']='center'):
        if not custom_name:
            custom_name = text
        super().__init__(x, y, w, h, c, hc, ht, batch, custom_name, visible=visible)
        cx, cy = x + w/2, y + h/2
        self.label = pyglet.text.Label(text, cx,cy,0,anchor_x="center",anchor_y='center', font_size=text_size, color=text_color,batch=batch)
        self.label.visible=visible
        match anchor:
            case 'left':
                self.label.x = x+self.label.content_width/2+10
            case 'center':
                pass
            case 'right':
                self.label.x = x+w/2+self.label.content_width/2+10
        self.text_color, self.text_hover_color = rgba(text_color), rgba(text_hover_color)

    def visible(self, visibility: bool=True):
        self.label.visible=visibility
        self.view.visible=visibility

class DropDownMenu(PanelTextButton):
    """Виджет выпадающего меню"""
    def __init__(self,master, text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch, items, custom_name, anchor: Literal['left', 'center', 'right']='left'):
        super().__init__(text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch, custom_name=custom_name, anchor=anchor)
        self.label.anchor_x='center'
        self.toggled = False
        self.children = []
        self._master = master
        for num, item in enumerate(items):
            child = PanelTextButton(item, text_color, text_hover_color, text_size, x, y-h*(num+1), w, h, c, hc, ht, batch=batch, visible=False, custom_name=f'{custom_name}_{item}', anchor=anchor)
            self.children.append(
                child
            )
        

    def toggle(self):
        self.toggled = not self.toggled
        for children in self.children:
            children.visible(self.toggled)

    def update(self, dt):
        super().update(dt)
        for children in self.children:
            children.update(dt)

class CheckBox(PanelTextButton):
    """Виджет чекбокса. Адаптивная поебота"""
    def __init__(self, text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch, toggled, anchor: Literal['left', 'center', 'right']='left'):
        super().__init__(text, text_color, text_hover_color, text_size, x, y, w, h, c, hc, ht, batch, anchor=anchor)
        self.label.x += text_size*2
        self.draw_outline(self.label.x-self.label.content_width/2-text_size*1.3, self.label.y-text_size/1.5, text_size/2, (255,255,255), batch=batch)
        self.draw_checkmark(self.label.x-self.label.content_width/2-text_size*1.3, self.label.y-text_size/1.5, text_size/2, (255,255,255), batch=batch)
        self.toggled = toggled
        self.checkmark_line1.visible = toggled
        self.checkmark_line2.visible = toggled
            

    def toggle(self):
        self.toggled = not self.toggled
        self.checkmark_line1.visible = self.toggled
        self.checkmark_line2.visible = self.toggled

    def draw_outline(self, x, y, w, color, batch):
        self.line1 = Line(x, y, x+w*2, y, thickness=2, color=color, batch=batch)
        self.line2 = Line(x+w*2, y, x+w*2, y+w*2, thickness=2, color=color, batch=batch)
        self.line3 = Line(x, y+w*2, x+w*2, y+w*2, thickness=2, color=color, batch=batch)
        self.line4 = Line(x, y+w*2, x, y, thickness=2, color=color, batch=batch)

    def draw_checkmark(self, x, y, w, color, batch):
        self.checkmark_line1 = Line(x+w, y+w/2, x+w*1.6, y+w*1.6, thickness=2, color=color, batch=batch)
        self.checkmark_line2 = Line(x+w/1.8, y+w*1.2, x+w, y+w/2, thickness=2, color=color, batch=batch)