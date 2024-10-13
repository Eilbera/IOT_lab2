import asyncio
import websockets
import json
import time
from Motor import Motor
from Ultrasonic import Ultrasonic
from Buzzer import Buzzer
from ADC import Adc

def beep(ms):
    buzzer.run('1')
    time.sleep(ms)
    buzzer.run('0')

def morse_beep(message):
    morse_code = {
        'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
        'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
        'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
        'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
        'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
        '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
        '8': '---..', '9': '----.'
    }
    
    for char in message.upper():
        if char == ' ':
            time.sleep(0.7)  
        elif char in morse_code:
            for symbol in morse_code[char]:
                if symbol == '.':
                    beep(0.1)
                elif symbol == '-':
                    beep(0.3)
                time.sleep(0.1)  
            time.sleep(0.3) 

class BatteryMonitor:
    def __init__(self, window_size=30):
        self.window_size = window_size
        self.readings = []
        self.timestamps = []
        self.last_percentage = None
        self.hysteresis = 2 
        self.load_threshold = 0.3  
        self.rest_voltage = None

    def add_reading(self, voltage, is_moving):
        current_time = time.time()
        self.readings.append((voltage, is_moving))
        self.timestamps.append(current_time)
        
        while len(self.readings) > self.window_size:
            self.readings.pop(0)
            self.timestamps.pop(0)
        
        if not is_moving and (self.rest_voltage is None or voltage > self.rest_voltage):
            self.rest_voltage = voltage

    def get_filtered_voltage(self):
        if not self.readings:
            return None

        rest_voltages = [v for v, moving in self.readings if not moving]
        if rest_voltages:
            return max(rest_voltages)
        else:
            return max(v for v, _ in self.readings)
    
    def calculate_percentage(self, voltage):
        levels = [
            (8.4, 100), (8.2, 90), (8.0, 80), (7.8, 70),
            (7.6, 60), (7.4, 50), (7.2, 40), (7.0, 30),
            (6.8, 20), (6.4, 10), (6.0, 0)
        ]
        for i, (v, p) in enumerate(levels):
            if voltage >= v:
                if i == 0:
                    return 100
                prev_v, prev_p = levels[i-1]
                return prev_p + (p - prev_p) * (voltage - v) / (prev_v - v)
        return 0

    def update(self, voltage, is_moving):
        self.add_reading(voltage, is_moving)
        filtered_voltage = self.get_filtered_voltage()
        
        if filtered_voltage is None:
            return voltage, self.last_percentage or 0

        new_percentage = self.calculate_percentage(filtered_voltage)
        
        if self.last_percentage is None or abs(new_percentage - self.last_percentage) > self.hysteresis:
            self.last_percentage = new_percentage
        
        return filtered_voltage, self.last_percentage

PWM = Motor()
ultrasonic = Ultrasonic()
buzzer = Buzzer()
adc = Adc()
battery_monitor = BatteryMonitor()

autonomous_mode = False
obstacle_distance = 20  
is_moving = False

car_state = {
    "direction": "Stopped",
    "speed": 0.0,
    "distance": 0.0,
    "ultrasonic": 0.0,
    "bluetooth": "",
    "autonomous_mode": False,
    "turn_angle": 0.0,
    "voltage": "0.0V",
    "battery": "0%"
}

move_start_time = 0
move_duration = 1  
move_distance = 0.5  

def move(direction):
    global is_moving, move_start_time
    is_moving = True
    move_start_time = time.time()
    car_state["direction"] = direction
    
    if direction == "Forward":
        PWM.setMotorModel(1000, 1000, 1000, 1000)
        car_state["speed"] = 1.0
    elif direction == "Backward":
        PWM.setMotorModel(-1000, -1000, -1000, -1000)
        car_state["speed"] = -1.0
    elif direction == "Left":
        PWM.setMotorModel(-1500, -1500, 2000, 2000)
        car_state["speed"] = 0.5
    elif direction == "Right":
        PWM.setMotorModel(2000, 2000, -1500, -1500)
        car_state["speed"] = 0.5

def stop():
    global is_moving
    is_moving = False
    PWM.setMotorModel(0, 0, 0, 0)
    car_state["direction"] = "Stopped"
    car_state["speed"] = 0.0

def check_obstacle():
    return ultrasonic.get_distance() < obstacle_distance

def autonomous_drive():
    if check_obstacle():
        buzzer.run('1')
        time.sleep(0.5)
        buzzer.run('0')
        move("Backward")
        time.sleep(1)
        move("Right")
        time.sleep(0.5)
    else:
        move("Forward")

def update_battery_life():
    try:
        raw_adc = adc.recvADC(2)
        voltage = raw_adc * 3
        filtered_voltage, percentage = battery_monitor.update(voltage, is_moving)
        car_state["voltage"] = f"{filtered_voltage:.2f}V"
        car_state["battery"] = f"{percentage:.1f}%"
        print(f"Raw Voltage: {voltage:.2f}V")
        print(f"Filtered Voltage: {filtered_voltage:.2f}V")
        print(f"Battery Percentage: {percentage:.1f}%")
        print(f"Is Moving: {is_moving}")
    except Exception as e:
        print(f"Error reading battery: {e}")

def control_car(command):
    global autonomous_mode, move_duration, move_distance
    try:
        if command == "87":  
            move("Forward")
        elif command == "83":  
            move("Backward")
        elif command == "65":  
            move("Left")
        elif command == "68":  
            move("Right")
        elif command == "32":  
            autonomous_mode = not autonomous_mode
            car_state["autonomous_mode"] = autonomous_mode
        elif command.startswith("MOVE:"):  
            parts = command.split(':')
            if len(parts) == 4:
                _, direction, duration, distance = parts
                move_duration = float(duration)
                move_distance = float(distance)
                move(direction)
            else:
                raise ValueError("Invalid MOVE command format")
        else:
            stop()
        
        car_state["ultrasonic"] = ultrasonic.get_distance()
        new_bluetooth_message = f"Command received: {command}"
        if car_state["bluetooth"] != new_bluetooth_message:
            car_state["bluetooth"] = new_bluetooth_message
            if "MESSAGE:" in command:
                message_part = command.split("MESSAGE:", 1)[1].strip()
                morse_beep(message_part)  
    except Exception as e:
        print(f"Error in control_car: {e}")
        stop()

async def handle_client(websocket, path):
    global autonomous_mode
    try:
        update_battery_life()  
        await websocket.send(json.dumps(car_state))  
        async for message in websocket:
            print(f"Received command: {message}")
            if message == "UPDATE":
                update_battery_life()
            else:
                control_car(message)
            
            update_battery_life()  
            print(f"Sending car state: {car_state}")
            await websocket.send(json.dumps(car_state))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in handle_client: {e}")

async def movement_control():
    global is_moving, move_start_time
    while True:
        try:
            if is_moving:
                elapsed_time = time.time() - move_start_time
                if elapsed_time >= move_duration:
                    stop()
                    if car_state["direction"] in ["Forward", "Backward"]:
                        car_state["distance"] += abs(car_state["speed"]) * move_duration
                    else:  
                        turn_rate = 45  
                        turn_angle = turn_rate * move_duration
                        car_state["turn_angle"] += turn_angle if car_state["direction"] == "Right" else -turn_angle
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Error in movement_control: {e}")

async def main_loop():
    global autonomous_mode
    while True:
        try:
            if autonomous_mode:
                autonomous_drive()
            update_battery_life()  
            await asyncio.sleep(1)  
        except Exception as e:
            print(f"Error in main_loop: {e}")

async def start_server():
    server = await websockets.serve(handle_client, "0.0.0.0", 65432)
    print("Server listening on 0.0.0.0:65432")
    await server.wait_closed()

if __name__ == "__main__":
    print("RPi Car Control")
    print("Use WSAD to steer, SPACE to toggle autonomous mode, Q to quit")
    
    loop = asyncio.get_event_loop()
    loop.create_task(main_loop())
    loop.create_task(movement_control())
    loop.run_until_complete(start_server())