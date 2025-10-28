import pyglet
from pyglet.math import Mat4

class Camera:
    def __init__(self, window, x=0, y=0, zoom=1.0):
        self._window = window
        self._x = x
        self._y = y
        self._zoom = zoom
        self.update_projection()
        
    def begin(self):
        self.origin_projection = self._window.projection
        self._window.projection = self.current_projection

    def end(self):
        self._window.projection = self.origin_projection

    @property
    def position(self):
        return self._x, self._y

    @property
    def zoom(self):
        return self._zoom

    @property
    def center(self):
        width, height = self._window.size
        return (self._x, self._y)

    def update_projection(self):
        x, y = self.position
        width, height = self._window.size
        
        # Масштабируем размер области просмотра
        scaled_width = width / self._zoom
        scaled_height = height / self._zoom
        
        # Центрируем область просмотра вокруг текущей позиции камеры
        left = x - scaled_width / 2
        right = x + scaled_width / 2
        bottom = y - scaled_height / 2
        top = y + scaled_height / 2

        self.current_projection = Mat4.orthogonal_projection(
            left=left, 
            right=right,
            bottom=bottom,
            top=top,
            z_near=-8192,
            z_far=8192
        )

    def move(self, dx, dy):
        self._x += dx / self._zoom
        self._y += dy / self._zoom
        self.update_projection()

    def zoom_to(self, zoom, focus_x=None, focus_y=None):
        """Установить зум с возможностью фокусировки на точке"""
        old_zoom = self._zoom
        
        if focus_x is not None and focus_y is not None:
            # Сохраняем мировые координаты точки фокуса
            world_x, world_y = self.screen_to_world(focus_x, focus_y)
        
        self._zoom = max(1, min(4, zoom))  # Ограничиваем зум
        
        if focus_x is not None and focus_y is not None:
            # Возвращаем точку фокуса в те же экранные координаты
            new_world_x, new_world_y = self.screen_to_world(focus_x, focus_y)
            self.move((world_x - new_world_x) * self._zoom, (world_y - new_world_y) * self._zoom)
        else:
            self.update_projection()

    def zoom_in(self, factor=1.1, focus_x=None, focus_y=None):
        """Увеличить зум"""
        self.zoom_to(self._zoom * factor, focus_x, focus_y)

    def zoom_out(self, factor=1.1, focus_x=None, focus_y=None):
        """Уменьшить зум"""
        self.zoom_to(self._zoom / factor, focus_x, focus_y)

    def focus(self, x, y):
        """Сфокусироваться на указанной мировой координате"""
        if self._x == x and self._y == y:
            return
        self._x = x
        self._y = y
        self.update_projection()

    def screen_to_world(self, screen_x, screen_y):
        """Преобразовать экранные координаты в мировые"""
        width, height = self._window.size
        scaled_width = width / self._zoom
        scaled_height = height / self._zoom
        
        world_x = self._x - scaled_width / 2 + screen_x / self._zoom
        world_y = self._y - scaled_height / 2 + (screen_y) / self._zoom
        
        return world_x, world_y

    def world_to_screen(self, world_x, world_y):
        """Преобразовать мировые координаты в экранные"""
        width, height = self._window.size
        scaled_width = width / self._zoom
        scaled_height = height / self._zoom
        
        screen_x = (world_x - (self._x - scaled_width / 2)) * self._zoom
        screen_y = height - (world_y - (self._y - scaled_height / 2)) * self._zoom
        
        return screen_x, screen_y

    def __enter__(self):
        self.begin()

    def __exit__(self, exception_type, exception_value, traceback):
        self.end()

class ControllableCamera(Camera):
    def on_resize(self, width, height):
        self.update_projection()
    
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if buttons == pyglet.window.mouse.MIDDLE:
            self.move(-dx,-dy)
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if scroll_y < 0:
            self.zoom_out(1.1, x, y)
        elif scroll_y > 0:
            self.zoom_in(1.1, x, y)