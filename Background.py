import pyglet 

class Background:
    def __init__(self, tex, window, batch=None):
        self.tex = pyglet.resource.texture(f'src/background/{tex}.png')
        self.window = window
        self.batch = batch or pyglet.graphics.Batch()
        
        # Создаем шейдерную программу для фона
        self.shader_program = self._create_shader_program()
        
        # Создаем группу для рендеринга
        self.group = self._create_render_group()
        
        # Создаем геометрию для фона
        self.vertex_list = self._create_background_geometry()
        
        # Обновляем uniform'ы при создании
        self._update_uniforms()
    
    def _create_shader_program(self):
        """Создает шейдерную программу для бесконечного фона"""
        vertex_source = """#version 330 core
            in vec2 position;
            in vec2 tex_coords;
            out vec2 texture_coords;

            uniform WindowBlock 
            {
                mat4 projection;
                mat4 view;
            } window;  

            void main()
            {
                gl_Position = vec4(position, 0.0, 1.0);
                texture_coords = tex_coords;
            }
        """

        fragment_source = """#version 330 core
            in vec2 texture_coords;
            out vec4 final_color;

            uniform sampler2D our_texture;
            uniform vec2 window_size;
            uniform vec2 texture_size;

            uniform WindowBlock 
            {
                mat4 projection;
                mat4 view;
            } window;  

            void main()
            {
                // Преобразуем нормализованные координаты в экранные (от -size/2 до +size/2)
                vec2 screen_coords = (texture_coords - 0.5) * window_size;
                
                
                //screen_coords = ((window.projection * window.view * vec4(screen_coords, 0.0,-1 + window.projection[2][2])).xy)* window_size/2;
              vec2 t = vec2(window.projection[3][0], window.projection[3][1]) * window_size;
              vec2 s = vec2(window.projection[0][0], window.projection[1][1]) * window_size;
              screen_coords = (screen_coords - t/2)/s*2;


                // Центрируем текстуру и создаем бесконечное повторение
                vec2 repeated_tex_coords = fract((screen_coords + texture_size * 0.5) / texture_size);
                
                final_color = texture(our_texture, repeated_tex_coords);
            }
        """

        vert_shader = pyglet.graphics.shader.Shader(vertex_source, 'vertex')
        frag_shader = pyglet.graphics.shader.Shader(fragment_source, 'fragment')
        program = pyglet.graphics.shader.ShaderProgram(vert_shader, frag_shader)
        
        return program
    
    def _create_render_group(self):
        """Создает группу рендеринга для фона"""
        class BackgroundGroup(pyglet.graphics.Group):
            def __init__(self, texture, program, parent=None):
                super().__init__(parent=parent)
                self.texture = texture
                self.program = program

            def set_state(self):
                self.program.use()
                pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                pyglet.gl.glBindTexture(self.texture.target, self.texture.id)
                self.program['our_texture'] = 0
                
            def unset_state(self):
                pass

            def __eq__(self, other):
                return (self.__class__ is other.__class__ and
                        self.texture.id == other.texture.id and
                        self.parent == other.parent)

            def __hash__(self):
                return hash((self.texture.id, self.parent))

        return BackgroundGroup(self.tex, self.shader_program)
    
    def _create_background_geometry(self):
        """Создает геометрию фона на весь экран"""
        # Вершины покрывающие все окно (в координатах OpenGL)
        positions = [
            -1.0, -1.0,  # нижний левый
             1.0, -1.0,  # нижний правый
             1.0,  1.0,  # верхний правый
            -1.0,  1.0,  # верхний левый
        ]
        
        

        # Текстурные координаты охватывают все окно
        tex_coords = [
            0.0, 0.0,  # нижний левый
            1.0, 0.0,  # нижний правый
            1.0, 1.0,  # верхний правый
            0.0, 1.0,  # верхний левый
        ]
        
        indices = [0, 1, 2, 0, 2, 3]
        
        return self.shader_program.vertex_list_indexed(
            4, pyglet.gl.GL_TRIANGLES, indices, batch=self.batch, group=self.group,
            position=('f', positions),
            tex_coords=('f', tex_coords)
        )
    
    def _update_uniforms(self):
        """Обновляет uniform переменные"""
        self.shader_program['window_size'] = [self.window.width, self.window.height]
        self.shader_program['texture_size'] = [self.tex.width, self.tex.height]
    
    def on_resize(self, width, height):
        """Вызывается при изменении размера окна"""
        self._update_uniforms()
        
    
    def draw(self):
        """Отрисовывает фон"""
        self.batch.draw()
    
    def update(self, dt):
        """Обновление фона"""
        pass


# Пример использования:
