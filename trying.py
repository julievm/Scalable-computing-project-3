# import socket

# def send_udp_broadcast(message, port):
#     # Create a UDP socket
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # Set the socket option to enable broadcasting
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

#     # Define the broadcast address and port
#     broadcast_address = '10.35.70.41'

#     try:
#         # Send the message to the broadcast address
#         sock.sendto(message.encode(), (broadcast_address, port))
#         print(f"Message sent to {broadcast_address}:{port}")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#     finally:
#         sock.close()

# # Example usage
# send_udp_broadcast("Hello, Raspberry Pis!", 33000)


# import socket
# from time import sleep

# def main():
#     interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
#     print(interfaces)
#     allips = [ip[-1][0] for ip in interfaces]
#     print(allips)
#     msg = b'hello world, broadcasting....'
#     while True:
#         for ip in allips:
#             print(f'sending on {ip}')
#             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
#             sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#             sock.bind((ip,0))
#             sock.sendto(msg, ("255.255.255.255", 33000))
#             sock.close()

#         sleep(2)
# main()


import asyncio
import json
import logging
import threading
import socket
import time
from asyncio import DatagramTransport, StreamWriter, StreamReader, Task
from typing import List, Tuple, Dict

print("Creating UDP server...")


class _Address:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def __eq__(self, other):
        return self.host == other.host and self.port == other.port

    def __hash__(self):
        return hash((self.host, self.port))

    def __str__(self):
        return f"{self.host}:{self.port}"


class UDP:
    def __init__(self) -> None:
        self.udp_port = 33000
        self.tcp_port = 33001
        self.hostname = socket.gethostbyname(socket.gethostname())
        self.announcement = {
            "heartbeat": "ALIVE",
            "NEIGHBOURS": self.hostname
        }

    async def start_udp(self):
        # Listen for announcements
        class Protocol:
            def connection_made(_, transport: DatagramTransport):
                print(f"UDP transport established: {transport}")

            def connection_lost(_, e: Exception):
                print(f"UDP transport lost: {e}")

            def datagram_received(_, data: bytes, addr: Tuple[str, int]):
                self._on_udp_data(data, _Address(*addr[0:2]))

            def error_received(_, e: OSError):
                print(f"UDP transport error: {e}")

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(lambda: Protocol(), local_addr=("0.0.0.0", self.udp_port),
                                                                  allow_broadcast=True)

        # Regularly broadcast announcements
        while True:
            print("Sending peer announcement...")
            transport.sendto(json.dumps(self.announcement).encode('utf-8'), ("255.255.255.255", self.udp_port))
            await asyncio.sleep(20)

    def _on_udp_data(self, data: bytes, addr: _Address):
        print(f"Received data {data=}")
        print(str(addr))
        pass
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"Received connection from {addr}")

        while True:
            data = await reader.read(100)
            if not data:
                break

            message = data.decode('utf-8')
            print(f"Received {message} from {addr}")

            response = "Hi"
            writer.write(response.encode('utf-8'))
            await writer.drain()

        print(f"Closing connection with {addr}")
        writer.close()
        await writer.wait_closed()

    async def start_tcp_server(self):
        server = await asyncio.start_server(
            self.handle_client, self.hostname, self.tcp_port)
        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()


    # async def start_tcp(self):
    #     print("Creating TCP server...")
    #     server = await asyncio.start_server(self._on_tcp_conn, self.hostname, self.port)
    #     async with server:
    #         await server.serve_forever()

    # async def _on_tcp_conn(self, reader, writer):
    #     print(f"Handling TCP connection from {writer.get_extra_info('peername')}...")
    #
    #     # Read entire message
    #     msg_bytes = await reader.read()
    #     writer.close()
    #     msg = json.loads(msg_bytes.decode())

        # Insert new data into data and forward to other peers
        # print(f"Received update to data: {msg}")
        # other_addrs = [peer for peer in self.peers if peer != writer.get_extra_info('peername')]
        # await self._send_to_addrs(msg_bytes, other_addrs)

    # async def _send_to_addrs(self, message, addrs):
        #for host, port in addrs:
            #await self.send_request(host, port, message)

    async def send_request(self, host, port, message):
        print(f"Sending request to {host}:{port}...")
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(message.encode('utf-8'))
        await writer.drain()

        response = await reader.read()
        print(f"Received response from {host}:{port}: {response.decode()}")

        writer.close()
        await writer.wait_closed()

        return response.decode()

    async def send_request(self, host, port, message):
        print(f"Sending request to {host}:{port}...")
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(message.encode('utf-8'))
        await writer.drain()

        response = await reader.read(100)  # Read the response
        print(f"Received response from {host}:{port}: {response.decode()}")

        writer.close()
        await writer.wait_closed()

        return response.decode()

async def tcp_client(message, host, port, retry_interval=5):
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)

            print(f'Sending: {message}')
            writer.write(message.encode())

            data = await reader.read(100)
            print(f'Received: {data.decode()}')

            print('Closing the connection')
            writer.close()
            await writer.wait_closed()

            break  # Exit the loop after successful communication

        except (ConnectionRefusedError, OSError) as e:
            print(f"Connection to {host}:{port} refused, retrying in {retry_interval} seconds...")
            await asyncio.sleep(retry_interval)
        except Exception as e:
            print(f"An error occurred: {e}, retrying in {retry_interval} seconds...")
            await asyncio.sleep(retry_interval)

def run_command_loop(udp, loop):
    while True:
        command = input("Enter command (send, quit): ").strip().lower()
        if command == "send":
            request_data = input("Enter interest package (eg. bus1/temperature): ").strip().lower()

            asyncio.run_coroutine_threadsafe(udp.send_request("rasp-034.berry.scss.tcd.ie", 33001, request_data), loop)
        elif command == "quit":
            break

async def main():
    udp = UDP()
    print("Starting server")

    client_task = asyncio.create_task(udp.start_udp())
    server_task = asyncio.create_task(udp.start_tcp_server())

    # Get the current event loop for the main thread
    loop = asyncio.get_running_loop()

    # Start the command loop in a separate thread, passing the event loop
    command_thread = threading.Thread(target=run_command_loop, args=(udp, loop), daemon=True)
    command_thread.start()

    # Keep running until the command loop stops the event loop
    try:
        await asyncio.gather(server_task, client_task)
    except asyncio.CancelledError:
        # The server task has been cancelled, meaning we're shutting down
        pass

asyncio.run(main())

