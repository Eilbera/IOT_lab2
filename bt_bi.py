import asyncio
import websockets
import socket
import threading

def create_bluetooth_socket():
    return socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

def bluetooth_send(sock, message):
    print(f"Sending over Bluetooth: {message}")
    sock.send(message.encode('utf-8'))

def bluetooth_receive(sock):
    message = sock.recv(1024)
    print(f"Received over Bluetooth: {message.decode('utf-8')}")
    return message

def bluetooth_client(mac_address, port=1):
    sock = create_bluetooth_socket()
    sock.connect((mac_address, port))
    print(f"Bluetooth client connected to {mac_address}")
    return sock

async def websocket_to_bluetooth(websocket, bt_sock):
    try:
        async for message in websocket:
            print(f"Received from WebSocket: {message}")
            bluetooth_send(bt_sock, message)
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")

def bluetooth_to_websocket(bt_sock, websocket):
    while True:
        try:
            message = bluetooth_receive(bt_sock)
            asyncio.run(websocket.send(message.decode('utf-8')))
        except Exception as e:
            print(f"Error in Bluetooth receiving: {e}")
            break

async def handle_connection(websocket, path, bt_sock):
    print("New WebSocket connection established")
    ws_to_bt_task = asyncio.create_task(websocket_to_bluetooth(websocket, bt_sock))
    bt_to_ws_thread = threading.Thread(target=bluetooth_to_websocket, args=(bt_sock, websocket))
    bt_to_ws_thread.start()
    
    await ws_to_bt_task
    bt_to_ws_thread.join()

async def main(bt_sock):
    server = await websockets.serve(
        lambda ws, path: handle_connection(ws, path, bt_sock),
        "localhost", 65432
    )
    print("WebSocket server started on localhost:65432")
    await server.wait_closed()

if __name__ == "__main__":
    mac_address = "D8:3A:DD:6D:C7:55"
    
    bt_sock = bluetooth_client(mac_address)
    
    asyncio.run(main(bt_sock))