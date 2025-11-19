"""
Модуль для работы с клиентом
"""
import time
from enum import Enum
import select
import socket
import threading
import json
from collections import deque
import logging
from pyglet.event import EventDispatcher
from server import Protocol
from hashlib import sha256

logging.basicConfig(level=logging.INFO)

class NetClient(EventDispatcher):
    def __init__(self, server_host, server_port, use_queue=False):
        self.server_host=server_host
        self.server_port=server_port
        self.running=False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._is_connected=False
        self._is_connecting=False
        self.input_queue = deque()
        self.update_queue = deque()
        self.buffer = b''
        self.use_queue=use_queue
        logging.debug("NetClient создан")
        if self.connect()==0:
            self._is_connected=True
            self._is_connecting=False
            logging.debug("Запуск цикла...")
            time.sleep(0.1)
            self.thread = threading.Thread(target=self.network_loop, daemon=True)
            self.thread.start()

    @property
    def is_connecting(self) -> bool:
        """Переменная, которая указывает, подключается ли сейчас клиент"""
        return self._is_connecting
    
    @property
    def is_connected(self) -> bool:
        """Переменная, которая указывает, подключен ли клиент"""
        return self._is_connected

    def connect(self) -> int:
        """
        Выполняет подключение
        
        Возвращает номер ошибки или 0, если ошибок нет
        """
        self._is_connecting=True
        attempt=1
        while attempt<=4:
            try:
                self.socket.settimeout(5)
                self.socket.connect((self.server_host, self.server_port))
                logging.info("Клиент подключён!")
                self.socket.setblocking(False)
                self.running=True
                self.dispatch_event("on_connect")
                return 0
            except ConnectionRefusedError:
                logging.error(f"Подключение к {self.server_host}:{self.server_port} было отвергнуто!")
                self._is_connecting=False
                self.socket.close()
                self.dispatch_event("on_disconnect")
                return 1
            except socket.timeout:
                if attempt==4:
                    logging.error(f"Невозможно подключиться к серверу ({self.server_host}:{self.server_port})! Истекло время ожидания")
                    self._is_connecting=False
                    self.socket.close()
                    self.dispatch_event("on_disconnect")
                    return 2
                logging.warning(f"Истекло время ожидания для {self.server_host}:{self.server_port}! Переподключение... ({attempt}/3)")
                attempt+=1
            except OSError:
                pass
    
    def network_loop(self):
        """
        Основной цикл сети в отдельном потоке
        """
        try:
            while self.running:
                read_sockets = [self.socket]
                write_sockets = [self.socket] if self.input_queue else []
                readable, writable, exceptional = select.select(read_sockets, write_sockets, read_sockets, 0.01)

                if self.socket in writable:
                    while self.input_queue:
                        data = self.input_queue.popleft()
                        self.socket.sendall(json.dumps(data).encode("utf-8")+b"\n")
                if self.socket in readable:
                    raw_data = self.socket.recv(4096).decode('utf-8').split("\n")
                    for data in raw_data[:len(raw_data)-1]:
                        if not data:
                            logging.info("Получены пустые данные: соединение закрыто")
                            self.dispatch_event("on_disconnect")
                            break
                        update = json.loads(data)
                        self.dispatch_event("on_receive", update)
                        if self.use_queue:
                            self.update_queue.append(update)

        except ConnectionResetError:
            logging.error(f"Соединение с сервером {self.server_host}:{self.server_port} было разорвано!")
            self.dispatch_event("on_disconnect")
            self._is_connected = False
            self.running=False
            self.socket.close()

        except OSError as e:
            logging.error(e)
            self.dispatch_event("on_disconnect")
            self._is_connected = False
            self.running=False
            self.socket.close()

    def get_updates(self):
        """Возвращает все накопленные сообщения"""
        if not self.use_queue:
            raise RuntimeError("Невозможно использовать get_updates с use_queue=False")
        updates = list(self.update_queue)
        self.update_queue.clear()
        return updates
    
    def send(self, input):
        """Отправляет сообщение в очередь на отправку"""
        self.input_queue.append(input)

    def close(self):
        """Закрытие соединения"""
        logging.debug(f"Закрытие соединения с {self.server_host}:{self.server_port}")
        self._is_connected = False
        self.running=False
        self.socket.close()
        self.dispatch_event("on_disconnect")

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_receive(self, update):
        pass

NetClient.register_event_type("on_connect")
NetClient.register_event_type("on_disconnect")
NetClient.register_event_type("on_receive")

class GameClient(NetClient):
    def __init__(self, server_host, server_port, server_password:str, account_password, player_name):
        self.player_name = player_name
        self.server_password = server_password
        if self.server_password:
            self.server_password = sha256(self.server_password.encode('utf-8')).hexdigest()
        self.account_password = account_password
        if not self.account_password:
            raise ValueError("Пароль аккаунта не указан")
        self.account_password = sha256(self.account_password.encode('utf-8')).hexdigest()
        self.heartbeat_count = 0
        self.ack = True
        super().__init__(server_host, server_port)

    def send_heartbeat(self):
        self.send(
            {
                "code": Protocol.CODE.HEARTBEAT.value
            }
        )

    def on_connect(self):
        self.send({"code":Protocol.CODE.HELLO.value, "name":self.player_name, "password":self.server_password, "account_password": self.account_password})

    def on_receive(self, update:dict):
        code = Protocol.CODE(update.get("code"))
        match code:
            case Protocol.CODE.ACK:
                self.ack=True
                self.dispatch_event("heartbeat_ack")
            case Protocol.CODE.WRONG_PASSWORD:
                raise PermissionError("Неправильный пароль для сервера")
            case Protocol.CODE.WRONG_PASSWORD_2:
                raise PermissionError("Неправильный пароль для аккаунта")
            case Protocol.CODE.WELCOME:
                scheme = update.get("scheme")
                players = update.get("players")
                self.dispatch_event("on_join", scheme, players)
            case Protocol.CODE.NEW_PLAYER:
                player_name = update.get("name")
                self.dispatch_event("on_player_joined", player_name)
            case Protocol.CODE.PLAYER_MOVE:
                player_name = update.get("name")
                pos = update.get("move")
                moved_time = update.get("time")
                self.dispatch_event("on_player_moved", player_name, pos, moved_time)
            case Protocol.CODE.PLAYER_HIT:
                player_name = update.get("name")
                hit = update.get("hit")
                self.dispatch_event("on_player_hit", player_name, hit)
            case Protocol.CODE.START:
                players = update.get("players")
                self.dispatch_event("on_game_start", players)
            case Protocol.CODE.CLIENT_DISCONNECTED:
                player_name = update.get("name")
                exit = update.get("exit")
                self.dispatch_event("on_player_disconnect", player_name, exit)

    def update(self):
        self.heartbeat_count = (self.heartbeat_count + 1) % 300
        if self.heartbeat_count == 0:
            self.send_heartbeat()
            if not self.ack:
                self.close()
                return
            self.ack = False

    def heartbeat_ack(self):
        pass

    def on_player_disconnect(self, player_name, exit):
        pass

    def on_player_joined(self, player_name):
        pass

    def on_join(self, scheme, players):
        pass

    def on_player_moved(self, player_name, pos, moved_time):
        pass

    def on_player_hit(self, player_name, hit):
        pass

    def on_game_start(self, players):
        pass

GameClient.register_event_type("heartbeat_ack")
GameClient.register_event_type("on_player_disconnect")
GameClient.register_event_type("on_player_joined")
GameClient.register_event_type("on_join")
GameClient.register_event_type("on_player_moved")
GameClient.register_event_type("on_player_hit")
GameClient.register_event_type("on_game_start")

# debug
if __name__ == "__main__":
    connection = GameClient("localhost", 12345, 123456, "Artyom")