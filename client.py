"""
Модуль для работы с клиентом
"""
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
        self.input_queue = deque()
        self.update_queue = deque()
        logging.debug("NetClient создан")
        if self.connect()==0:
            logging.debug("Запуск цикла...")
            self.thread = threading.Thread(target=self.network_loop, daemon=True)
            self.thread.start()

    def connect(self) -> int:
        """
        Выполняет подключение
        
        Возвращает номер ошибки или 0, если ошибок нет
        """
        attempt=1
        while attempt<=4:
            try:
                self.socket.settimeout(5)
                self.socket.connect((self.server_host, self.server_port))
                logging.info("Клиент подключён!")
                self.running=True
                return 0
            except ConnectionRefusedError:
                logging.error(f"Подключение к {self.server_host}:{self.server_port} было отвергнуто!")
                self.socket.close()
                return 1
            except socket.timeout:
                if attempt==4:
                    logging.error(f"Невозможно подключиться к серверу ({self.server_host}:{self.server_port})! Истекло время ожидания")
                    return 2
                logging.warning(f"Истекло время ожидания для {self.server_host}:{self.server_port}! Переподключение... ({attempt}/3)")
                attempt+=1
            except OSError:
                pass
    
    def network_loop(self):
        """
        Основной цикл сети в отдельном потоке
        """
        while self.running:
            try:
                while self.input_queue:
                    data = self.input_queue.popleft()
                    self.socket.sendall(json.dumps(data).encode("utf-8"))
                data = self.socket.recv(4096).decode("utf-8")
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
    
# debug
if __name__ == "__main__":
    client = NetClient("localhost", 12345)
    while client.running:
        client.send_input({'code': 10})
        logging.info(client.get_updates())