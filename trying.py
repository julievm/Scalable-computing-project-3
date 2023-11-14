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
from datetime import datetime

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
    def __init__(self, name) -> None:
        self.udp_port = 33000
        self.tcp_port = 33001
        self.vehicle_name = name
        self.hostname = socket.gethostbyname(socket.gethostname())
        self.announcement = {
            "heartbeat": "ALIVE",
            "NEIGHBOURS": self.hostname,
            "vehicle_name": self.vehicle_name
        }
        self.fib = {}
        self.sensor = {}

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
        transport, protocol = await loop.create_datagram_endpoint(lambda: Protocol(),
                                                                  local_addr=("0.0.0.0", self.udp_port),
                                                                  allow_broadcast=True)

        # Regularly broadcast announcements
        while True:
            print("Sending peer announcement...")
            transport.sendto(json.dumps(self.announcement).encode('utf-8'), ("255.255.255.255", self.udp_port))
            await asyncio.sleep(20)

    class UDP:
        # ... (existing parts of your UDP class)

        async def start_local_udp_broadcast(self):
            """Broadcast a message to the local machine on a specific port."""
            local_broadcast_address = '127.255.255.255'  # Local broadcast address
            local_broadcast_port = 33002  # The port you want to broadcast on

            loop = asyncio.get_running_loop()

            # Since we are broadcasting locally, we do not need the SO_BROADCAST option
            # Listen for announcements
            class LocalProtocol:
                def connection_made(_, transport: DatagramTransport):
                    print(f"Local UDP transport established: {transport}")

                def connection_lost(_, e: Exception):
                    print(f"Local UDP transport lost: {e}")

                def datagram_received(_, data: bytes, addr: Tuple[str, int]):
                    self._on_udp_data(data, _Address(*addr[0:2]))

                def error_received(_, e: OSError):
                    print(f"Local UDP transport error: {e}")

            # Create a datagram endpoint and start broadcasting locally
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: LocalProtocol(),
                local_addr=("0.0.0.0", local_broadcast_port)
            )

            try:
                while True:
                    print("Sending local peer announcement...")
                    # Here we are using the local broadcast address to stay within the Pi
                    transport.sendto(json.dumps(self.announcement).encode('utf-8'),
                                     (local_broadcast_address, local_broadcast_port))
                    await asyncio.sleep(20)
            finally:
                transport.close()

    async def decrement_ttl(self):
        while True:
            try:
                for key in list(self.fib.keys()):
                    # Decrement the TTL
                    self.fib[key][2] -= 1
                    # Remove the entry if the TTL reaches zero
                    if self.fib[key][2] <= 0:
                        del self.fib[key]
                # Wait for 1 second before decrementing again
                # await asyncio.sleep(1)
            except RuntimeError:
                self.fib = {}

            try:
                for key in self.sensor.keys():
                    # Decrement the TTL
                    self.sensor[key]['ttl'] -= 1
                    # Remove the entry if the TTL reaches zero
                    if self.sensor[key]['ttl'] <= 0:
                        del self.sensor[key]
                # Wait for 1 second before decrementing again
            except RuntimeError:
                self.sensor = {}
            await asyncio.sleep(1)

    def add_to_fib(self, data: bytes, addr: _Address):
        # Decode the bytes data to string and parse it as JSON
        data_string = data.decode('utf-8')
        try:
            data_dict = json.loads(data_string)
            name = data_dict['vehicle_name']
            host = addr.host
            port = addr.port
            ttl = 25
            value = [host, port, ttl]

            # Update TTL if the entry exists, else add a new entry
            if name in self.fib:
                self.fib[name][2] = ttl
            else:
                self.fib[name] = value
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON data: {e}")
        except KeyError as e:
            print(f"Key error: {data_string} does not contain a vehicle_name")

    def _on_udp_data(self, data: bytes, addr: _Address):
        # print(f"Received data {data=}")
        self.add_to_fib(data, addr)
        print(self.fib)
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
            type = message.split('/')[1]
            name = message.split('/')[0]

            if type in self.sensor.keys():
                response = self.sensor[type]
            else:
                response = "REQUESTED DATA DOES NOT EXIST..."
            # response = "Hi"
            writer.write(json.dumps(response).encode('utf-8'))
            await writer.drain()

        print(f"Closing connection with {addr}")
        writer.close()
        await writer.wait_closed()

    async def handle_sensor_data(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(100)  # Read up to 100 bytes
        message = json.loads(data.decode('utf-8'))
        addr = writer.get_extra_info('peername')

        # print(f"Received {message} from {addr}")

        # store_to_repo(message)
        # Process the sensor data here
        self.sensor[message["name"]] = message

        # Close the connection
        # print("Close the connection")
        writer.close()

    async def start_tcp_server(self):
        server = await asyncio.start_server(
            self.handle_client, self.hostname, self.tcp_port)
        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    async def start_sensor_server(self):
        server = await asyncio.start_server(self.handle_sensor_data, '127.0.0.1', 33003)
        addr = server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        async with server:
            await server.serve_forever()

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
            vehicle_name = request_data.split('/')[0]
            if vehicle_name in list(udp.fib.keys()):
                host = udp.fib[vehicle_name][0]
            else:
                print("It doesn't exist")
                continue

            host = host.split('.')[3]
            hoststring = f'rasp-0{host}.berry.scss.tcd.ie'
            asyncio.run_coroutine_threadsafe(udp.send_request(hoststring, udp.tcp_port, request_data), loop)
        elif command == "quit":
            break


async def main():
    udp = UDP('car1')
    print("Starting server")

    client_task = asyncio.create_task(
        udp.start_udp())  # broadcast announcement - every time it receives - it updates the fib
    server_task = asyncio.create_task(udp.start_tcp_server())
    ttl_task = asyncio.create_task(udp.decrement_ttl())
    sensor_task = asyncio.create_task(udp.start_sensor_server())

    # Get the current event loop for the main thread
    loop = asyncio.get_running_loop()

    # Start the command loop in a separate thread, passing the event loop
    command_thread = threading.Thread(target=run_command_loop, args=(udp, loop), daemon=True)
    command_thread.start()

    # Keep running until the command loop stops the event loop
    try:
        await asyncio.gather(server_task, client_task, ttl_task, sensor_task)
    except asyncio.CancelledError:
        # The server task has been cancelled, meaning we're shutting down
        pass


asyncio.run(main())

