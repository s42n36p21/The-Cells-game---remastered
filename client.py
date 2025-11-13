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
from server import NetServer

logging.basicConfig(level=logging.DEBUG)

class NetClient(EventDispatcher):
    def __init__(self, server_host, server_port):
        self.server_host=server_host
        self.server_port=server_port
        self.running=False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._is_connected=False
        self._is_connecting=False
        self.input_queue = deque()
        self.update_queue = deque()
        self.buffer = b''
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
                    raw_data = self.socket.recv(4096)
                    if not raw_data:
                        logging.info("Получены пустые данные: соединение закрыто")
                        self.dispatch_event("on_disconnect")
                        break
                    update = json.loads(raw_data)
                    self.dispatch_event("on_receive", update)
                    self.update_queue.append(update)
                    # может быть полезно позже
                    """
                    self.buffer += raw_data
                    logging.debug(f"Получено сырых байтов: {len(raw_data)}, буфер: {len(self.buffer)} байт")
                    
                    # Парсим буфер на строки (до \n)
                    while b'\n' in self.buffer:
                        line_bytes, self.buffer = self.buffer.split(b'\n', 1)
                        if line_bytes:
                            try:
                                message_str = line_bytes.decode("utf-8")
                                update = json.loads(message_str)
                                self.update_queue.append(update)
                            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                                logging.error(f"Ошибка парсинга строки '{line_bytes.decode('utf-8', errors='ignore')}': {e}")
                        else:
                            logging.debug("Получена пустая строка")"""
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

class GameClient:
    def __init__(self, server_host, server_port, password, player_name):
        self.client = NetClient(server_host, server_port)
        self.client.push_handlers(self)
        self.player_name = player_name
        self.password = password

    def on_connect(self):
        self.client.send({"code":NetServer.CODE.HELLO.value, "name":self.player_name, "password":self.password})

    def on_receive(self, update):
        code = update.get("code")
        match code:
            case NetServer.CODE.WRONG_PASSWORD:
                raise PermissionError("Неправильный пароль")
            case NetServer.CODE.WELCOME:
                self.scheme = update.get("scheme")
                self.players = update.get("players")
                logging.info("Вошли!")

# debug
if __name__ == "__main__":
    connection = GameClient("localhost", 12345, 123456, "Artyom")