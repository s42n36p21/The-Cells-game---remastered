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

logging.basicConfig(level=logging.DEBUG)

class NetClient:
    def __init__(self, server_host, server_port):
        self.server_host=server_host
        self.server_port=server_port
        self.running=False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._is_connected=False
        self._is_connecting=False
        self.input_queue = deque()
        self.update_queue = deque()
        logging.debug("NetClient создан")
        if self.connect()==0:
            self._is_connected=True
            self._is_connecting=False
            logging.debug("Запуск цикла...")
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
                return 0
            except ConnectionRefusedError:
                logging.error(f"Подключение к {self.server_host}:{self.server_port} было отвергнуто!")
                self._is_connecting=False
                self.socket.close()
                return 1
            except socket.timeout:
                if attempt==4:
                    logging.error(f"Невозможно подключиться к серверу ({self.server_host}:{self.server_port})! Истекло время ожидания")
                    self._is_connecting=False
                    self.socket.close()
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
                readable, writable, exceptional = select.select(read_sockets, write_sockets, read_sockets, 0.1)

                if self.socket in writable:
                    while self.input_queue:
                        data = self.input_queue.popleft()
                        self.socket.sendall(json.dumps(data).encode("utf-8"))
                if self.socket in readable:
                    data = self.socket.recv(4096).decode("utf-8")
                    logging.info(data)
                    if data:
                        update=json.loads(data)
                        self.update_queue.append(update)
        except OSError as e:
            logging.error(e)
            self.running=False
            self.socket.close()

    def get_updates(self):
        """Возвращает все накопленные сообщения"""
        updates = list(self.update_queue)
        self.update_queue.clear()
        return updates
    
    def send_input(self, input):
        """Отправляет сообщение в очередь на отправку"""
        self.input_queue.append(input)

    def close(self):
        """Закрытие соединения"""
        logging.debug(f"Закрытие соединения с {self.server_host}:{self.server_port}")
        self.running=False
        self.socket.close()

class GameClient:
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

    def __init__(self, server_host, server_port, password, player_name):
        self.client = NetClient(server_host, server_port)
        while self.client.is_connecting:
            time.sleep(0.1)
        if not self.client.running:
            logging.error("Разорвано соединение с сервером")
            raise ConnectionError
        if not self.client.is_connected:
            raise ConnectionError
        self.client.send_input({"code":self.CODE.HELLO.value, "name":player_name, "password":password})
        time.sleep(1)
        while True:
            self.client.send_input({"code":self.CODE.HELLO.value, "name":player_name, "password":password})
            time.sleep(0.1)
        #update:dict = self.client.get_updates()
        #if not update:
            #logging.error("Ответ от сервера не был получен")
            #raise ConnectionError
        #code = update.get("code")
        #if code == self.CODE.WRONG_PASSWORD:
            #raise PermissionError("Неправильный пароль")
        #if code == self.CODE.WELCOME:
           # self.scheme = update.get("scheme")
           # self.players = update.get("players")    

# debug
if __name__ == "__main__":
    connection = GameClient("localhost", 12345, 123456, "Artyom")