import pyglet
from pyglet.experimental import net
import weakref
import json
from typing import Dict, Any
import time
from enum import Enum

from TCGCell import P_ENERGY, Energy
from random import shuffle

with open('3x3.json', 'r', encoding='utf-8') as file:
    SCHEME = json.load(file)

class Protocol:
    class CODE(Enum):
        HELLO = 10
        WELCOME = 20
        NEW_PLAYER = 30  
        
        MOVE = 100
        HIT = 110
        PASS = 120
        QUIT = 130
        READY = 140
        
        PLAYER_MOVE = 200
        PLAYER_HIT = 210
        PLAYER_PASS = 220
        PLAYER_QUIT = 230
        
        WRONG_PASSWORD = 300   
        
        START = 400
        
    def __init__(self, server: "GameServer"):
        self.server = server
        
    def connection(self, connection):
        self.server.hello_connections.add(connection)
        connection.push_handlers(self.server)
        
    def join_player(self, connection, data):
        #print('Отправка новому клиенту данных')
        self.server.connections.add(connection)
       
        self.server.send({
            'code': self.CODE.WELCOME.value,
            'scheme': SCHEME, 'players': self.server.players
        }, connection)
        
        self.server.players[data.get('name')] = {'name':data.get('name'), "position": (0,0)}
        
        msg = {"code": self.CODE.NEW_PLAYER.value, "name": data.get('name')}
        self.server.broadcast(msg, connection)
        
    def handle_message(self, connection, data: Dict):
        #print("Пришло сообщение от клиента")
        #print(data)
        code = self.CODE(data.get('code'))
        match code:
            case self.CODE.HELLO:
                #print("Попытка входа клиента")
                if connection not in self.server.hello_connections:
                    return
                name = data.get('name')
                password = data.get('password')
                if self.server.db['register'].get(name):
                    if self.server.db['register'].get(name) == password:
                        self.join_player(connection, data)
                    else:
                        self.server.send({
                            'code': self.CODE.WRONG_PASSWORD.value
                        })
                        self.server.hello_connections.discard(connection)
                        connection.close()
                else:
                    self.server.db['register'][name] = password
                    self.join_player(connection, data)
                    
                    
            case self.CODE.MOVE:
                name = data.get('name')
                pos = data.get('move')
                time = data.get('time')
                
                self.server.players[name]['position'] = pos
                self.server.broadcast({
                    'code': self.CODE.PLAYER_MOVE.value,
                    'name': name,
                    'move': pos ,
                    'time': time
                }, exclude=connection)
                
            case self.CODE.HIT:
                print('игрок походил')
                self.server.broadcast(
                    {'code':self.CODE.PLAYER_HIT.value, 'hit': data.get('hit'), 'name': data.get('name')}
                )
            case self.CODE.PASS:1
            case self.CODE.QUIT:1
            case self.CODE.READY:
                
                name = data.get('name')
                self.server.players[name]['ready'] = True
                print([p.get('ready') for p in self.server.players.values()])
                if all([p.get('ready') for p in self.server.players.values()]):
                    
                    l = P_ENERGY
                    shuffle(l)
                    players = list(zip(self.server.players, [i.value for i in l]))
                    self.server.broadcast({'code':self.CODE.START.value, 'players': players})
                

class GameServer:
    def __init__(self, host='localhost', port=12345):
        self.server = net.Server(address=host, port=port)
        self.connections = weakref.WeakSet()
        self.hello_connections = weakref.WeakSet()
        self.db = {
            "register": {}, 
        }
        
        self.players = {}
        
        self.protocol = Protocol(self)
        
        # Регистрируем обработчики событий
        self.server.push_handlers(self)
        
    def on_connection(self, connection):
        print(f"Новый клиент подключился: {connection}")
        self.protocol.connection(connection)
        
    
    def on_disconnect(self, connection):
        print(f"Клиент отключился: {connection}")
        self.connections.discard(connection)
    
    def on_receive(self, connection, message):
        try:
            data = json.loads(message.decode())
            self.handle_message(connection, data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Ошибка декодирования сообщения: {e}")
    
    def handle_message(self, connection, data):
        self.protocol.handle_message(connection, data)
    
    def send(sekf, message, connection):
        message_bytes = json.dumps(message).encode()
        try:
            connection.send(message_bytes)
        except:
            print("Не получилось доставить")
            pass
        
    def broadcast(self, message, exclude=None):
       # print("""Отправка сообщения всем подключенным клиентам""")
        
        message_bytes = json.dumps(message).encode()
        for connection in self.connections:
            if connection is not exclude:
                try:
                    #print("Отправка клиенту из броадкаста")
                    connection.send(message_bytes)
                except:
                    # Если отправка не удалась, соединение, вероятно, разорвано
                    pass

def main():
    server = GameServer(host='localhost', port=12345)
    print("Сервер запущен. Ожидание подключений...")
    
    try:
        pyglet.app.run()
    except KeyboardInterrupt:
        print("Сервер остановлен")

if __name__ == "__main__":
    main()