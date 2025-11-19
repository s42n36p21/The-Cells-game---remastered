from pyglet.event import EventDispatcher

class MouseEvent(EventDispatcher):
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.dispatch_event('on_mouse_move', x, y, dx, dy)
    
    def on_mouse_motion(self, x, y, dx, dy):
        self.dispatch_event('on_mouse_move', x, y, dx, dy)
        
    def on_mouse_enter(self, x, y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
        
    def on_mouse_leave(self, x, y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_press(self, x, y, button, modifiers):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_release(self, x, y, button, modifiers):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_move(self, x, y, dx=0, dy=0):
        """on_mouse_motion OR on_mouse_drag"""
        
MouseEvent.register_event_type('on_mouse_move')

    
def rgba(color):
    r, g, b, *a = color
    return r, g, b, a[0] if a else 255