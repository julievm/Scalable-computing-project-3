import socket
import threading
import json
from base_utils import *


def split_str(act_string):
    temp_str = act_string[1].replace('[', '').replace(']', '').replace(' ', '').lower()
    return str(temp_str)
class CentralDirectoryServer:
    def __init__(self, host, port):
        self.peers = {}  # Store active nodes with their info
        self.host = host
        self.port = port

    def start(self):
        # Start the server in a new thread
        server_thread = threading.Thread(target=self.run_server, daemon=True)
        server_thread.start()
        print(f"Central Directory Server started on {self.host}:{self.port}")

    def send_to_all(self, peer):
        # peer is a tuple containing (host, port, action_list)
        for action, peer_info in self.peers.items():
            # Unpack the peer_info to get the host and port
            peer_host, peer_port = peer_info
            # Don't send the peer to itself
            if (peer_host, peer_port) == (peer[0], peer[1]):
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                    peer_socket.connect((peer_host, peer_port))
                    # Prepare the peer information to send (you might need to adjust the format)
                    peer_data = f"UPDATE {peer[2]}"
                    # Encrypt the message before sending
                    encrypted_data = encrypt_msg(peer_data)
                    peer_socket.sendall(encrypted_data)
            except Exception as e:
                print(f"Error sending to {peer_host}:{peer_port} - {e}")

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    data = client_socket.recv(1024)
                    if not data:
                        return
                    decrypted = decrypt_msg(data)
                    dataMessage = decrypted.split(' ')
                    action_list = split_str(data.split('NODE '))
                    host = dataMessage[1]
                    port = int(dataMessage[3])
                    peer = (host, port, action_list)
                    client_socket.sendall(encrypt_msg(self.peers))
                    self.send_to_all(peer)
                    self.peers[action_list]=[host,port]

                except Exception as e:
                    print(f"An error occurred: {e}")
                finally:
                    client_socket.close()

    def register_node(self, message, addr):
        node_id = message.get('node_id')
        node_info = {'address': addr, 'details': message.get('details', {})}
        self.active_nodes[node_id] = node_info
        print(f"Node {node_id} registered from {addr}")

    def unregister_node(self, message, addr):
        node_id = message.get('node_id')
        if node_id in self.active_nodes:
            del self.active_nodes[node_id]
            print(f"Node {node_id} unregistered")

    def list_nodes(self, client_socket):
        # Send the list of nodes to the requester
        node_list = json.dumps(self.active_nodes).encode('utf-8')
        client_socket.sendall(node_list)
        print("Node list sent to a client")

if __name__ == '__main__':
    # Run the directory server
    directory_server = CentralDirectoryServer('localhost', 5000)
    directory_server.start()

    # Keep the server running
    input("Press Enter to stop the server...\n")
