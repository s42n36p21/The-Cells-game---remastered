import asyncio
from asyncio import StreamReader, StreamWriter
import logging
import json
from enum import Enum

from TCGCell import P_ENERGY, Energy
from random import shuffle

with open('3x3.json', 'r', encoding='utf-8') as file:
    SCHEME = json.load(file)

with open('server.json', 'r', encoding='utf-8') as file:
    CONFIG = json.load(file)

class Protocol:
    class CODE(Enum):
        HELLO = 10
        WELCOME = 20
        NEW_PLAYER = 30  
        CLIENT_DISCONNECTED=40
        HEARTBEAT=50
        ACK = 60
        
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

class NetServer:

    def __init__(self, server_port, connection_timeout=False):
        self.server_port=server_port
        self.running=True
        self.server = None
        self.timeout = connection_timeout
        self.connections = {}
        self.db = {
            "register":CONFIG
        }
        self.players = {}
        self.names_connections = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG)
    
    async def start_forever(self):
        self.server = await asyncio.start_server(self.network_loop, "0.0.0.0", self.server_port)
        async with self.server:
            self.logger.info(f"Сервер открыт и слушает на порту {self.server_port}")
            self.running=True
            await self.server.serve_forever()

    async def network_loop(self, reader:StreamReader, writer:StreamWriter):
        """
        Основной цикл сети в асинхронном потоке
        """
        client_address, client_port = writer.get_extra_info('peername')
        self.connections.update({(client_address, client_port):writer})
        self.logger.info(f"Подключен новый клиент: {client_address}:{client_port}")
        try:
            while self.running:
                if self.timeout:
                    data = await asyncio.wait_for(reader.readline(), 30)
                else:
                    data = await reader.readline()
                if not data:
                    self.logger.info(f"Клиент {client_address}:{client_port} отключился")
                    self.connections.pop((client_address, client_port), None)
                    await self.player_disconnected((client_address, client_port))
                    break
                message = data.decode('utf-8')
                if not message:
                    continue
                dictionary = json.loads(message)
                await self.handle_message((client_address, client_port), dictionary)
        except ConnectionResetError:
            self.logger.info(f"Клиент {client_address}:{client_port} отключился")
            self.connections.pop((client_address, client_port), None)
            await self.player_disconnected((client_address, client_port))
        except Exception as e:
            self.running=False
            self.logger.error("Ошибка: ", e)
            self.connections.pop((client_address, client_port), None)
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Соединение с {client_address}:{client_port} закрыто")
            await self.player_disconnected((client_address, client_port))
    
    async def send(self, writer:StreamWriter, message: dict):
        """Отправляет сообщение указанному клиенту в writer"""
        if writer and not writer.is_closing():
            writer.write(json.dumps(message).encode('utf-8')+b"\n")
            await writer.drain()
        else:
            self.logger.error("Пидор закрыл соединение")

    async def close_client(self, connection):
        """Закрывает соединение с клиентом"""
        writer: StreamWriter = self.connections.pop(connection, None)
        if not writer:
            self.logger.info("Пидор уже закрыт")
        if not writer.is_closing():
            self.logger.info(f"Закрытие соединения с клиентом {connection[0]}:{connection[1]}...")
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Клиент {connection[0]}:{connection[1]} был отключён!")
            await self.player_disconnected(connection)

    async def close_all(self):
        """Полное отключение сервера"""
        self.logger.info(f"Закрытие всех соединений...")
        self.running=False
        self.server.close_clients()
        self.server.close()
        await self.server.wait_closed()
        self.logger.info(f"Сервер отключён!")

    async def player_disconnected(self, connection):
        name = self.names_connections.pop(connection)
        await self.broadcast({
            "code": Protocol.CODE.CLIENT_DISCONNECTED.value,
            "name": name
            }, [connection])
        self.players.pop(name)

    async def join_player(self, connection, message):
        writer = self.connections.get(connection)
        self.logger.info('Пидор присоединился')
       
        await self.send(writer, {
            'code': Protocol.CODE.WELCOME.value,
            'scheme': SCHEME, 'players': self.players
        })
        
        self.names_connections.update({connection: message.get("name")})

        self.players[message.get('name')] = {'name':message.get('name'), "position": (0,0)}
        
        msg = {"code": Protocol.CODE.NEW_PLAYER.value, "name": message.get('name')}
        await self.broadcast(msg, [connection])

    async def handle_message(self, connection: tuple, message: dict):
        code = Protocol.CODE(message.get('code'))
        writer = self.connections.get(connection)
        match code:
            case Protocol.CODE.HEARTBEAT:
                await self.send(writer, {
                    "code": Protocol.CODE.ACK.value
                })

            case Protocol.CODE.HELLO:
                self.logger.info("Попытка входа клиента")
                name = message.get('name')
                password = message.get('password')
                if self.db['register'].get(name):
                    if self.db['register'].get(name) == password:
                        await self.join_player(connection, message)
                    else:
                        await self.send(writer, {
                            'code': Protocol.CODE.WRONG_PASSWORD.value
                        })
                        await self.close_client(connection)
                else:
                    self.db['register'][name] = password
                    await self.join_player(connection, message)
                    
                    
            case Protocol.CODE.MOVE:
                name = message.get('name')
                pos = message.get('move')
                time = message.get('time')
                
                self.players[name]['position'] = pos
                await self.broadcast({
                    "code": Protocol.CODE.PLAYER_MOVE.value,
                    "name": name,
                    "move": pos,
                    "time": time
                }, exclude=[connection])
                
            case Protocol.CODE.HIT:
                self.logger.info('пидор походил')
                await self.broadcast(
                    {'code':Protocol.CODE.PLAYER_HIT.value, 'hit': message.get('hit'), 'name': message.get('name')}
                )
            case Protocol.CODE.PASS:1
            case Protocol.CODE.QUIT:1
            case Protocol.CODE.READY:
                
                name = message.get('name')
                self.players[name]['ready'] = True
                print([p.get('ready') for p in self.players.values()])
                if all([p.get('ready') for p in self.players.values()]):
                    self.logger.info("Запуск игры")
                    l = P_ENERGY
                    shuffle(l)
                    players = list(zip(self.players, [i.value for i in l]))
                    await self.broadcast({'code':Protocol.CODE.START.value, 'players': players})

    async def broadcast(self, message:dict, exclude:list[tuple] | None = None):
        """Передача сообщения всем клиентам, которые не находятся в списке exclude"""
        if not exclude:
            exclude = []
        writer_list = [writer for connection, writer in self.connections.items() if connection not in exclude]
        for writer in writer_list:
            await self.send(writer, message)

if __name__ == "__main__":
    server = NetServer(CONFIG.get("port"), connection_timeout=True)
    asyncio.run(server.start_forever())