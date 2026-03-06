import pyglet
from core.Pyglet.Background import Background
from core.Settings import Settings
from core.Pyglet.widgets import CheckBox, DropDownMenu
settings = Settings()
settings.load()

class foo:
    pass

class Scene(pyglet.event.EventDispatcher):
    self_push_handlet = pyglet.event.EventDispatcher.push_handlers     

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
    
class SettingsMenu(Scene):
    def setup(self):
        self.batch = pyglet.graphics.Batch()

        self.back_ground = Background(settings.background, self._master)
        self.push_handlers(self.back_ground)

        w, h = self._master.size
        px, py = 340, 300
        bg = [(32,32,32, 128),(0,0,0, 128) ]
        dd_bg = [(255, 255, 255, 255), (200, 200, 200, 255)]
        self.ui = [
            DropDownMenu(self, "Меню", (100,100, 100), (50, 50, 50), 24, px, h-py/2, w-px*2, h/3-125, *dd_bg, .5,batch=self.batch, items=['1', '2', '3'], custom_name='Menu', anchor='left'),
            CheckBox("Чекбокс",(200,200, 200), (250, 250, 250), 24, px, h-py/2-h/4, w-px*2, h/3-125, *bg, .5,batch=self.batch, toggled=False, anchor='left'),
        ]
        for ui in self.ui:
            ui.push_handlers(self)
            self.push_handlers(ui)

    def draw(self):
        self.back_ground.draw()
        self.batch.draw()

    def update(self, dt):
        for ui in self.ui:
            ui.update(dt)

    def on_widget_click(self, button):
        print(button.custom_name)
        cmd =  button.custom_name
        match cmd:
            case "Menu":
                button.toggle()
                if button.toggled:
                    for child in button.children:
                        child.push_handlers(self)
                        self.push_handlers(child)
                else:
                    for child in button.children:
                        child.remove_handlers(self)
                        self._master.remove_handlers(child)
            case "Чекбокс":
                button.toggle()