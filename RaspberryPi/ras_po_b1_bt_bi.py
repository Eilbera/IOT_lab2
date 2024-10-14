import socket
import asyncio
import websockets
import json
import time
import threading

def create_bluetooth_socket():
    return socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

def bluetooth_send(sock, message):
    print(f"Sending via Bluetooth: {message}")
    sock.send(message.encode('utf-8'))

def bluetooth_receive(sock):
    try:
        message = sock.recv(1024)
        if message:
            print(f"Received via Bluetooth: {message.decode('utf-8')}")
            return message
        else:
            print("No data received from Bluetooth")
            return None
    except socket.error as e:
        print(f"Error receiving Bluetooth data: {e}")
        return None

def bluetooth_server(mac_address, port=1):
    server_sock = create_bluetooth_socket()
    server_sock.bind((mac_address, port))
    server_sock.listen(1)
    print("Waiting for Bluetooth connection...")
    client_sock, address = server_sock.accept()
    print(f"Bluetooth server connected to {address}")
    return client_sock

def bluetooth_client(mac_address, port=1):
    sock = create_bluetooth_socket()
    sock.connect((mac_address, port))
    print(f"Bluetooth client connected to {mac_address}")
    return sock

async def websocket_to_bluetooth(websocket, queue):
    try:
        async for message in websocket:
            print(f"Received via WebSocket: {message}")
            await queue.put(message)
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")

async def bluetooth_to_websocket(websocket):
    try:
        while True:
            message = await asyncio.get_event_loop().run_in_executor(None, bluetooth_receive, bt_sock)
            if message:
                print(f"Sending to WebSocket: {message.decode('utf-8')}")
                await websocket.send(message.decode('utf-8'))
            else:
                await asyncio.sleep(0.1)
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")

async def main():
    uri = "ws://127.0.0.1:65432"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket server at {uri}")
        try:
            queue = asyncio.Queue()
            await asyncio.gather(
                websocket_to_bluetooth(websocket, queue),
                bluetooth_to_websocket(websocket),
                handle_websocket_responses(queue)
            )
        except Exception as e:
            print(f"Error in main: {e}")

async def handle_websocket_responses(queue):
    try:
        while True:
            message = await queue.get()
            print(f"Received from WebSocket server: {message}")
            try:
                car_state = json.loads(message)
                print(f"Car State: {json.dumps(car_state, indent=2)}")
                await asyncio.get_event_loop().run_in_executor(None, bluetooth_send, bt_sock, message)
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {message}")
    except Exception as e:
        print(f"Error in handle_websocket_responses: {e}")

if __name__ == "__main__":
    mac_address = "D8:3A:DD:6D:C7:55"
    
    bt_sock = bluetooth_server(mac_address)
    
    asyncio.run(main())