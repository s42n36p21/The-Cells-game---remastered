import configparser

PATH = 'src/settings.cfg'

class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            # Инициализация значений по умолчанию
            cls._instance.amount_players = 2
            cls._instance.background = ''
            cls._instance.sensor_type = 1
            cls._instance.sound_effects = True
            cls._instance.chain_reaction = True
            cls._instance.fullscreen = False
        return cls._instance
    
    def load(self):
        config = configparser.ConfigParser()
        config.read(PATH)
        
        self.amount_players = config['ROOT'].getint('amount_players')
        self.background = config['ROOT'].get('background')
        self.sensor_type = config['ROOT'].getint('sensor_type')
        self.sound_effects = config['ROOT'].getboolean('sound_effects')
        self.chain_reaction = config['ROOT'].getboolean('chain_reaction')
        self.fullscreen = config['ROOT'].getboolean('fullscreen')
        
    def save(self):
        config = configparser.ConfigParser()
        
        config['ROOT'] = {
            'amount_players': str(self.amount_players),
            'background': self.background,
            'sensor_type': str(self.sensor_type),
            'sound_effects': str(self.sound_effects).lower(),
            'chain_reaction': str(self.chain_reaction).lower(),
            'fullscreen': str(self.fullscreen)
        }
        
        with open(PATH, 'w') as configfile:
            config.write(configfile)