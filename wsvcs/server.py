import websockets

from wsvcs.src.chunkify.chunk_reader import split_package_to_chunks
from wsvcs.src.tui import input_with_default
from wsvcs.src.packages import *

from websockets import WebSocketServerProtocol
from websockets.server import serve

from pickle import dumps, loads

import asyncio


class Server:
    def __init__(self):
        self.rooms = {}

    async def run(self):
        print('Start As Server')
        ip   = input_with_default('Ip', 'localhost')
        port = int(input_with_default('Port', '8765'))
        async with serve(self.bootstrap, ip, port):
            print('Bootstrap has started')
            await asyncio.get_running_loop().create_future()

    async def bootstrap(self, websocket: WebSocketServerProtocol):
        role = await websocket.recv()

        if role == 'sub':
            print("[SUB]: Receiving project name")
            project_name = loads(await websocket.recv())['room']

            try:
                async with asyncio.timeout(60):
                    while project_name not in self.rooms:
                        await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                await websocket.close(reason="Publisher not create a room during 60 seconds")
                return

            self.rooms[project_name]['subscribers'].append(websocket)

            try:
                print("[SUB]: Receiving missing packages")
                files = set((await self.receive_chunked_package(websocket))['packages'])
                self.rooms[project_name]['status'] += 1
                self.rooms[project_name]['files']  |= files

                print("[SUB]: Waiting to complete sending")
                while self.rooms.get(project_name, None) is not None:
                    await asyncio.sleep(0.001)

            except websockets.exceptions.ConnectionClosedError:
                print("[SUB]: CONNECTION ERROR")
                self.rooms[project_name]['subscribers'].remove(websocket)

        elif role == 'pub':
            print("[PUB]: Receiving project name")
            project_name = loads(await websocket.recv())['room']
            self.rooms[project_name] = {'subscribers': [], 'available': True, 'status': 0, 'files': set()}

            print("[PUB]: Enter to console")
            try:
                while True:
                    package = loads(await websocket.recv())
                    if package['type'] == 'refresh':
                        await websocket.send(
                            dumps(
                                subscribers_package(
                                    [f"{ws.remote_address[0]}:{ws.remote_address[1]}"
                                     for ws in self.rooms[project_name]['subscribers']]
                                )
                            )
                        )
                    elif package['type'] == 'sync':
                        break
                    else:
                        print(f'Unexpected package: {package}')

                print("[PUB]: Close room")
                self.rooms[project_name]['available'] = False

                print("[PUB]: Receiving hashes")
                hashes = await self.receive_chunked_package(websocket)

                print("[PUB]: Sending hashes")
                await asyncio.gather(*[
                    self.send_chunked_package(
                        sub,
                        split_package_to_chunks(dumps(hashes))
                    ) for sub in self.rooms[project_name]['subscribers']])

                print("[PUB]: Waiting to receive all missed packages")
                while self.rooms[project_name]['status'] != len(self.rooms[project_name]['subscribers']):
                    await asyncio.sleep(0.01)

                print("[PUB]: Transmit missed files")
                await self.send_chunked_package(
                    websocket,
                    split_package_to_chunks(
                        dumps(missed_package(list(self.rooms[project_name]['files'])))
                    )
                )

                print("[PUB]: Transmit chunks")
                while True:
                    package = loads(await websocket.recv())
                    if package['type'] == 'complete':
                        continue
                    elif package['type'] == 'close':
                        break
                    elif package['type'] in ('chunk', 'full'):
                        package = dumps(package)
                        await asyncio.gather(*[sub.send(package) for sub in self.rooms[project_name]['subscribers']])

                await asyncio.gather(*[sub.send(dumps(complete())) for sub in self.rooms[project_name]['subscribers']])
                print("Successful")

            except websockets.ConnectionClosedError:
                print("[PUB]: CONNECTION ERROR")
                print("[PUB]: DISCONNECTING SUBS")
                await asyncio.gather(*[sub.close() for sub in self.rooms[project_name]['subscribers']])

            del self.rooms[project_name]

    @staticmethod
    async def receive_chunked_package(websocket: WebSocketServerProtocol):
        full_package = b''
        while True:
            package = loads(await websocket.recv())
            if package['type'] == 'complete':
                break
            elif package['type'] in ('chunk', 'full'):
                full_package += package['data']
        return loads(full_package)

    @staticmethod
    async def send_chunked_package(websocket: WebSocketServerProtocol, chunk_generator):
        for chunk, path in chunk_generator:
            await websocket.send(
                dumps(
                    data_chunk_package(chunk, path)
                )
            )
        await websocket.send(dumps(complete()))


__all__ = [
    'Server'
]
