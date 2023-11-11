import socket
import threading
import json
import random
import time
import re
from base_utils import *

RUNNING = True
VEHICLE_TYPE = VEHICLES[0]
# Vehicle number can be passed in as second command-line argument
VEHICLE_NUM = 1


def send_advertising_port(router_tuple, data):
    for tries in range(2):
        try:
            router_host, router_port = router_tuple[tries]
            print(f'Populating central Dir {data} {router_host}:{router_port}')
            nodelist=send_and_recieve_raw_data(router_host, router_port, data)
            break
        except Exception:
            continue
    return nodelist


def send_and_recieve_raw_data(host, port, data):
    print(f'We are sending {data} to {host}:{port}')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((host, port))
        s.sendall(encrypt_msg(data))
        response = decrypt_msg(s.recv(1024))
        return response

def send_raw_data(host, port, data):
    print(f'We are sending {data} to {host}:{port}')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((host, port))
        s.sendall(encrypt_msg(data))


def send_data_back(conn, data):
    try:
        conn.send(encrypt_msg(data))
    except Exception as e:
        print(f'Exception while sending data to router: {e}')
    

def send_msg(msg):
    for tries in range(2):
        try:
            router_host, router_port = INTEREST_ROUTER_TUPLE[tries]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((router_host, router_port))
            s.send(encrypt_msg(msg))
            answer = s.recv(1024)
            decrypted = decrypt_msg(answer)
            s.close()
            return decrypted
        except Exception:
            continue

def process_data(data):
    if data is None or data.startswith('404 not found'):
        print("No data!")
    elif data == PAYLOAD_TOO_LARGE_STRING or data == MULTIPLE_CHOICES_STRING:
        pass  # Cause we need to wait for a direct transfer
    else:
        print(data)
        [datatype, datavalue] = data.split(' ')
        [vehicle, vehicle_property] = datatype.split('/')

        if vehicle_property == "fuel_sensor" and int((datavalue.replace('%', ''))) < 10:
            print(f'Less than 10% of fuel left for vehicle {vehicle}.')
        if vehicle_property == "maintain" and datavalue == 'True':
            print(f'Vehicle {vehicle} needs maintenance.')
        if vehicle_property == "track_temperature" and int(datavalue) > 50:
            print(f'Track temperature for train {vehicle} is too high.')

class Node:
    def __init__(self, port, type, number):
        self.host = socket.gethostname()
        self.port = port
        self.fib = []  # Forwarding Information Base, mapping data names to next-hop (host, port)
        self.data_store = {}  # Data the node is responsible for   FIB - Device name    Data Name
        self.peers = []  # List of peers (host, port)
        self.vehicle_type= type
        self.vehicle_number=number
        
    def add_fib_entry(self,node_list):
        # node_list=request_data_cd(data_name)
        for x in node_list:
            self.fib.append(x)
            # self.peers.append(x)

    def update_fib_entry(self,data):
        #{self.vehicle_type}/{self.vehicle_number}
        self.fib.append(data)
        
    def add_data(self, data_name, data):
        self.data_store[data_name] = data
    
    def add_peer(self, peer):
        self.peers.append(peer)

    def generate_boolean(self):
        return random.choice(['True', 'False'])


    def generate_destination(self):
        return random.choice(['Harbour', 'City_Hall', 'College', 'Trinity_College_Dublin,Dublin_2', 'Liv_Student,four_courts'])


    def generate_temperature(self):
        return str(random.randint(-10, 40))



    def generate_gps_position(self):
        return str(random.randint(-9000, 9000) / 100) + ',' + str(random.randint(-9000, 9000) / 100)


    def generate_percentage(self):
        return str(random.randint(0, 100)) + '%'


    def generate_integer(self):
        return str(random.randint(0, 300))


    def generate_data(self, vehicle, specific_type):
        if specific_type == 'waiting':
            return self.generate_boolean()
        elif specific_type == 'maintain':
            return self.generate_boolean()
        elif specific_type == 'in_service':
            return self.generate_boolean()
        elif specific_type == 'ambient_temperature':
            return self.generate_temperature()
        elif specific_type == 'position':
            if vehicle == 'train' or vehicle == 'metro' or vehicle == 'tram':
                return self.generate_track_position()
            else:
                return self.generate_gps_position()
        elif specific_type == 'fuel_sensor':
            return self.generate_percentage()
        elif specific_type == 'passengers':
            return self.generate_integer()
        elif specific_type == 'destination':
            return self.generate_destination()
        else:
            print(f'Error: data type {vehicle}/{specific_type} not known')

    
    def handle_connection(self, client_socket, addr):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                message = json.loads(message)
                if message['type'] == 'interest':
                    data_name = message['data_name']
                    if data_name in self.data_store:
                        # If we have the data, send it back
                        response = json.dumps({'type': 'data', 'data_name': data_name, 'data': self.data_store[data_name]})
                        client_socket.sendall(response.encode('utf-8'))
                    elif data_name in self.fib:
                        # Forward the interest to the next hop
                        next_hop = self.fib[data_name]
                        self.forward_interest(next_hop, data_name)
            except Exception as e:
                print(f"Error handling connection: {e}")
                break
        client_socket.close()
    
    def forward_interest(self, next_hop, data_name):
        next_host, next_port = next_hop
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((next_host, next_port))
            interest = json.dumps({'type': 'interest', 'data_name': data_name})
            s.sendall(interest.encode('utf-8'))
            data = s.recv(1024).decode('utf-8')
            print(f"Received data for {data_name}: {data}")
    
    

    # def advertise(delay):
    #     while RUNNING:
    #         advertising_message = f'HOST {get_host(socket)} PORT {PRODUCER_PORT_COMPAT} ACTION '
    #         for data_type in DATA_TYPES[VEHICLE_TYPE]:
    #             advertising_message += f'{VEHICLE_TYPE}{VEHICLE_NUM}/{data_type},'
    #         advertising_message = advertising_message[:-1]  # Remove trailing comma
    #         try:
    #             send_advertising_data(ROUTER_TUPLE, advertising_message)
    #         except Exception as e:
    #             print(f"Failed to advertise {e}")

    #         time.sleep(delay)

    def poptocentral(self):
        advertising_message = f'HOST {(self.host)} PORT {self.port} NODE {self.vehicle_type}{self.vehicle_number}'
        list=send_advertising_port(ROUTER_TUPLE, advertising_message)
        self.add_fib_entry(list)
    
    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((get_host(socket), self.port))
            s.listen(5)
            while RUNNING:
                conn, addr = s.accept()
                with conn:
                    print(f"Connection started by {addr}")

                    raw_data = conn.recv(1024)
                    requested_data = decrypt_msg(raw_data)
                    split_data = requested_data.split(' ')
                    consumer_host = None

                    if split_data[0] == "UPDATE":
                        self.update_fib_entry(split_data[1:])
                        continue

                    if len(split_data) > 1:
                        requested_data = split_data[0]
                        consumer_host = split_data[1]
                        consumer_port = split_data[2]

                    print(f'Data {requested_data} was requested')

                    # Gather the data
                    [vehicle_string, datatype] = requested_data.split('/')
                    vehicle_num = re.findall(r'\d+|\*', vehicle_string)[0]
                    vehicle_type = vehicle_string.replace(vehicle_num, '')
                    data_to_send = ""
                    if VEHICLE_TYPE == vehicle_type:
                        data_to_send = f'{VEHICLE_TYPE}{VEHICLE_NUM}/{datatype} {self.generate_data(vehicle_type, datatype)}'\

                    # Whether a direct transfer was requested
                    # Apparently string 'False' is True in python -> want to kms
                    # direct_transfer = split_data[2] == 'True' if (len(split_data) > 2) else False
                    # if not direct_transfer:
                    #     direct_transfer = consumer_host is not None and len(data_to_send) > LARGE_DATA_THRESHOLD

                    # If data too large send p2p to consumer
                    # We check we were sent IP to be compatible with common protocol
                    # if direct_transfer:
                    print("Sending via direct transfer...")
                        # send_data_back(conn, PAYLOAD_TOO_LARGE_STRING)
                        # Send large data directly to peer on separate thread
                    threading.Thread(target=send_raw_data,args=(consumer_host, consumer_port, data_to_send)).start()
                    # else:
                    #     send_data_back(conn, data_to_send)
                    #     print("We sent the data back:", data_to_send)

        

    # def server_thread(self):
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #         s.bind((self.host, self.port))
    #         s.listen()
    #         print(f"Node started on {self.host}:{self.port}")
    #         while True:
    #             client_socket, addr = s.accept()
    #             threading.Thread(target=self.handle_connection, args=(client_socket, addr), daemon=True).start()
    
    def run(self):
        threads = [
        # Listen for data requests from the router
        threading.Thread(target=self.poptocentral, daemon=True),

        
        threading.Thread(target=self.listen, daemon=True),
        
        # threading.Thread(target=self.req, daemon=True),
        # threading.Thread(target=self.advertise, daemon=True),
        ]
        for thread in threads:
            thread.start()
        # This is where you could add the code to join a network, exchange FIB information, etc.
        # For simplicity, this is omitted.

# Example usage:
if __name__ == '__main__':
    node_a = Node(8000)
    node_b = Node(8001)
    
    node_a.add_data('data1', 'This is data 1')
    
    # node_a.add_fib_entry('data1', ('localhost', 8001))
    # node_b.add_fib_entry('data1', ('localhost', 8000))
    
    node_a.run()
    node_b.run()
    
    # Now node_a can request data from node_b and vice versa
