from pyglet.gl import (glActiveTexture, GL_TEXTURE0, glBindTexture, glEnable,
     GL_BLEND, glBlendFunc, GL_DEPTH_TEST, glDepthFunc, GL_LESS, glDisable)
from pyglet import gl
from pyglet.image import load, ImageGrid
from pyglet.sprite import Sprite, SpriteGroup, vertex_source
from pyglet.math import Vec2
from pyglet.text import Label
from pyglet.graphics import Batch, shader
from collections import deque

def load_pixel_art_texture(filename):
    """Загружает текстуру с отключенной интерполяцией для пиксельной графики"""
    image = load(filename)
    texture = image.get_texture()
    
    gl.glBindTexture(texture.target, texture.id)
    gl.glTexParameteri(texture.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(texture.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
    
    return texture

N, E, S, W = 0, 1, 2, 3

fragment_source = """#version 150 core
    in vec4 vertex_colors;
    in vec3 texture_coords;
    out vec4 final_colors;

    uniform sampler2D sprite_texture;

    void main()
    {
        final_colors = texture(sprite_texture, texture_coords.xy) * vertex_colors;
        
        // No GL_ALPHA_TEST in core, use shader to discard.
        if(final_colors.a < 0.01){
            discard;
        }
    }
"""

vertex_shader = shader.Shader(vertex_source, "vertex")
fragment_shader = shader.Shader(fragment_source, "fragment")
depth_shader = shader.ShaderProgram(vertex_shader, fragment_shader)

class DepthSpriteGroup(SpriteGroup):
    def set_state(self):
        self.program.use()

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(self.texture.target, self.texture.id)

        glEnable(GL_BLEND)
        glBlendFunc(self.blend_src, self.blend_dest)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        #gl.glDepthMask(gl.GL_TRUE)  # Разрешить запись в буфер глубины

    def unset_state(self):
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        #gl.glDepthMask(gl.GL_FALSE)  # Запретить запись в буфер глубины
        self.program.stop()

class DepthSprite(Sprite):
    group_class = DepthSpriteGroup

class ActorSpriteManager:
    def __init__(self, path, scan_type='news', anim_length=4, batch=None):
        self.actor_texture = actor_texture = load_pixel_art_texture(path)
        self.actor_seq = actor_seq = ImageGrid(actor_texture, 4, anim_length)
        self.sprite = [None for s in range(4)]
        ref = zip(scan_type, list(range(4)))
        self.current = None
        self.heading = S
        self.state = 0
        for t, i in ref:
            sprites = [DepthSprite(actor_seq[(i, p)], batch=batch, program=depth_shader) for p in range(anim_length)]
            self.sprite['nesw'.index(t)] = sprites

        for i in self.sprite:
            for j in i:
                j: Sprite
                j.visible = False
        self.current = self.sprite[S][0]
        self.anchor()

    def use(self, heading=None, state=None):
        self.heading = self.heading if heading is None else heading
        self.state = self.state if state is None else state
        sprite = self.sprite[self.heading][self.state]
        pos = self.position
        self.current.visible = False
        self.current: Sprite = sprite
        self.position = pos
        self.current.visible = True
        
    def hide(self):
        self.current.visible = False

    def anchor(self, x=.5, y=.5):
        self.anchor_x=x
        self.anchor_y=y

    @property
    def width(self):
        return self.current.width
    
    @property
    def height(self):
        return self.current.height

    @property
    def position(self):
        x, y, z = self.current.position
        return Vec2(x, y) + Vec2(self.current.width, self.current.height) \
            * Vec2(self.anchor_x, self.anchor_y)

    @position.setter
    def position(self, new):
        anchor_offset = Vec2(self.width * self.anchor_x, 
                            self.height * self.anchor_y)
        z_value = -new[1] * 0.001  
        self.current.position = (new[0] - anchor_offset.x, 
                                new[1] - anchor_offset.y, 
                                z_value) 


class Actor:
    ID = 0
    def __init__(self, 
                 position=(0, 0), 
                 name="Entity",
                 color=(255,255,255,127),
                 img=None,
                 scan_type='news',
                 anim_length=4,
                 batch=None
                 ):
        self.ID = Actor.ID
        Actor.ID += 1
        self._batch = batch or Batch()
        self._sprite = ActorSpriteManager(img, scan_type, anim_length, batch=self._batch)
        self._sprite.use(S, 0)
        self._name_lable = Label(anchor_x='center', batch=self._batch)
        self.position = position
        self.name = name
        self.color = color

    @property
    def name(self):
        return self._name_lable.text

    @name.setter
    def name(self, name):
        self._name_lable.text = name

    @property
    def color(self):
        return self._name_lable.color
    
    @color.setter
    def color(self, color):
        r, g, b, *a = color
        self._name_lable.color = (r, g, b, 127)
    
    @property
    def position(self):
        return self._sprite.position
    
    @position.setter
    def position(self, new):
        self._sprite.position = new
        self.update_lable()

    def update_lable(self):
        text_x, text_y = self._sprite.position
        text_y += self._sprite.height / 2
        self._name_lable.x = text_x
        self._name_lable.y = text_y

    def update(self, dt):
        pass

    def draw(self):
        self._batch.draw()
        
class MoveableActor(Actor):
    def __init__(self, position=(0, 0), name="Entity", color=(255, 255, 255, 127), speed=250, img=None, scan_type='news', anim_length=4, batch=None):
        super().__init__(position, name, color, img, scan_type, anim_length, batch)
        self._speed = speed
        self.anim_length = anim_length
        self.target = None
        self.timer = 0
        self._step_delay = 0.25

    @property
    def speed(self):
        return self._speed
    
    @speed.setter
    def speed(self, new):
        self._speed = new

    def goto(self, x, y, time=None):
        self.target = Vec2(x, y)

    def move(self, dx, dy, time=None):
        self.goto(*(Vec2(dx, dy) + self.position), time=time)
    
    def stop(self):
        self.timer = 0
        self.target = None
        self._sprite.use(state=0)

    def look(self, x, y):
        if not (x or y):
            return
        if (abs(x)+.1) < (abs(y)):
            heading = N if y > 0 else S
        else:
            heading = E if x > 0 else W
        if self._sprite.heading != heading:
            self._sprite.use(heading=heading)

    @property
    def step_delay(self):
        return self._step_delay * (100.0 / self.speed if self.speed > 0 else 1.0)
    
    @step_delay.setter
    def step_delay(self, new):
        self._step_delay = new

    def step(self):
        if self.timer > self.step_delay:
            self._sprite.use(state=(self._sprite.state + 1) % self.anim_length)
            self.timer = 0

    def update(self, dt):
        if self.target is None:
            return
        
        dist: Vec2 = self.target - self.position
        speed = self.speed * dt
        self.look(*dist)

        if dist.length() > speed:
            self.timer += dt
            self.step()
            
            self.position += dist.normalize() * speed

        else:
            self.position = self.target
            self.stop()
            return
        
NESW = [N, E, S, W]

from pyglet.window.key import LEFT, RIGHT, UP, DOWN, W as WW, A, S as SS, D

WASD = [WW, D, SS, A]
ULDR = [UP, RIGHT, DOWN, LEFT]
WASD_ULDR = WASD + ULDR



def key_to_side(key):
    return NESW[WASD_ULDR.index(key)%4]

class Player(MoveableActor):
    def __init__(self, position=(0, 0), name="Entity", color=(255, 255, 255, 127), speed=100, img=None, scan_type='news', anim_length=4, batch=None):
        super().__init__(position, name, color, speed, img, scan_type, anim_length, batch)

        self.go = set()
        self.camera = None

    def on_key_press(self, symbol, modifiers):
        if symbol in WASD_ULDR:
            self.go.add(key_to_side(symbol))
    
    def on_key_release(self, symbol, modifiers):
        if symbol in WASD_ULDR:
            self.go.discard(key_to_side(symbol))

    def on_hide(self):
        self.go.clear()

    def attach_camera(self, cam):
        self.camera = cam

    def detach_camera(self):
        self.camera = None

    def on_deactivate(self):
        self.go.clear()

    def update(self, dt):
        if self.go:
            self.timer += dt
            velocity = Vec2(0, 1) * (N in self.go) + \
                    Vec2(1, 0) * (E in self.go) + \
                    Vec2(0, -1) * (S in self.go) + \
                    Vec2(-1, 0) * (W in self.go)
            velocity = velocity.normalize() * self.speed * dt
            self.look(*velocity)
            self.step()
            self.position += velocity
        else:
            if self.target is None:
                if self._sprite.state:
                    self._sprite.use(state=0)
            else:
                super().update(dt)
        

        if self.camera:
            self.camera.focus(*self.position)