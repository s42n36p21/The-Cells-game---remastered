import asyncio
from asyncio import StreamReader, StreamWriter
import logging
import json
from hashlib import sha256
from enum import Enum

from core.TCGlogic.TCGCell import P_ENERGY, Energy
from random import shuffle

with open('saves/3x3.json', 'r', encoding='utf-8') as file:
    SCHEME = json.load(file)

with open('settings/server.json', 'r', encoding='utf-8') as file:
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
        WRONG_PASSWORD_2 = 301
        
        START = 400

class NetServer:

    def __init__(self, server_port, connection_timeout=False, allow_rejoin = True):
        self.server_port=server_port
        self.running=True
        self.server = None
        self.rejoin = allow_rejoin
        self.timeout = connection_timeout
        self.connections = {}
        self.password = CONFIG.get('password', None)
        if self.password:
            self.password = sha256(self.password.encode('utf-8')).hexdigest()
        self.players = {}
        self.db = {
            "register": {}
        }
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
                    data = await asyncio.wait_for(reader.readline(), 15)
                else:
                    data = await reader.readline()
                if not data:
                    if (client_address, client_port) in self.connections:
                        self.logger.info(f"Клиент {client_address}:{client_port} отключился")
                        self.connections.pop((client_address, client_port), None)
                        if (client_address, client_port) in self.names_connections:
                            await self.player_disconnected((client_address, client_port))
                    break
                message = data.decode('utf-8')
                if not message:
                    continue
                dictionary = json.loads(message)
                await self.handle_message((client_address, client_port), dictionary)
        except TimeoutError:
            self.logger.info(f"Клиент {client_address}:{client_port} не отвечает")
        except ConnectionResetError:
            if (client_address, client_port) in self.connections:
                self.logger.info(f"Клиент {client_address}:{client_port} отключился")
                self.connections.pop((client_address, client_port), None)
                if (client_address, client_port) in self.names_connections:
                    await self.player_disconnected((client_address, client_port))
        except Exception as e:
            self.running=False
            self.logger.error("Ошибка: ", e)
            self.connections.pop((client_address, client_port), None)
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Соединение с {client_address}:{client_port} закрыто")
            if (client_address, client_port) in self.names_connections:
                await self.player_disconnected((client_address, client_port))
    
    async def send(self, writer:StreamWriter, message: dict):
        """Отправляет сообщение указанному клиенту в writer"""
        if writer and not writer.is_closing():
            writer.write(json.dumps(message).encode('utf-8')+b"\n")
            await writer.drain()
        else:
            self.logger.error("Клиент закрыл соединение")

    async def close_client(self, connection):
        """Закрывает соединение с клиентом"""
        writer: StreamWriter = self.connections.pop(connection, None)
        if not writer:
            self.logger.info("Клиент уже отключен")
        if not writer.is_closing():
            self.logger.info(f"Закрытие соединения с клиентом {connection[0]}:{connection[1]}...")
            writer.close()
            await writer.wait_closed()
            self.logger.info(f"Клиент {connection[0]}:{connection[1]} был отключён!")
            if connection in self.names_connections:
                await self.player_disconnected(connection)

    async def close_all(self):
        """Полное отключение сервера"""
        self.logger.info(f"Закрытие всех соединений...")
        self.running=False
        self.server.close_clients()
        self.server.close()
        await self.server.wait_closed()
        self.logger.info(f"Сервер отключён!")

    async def player_disconnected(self, connection, exit:bool = False):
        name = self.names_connections.pop(connection)
        await self.broadcast({
            "code": Protocol.CODE.CLIENT_DISCONNECTED.value,
            "name": name,
            "exit": exit or not self.rejoin
        }, [connection])
        if exit or not self.rejoin:
            self.players.pop(name)

    def _check_acc_password(self, password, name) -> bool:
        if not name in self.db["register"]:
            self.db["register"].update({
                name: password
            })
            return True
        return self.db["register"].get(name) == password

    async def join_player(self, connection, name, acc_password):
        writer = self.connections.get(connection)
        if not self._check_acc_password(acc_password, name):
            await self.send(writer, {
                        'code': Protocol.CODE.WRONG_PASSWORD_2.value
                    })
            return await self.close_client(connection)
        self.logger.info('Игрок присоединился')
       
        await self.send(writer, {
            'code': Protocol.CODE.WELCOME.value,
            'scheme': SCHEME, 'players': self.players
        })
        
        self.names_connections.update({connection: name})
        if name not in self.players:
            self.players[name] = {'name':name, "position": (0,0)}
        
            msg = {"code": Protocol.CODE.NEW_PLAYER.value, "name": name}
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
                acc_password = message.get('account_password')
                if not self.password:
                    await self.join_player(connection, name, acc_password)
                    return
                if self.password == password:
                    await self.join_player(connection, name, acc_password)
                    return
                else:
                    await self.send(writer, {
                        'code': Protocol.CODE.WRONG_PASSWORD.value
                    })
                    await self.close_client(connection)
                    
                    
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
            case Protocol.CODE.QUIT:
                self.logger.info("Игрок вышел")
                await self.player_disconnected(connection, exit=True)
            case Protocol.CODE.READY:
                
                name = message.get('name')
                self.players[name]['ready'] = True
                self.logger.info(f"Игроки готовы: {[k for k, v in self.players.items() if v.get('ready', None)]}")
                if all([p.get('ready') for p in self.players.values()]) and len(self.players)>1:
                    self.logger.info("Запуск игры")
                    l = P_ENERGY
                    shuffle(l)
                    players = list(zip(self.players, [i.value for i in l]))
                    await self.broadcast({'code':Protocol.CODE.START.value, 'players': players})
                elif len(self.players)==1:
                    self.logger.info("Недостаточно игроков для начала игры")
                else:
                    self.logger.info("Не все игроки проголосовали за запуск игры")

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