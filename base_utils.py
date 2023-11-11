#!/usr/bin/env python3

import base64
from cryptography.fernet import Fernet

# ROUTER_HOST = '10.35.70.24' # For testing on Pi
ROUTER_HOST = '127.0.0.1'  # For testing locally
ROUTER_IP_1 = '10.35.70.31'

# Set of ports that are compatible with common protocol
ROUTER_ADVERTISING_PORT_COMPAT = 33334  # Port router expects to receive advertising messages on
ROUTER_REQUEST_PORT_COMPAT = 33310  # Port router expects data requests to come in from
PRODUCER_PORT_COMPAT = 33301  # Port the producer expects requests to come in from
CONSUMER_PORT_COMPAT = 33302  # Port consumer expects requested data to come in from

# Data size threshold after which we use a direct peer transfer instead of going through the router
LARGE_DATA_THRESHOLD = 30
PAYLOAD_TOO_LARGE_STRING = "HTTP/1.1 413 Payload Too Large"
MULTIPLE_CHOICES_STRING = "HTTP/1.1 300 Multiple Choices"

ROUTER_TUPLE = [(ROUTER_HOST, ROUTER_ADVERTISING_PORT_COMPAT), (ROUTER_IP_1, ROUTER_ADVERTISING_PORT_COMPAT)]
INTEREST_ROUTER_TUPLE = [(ROUTER_HOST, ROUTER_REQUEST_PORT_COMPAT), (ROUTER_IP_1, ROUTER_REQUEST_PORT_COMPAT)]
VEHICLES = ['bus', 'train', 'tram', 'metro', 'taxi']
DATA_TYPES = dict(
    bus=['position', 'passengers', 'waiting', 'maintain', 'in_service', 'destination', 'ambient_temperature',
         'fuel_sensor'],
    tram=['position', 'passengers', 'waiting', 'maintain', 'in_service', 'destination',
          'ambient_temperature', 'track_temperature'],
    taxi=['position', 'passengers', 'waiting', 'maintain', 'in_service', 'destination',
          'ambient_temperature', 'fuel_sensor'],
    train=['position', 'passengers', 'waiting', 'maintain', 'in_service', 'destination',
           'ambient_temperature', 'fuel_sensor', 'locomotive', 'track_temperature'],
    metro=['position', 'passengers', 'waiting', 'maintain', 'in_service', 'destination',
           'ambient_temperature', 'locomotive', 'track_temperature']
)

ENCRYPTION_KEY = b'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg='

cipher_suite = Fernet(ENCRYPTION_KEY)


def get_host(socket):
    """Get Pi's hostname from current socket"""
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


# Take string, return encrypted byte array
def encrypt_msg(to_encode):
    ascii_encoded = to_encode.encode("ascii")
    base64_bytes = base64.b64encode(ascii_encoded)
    encrypted = cipher_suite.encrypt(base64_bytes)
    return encrypted


# Take a byte array, decrypt and return string
def decrypt_msg(to_decode):
    decrypted = cipher_suite.decrypt(to_decode)
    sample_string_bytes = base64.b64decode(decrypted)
    return sample_string_bytes.decode("ascii")


def tabular_display(temp_dict):
    print("{:<25} | {:<15}".format('ACTION', 'IP_ADDR'))
    for key, val in temp_dict.items():
        print("{:<25} | {:<15}".format(key, str(val)))
