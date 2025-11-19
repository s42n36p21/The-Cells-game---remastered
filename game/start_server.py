from core.networking.server import NetServer
import json
import asyncio

with open('settings/server.json', 'r', encoding='utf-8') as file:
    CONFIG = json.load(file)

server = NetServer(CONFIG.get("port"), connection_timeout=True)
asyncio.run(server.start_forever())