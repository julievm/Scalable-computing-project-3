import asyncio
from datetime import datetime
import json
import socket
import sys
import random
import threading
from typing import Tuple

NODE_PORT = 33001

    
async def send_sensor_data(port, sensortype):
    while True:
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        announcement = {
                    "name": sensortype,
                    "value": generate_sensor_data(sensortype),
                    "timestamp": str(datetime.now()),
                    "ttl": 10
                }
        print("inside asnyc: ", generate_sensor_data(sensortype))
        writer.write(json.dumps(announcement).encode('utf-8'))
        await writer.drain()  # Ensure the message is sent
        await asyncio.sleep(5)
 
def generate_temperature():
    print("random data: ",str(random.randint(-10, 40)))
    return str(random.randint(-10, 40))

def generature_pressure():
    return str(random.randint(900, 1100))

def generate_gps_position():
    return str(random.randint(-9000, 9000) / 100) + ',' + str(random.randint(-9000, 9000) / 100)

def generate_radar_data():
    distance = random.uniform(0, 1000)
    velocity = random.uniform(-1000, 1000)
    return {'distance': round(distance, 2), 'velocity': round(velocity, 2)}

def generate_humidity():
    return str(random.uniform(-2,2))

def generate_sensor_data(sensorType):
    if sensorType == 'temperature':
        return generate_temperature()
    if sensorType == "position":
        return generate_gps_position()
    if sensorType == 'radar':
        return generate_radar_data()
    if sensorType == 'pressure':
        return generature_pressure()
    if sensorType == 'humidity':
        return generate_humidity()

async def main():
    port = 33003
    sensortype = 'temperature'
    await send_sensor_data(port, sensortype)
    
asyncio.run(main())

# car1/temperature