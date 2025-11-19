from pyglet.event import EventDispatcher


class foo:
    pass

class Scene(EventDispatcher):
    self_push_handlet = EventDispatcher.push_handlers     

    def __init__(self, master):
        super().__init__()
        self._master = master
        self._master.push_handlers(self)
        self._units = []
        self._tasks = None
        
        self.setup()

    def setup(self):
        pass

    def draw(self):
        return
    
    def update(self, dt):
        pass

    def push_handlers(self, *args, **kwargs):
        return self._master.push_handlers(*args, **kwargs)
    