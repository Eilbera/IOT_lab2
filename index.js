// WebSocket connection
let socket;
const server_port = 65432;
const rpi_addr = "10.0.0.28";  // Raspberry Pi's IP address
const bluetooth_forwarder_addr = "127.0.0.1";  // Bluetooth forwarder

function connectWebSocket() {
    const connectionType = document.getElementById("connection-type").value;
    const server_addr = connectionType === "Wifi" ? rpi_addr : bluetooth_forwarder_addr;

    socket = new WebSocket(`ws://${server_addr}:${server_port}`);

    socket.onopen = function(e) {
        console.log(`[open] Connection established to ${connectionType} server`);
        document.getElementById("connection-status").textContent = `Connected (${connectionType})`;
        // Request initial state
        send_data("UPDATE");
    };

    socket.onmessage = function(event) {
        console.log(`Raw data received: ${event.data}`);
        try {
            const carState = JSON.parse(event.data);
            console.log(`Parsed car state:`, carState);
            updateUI(carState);
        } catch (error) {
            console.error('Error parsing server response:', error);
        }
    };

    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        } else {
            console.log('[close] Connection died');
        }
        document.getElementById("connection-status").textContent = "Disconnected";
        // Attempt to reconnect after a short delay
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = function(error) {
        console.log(`[error] ${error.message}`);
        document.getElementById("connection-status").textContent = "Error";
    };
}

function updateUI(carState) {
    console.log("Updating UI with car state:", carState);
    
    document.getElementById("direction").textContent = carState.direction || "Unknown";
    document.getElementById("speed").textContent = carState.speed ? carState.speed.toFixed(1) : "0.0";
    document.getElementById("bluetooth").textContent = carState.bluetooth || "No data";
    document.getElementById("autonomous-mode").textContent = carState.autonomous_mode ? "ON" : "OFF";
    
    if (carState.battery) {
        console.log("Updating battery:", carState.battery);
        document.getElementById("battery").textContent = carState.battery;
    } else {
        console.log("Battery data not received");
        document.getElementById("battery").textContent = "N/A";
    }
    
    if (carState.voltage) {
        console.log("Updating voltage:", carState.voltage);
        document.getElementById("voltage").textContent = carState.voltage;
    } else {
        console.log("Voltage data not received");
        document.getElementById("voltage").textContent = "N/A";
    }
}

function updateKey(e) {
    e = e || window.event;

    if (e.keyCode == '87') {
        // up (w)
        document.getElementById("upArrow").style.color = "green";
        send_data("87");
    }
    else if (e.keyCode == '83') {
        // down (s)
        document.getElementById("downArrow").style.color = "green";
        send_data("83");
    }
    else if (e.keyCode == '65') {
        // left (a)
        document.getElementById("leftArrow").style.color = "green";
        send_data("65");
    }
    else if (e.keyCode == '68') {
        // right (d)
        document.getElementById("rightArrow").style.color = "green";
        send_data("68");
    }
    else if (e.keyCode == '32') {
        // space
        send_data("32");
    }
}

function resetKey(e) {
    e = e || window.event;

    document.getElementById("upArrow").style.color = "grey";
    document.getElementById("downArrow").style.color = "grey";
    document.getElementById("leftArrow").style.color = "grey";
    document.getElementById("rightArrow").style.color = "grey";
}

function send_custom_move() {
    const direction = document.getElementById("move-direction").value;
    const duration = document.getElementById("move-duration").value;
    const distance = document.getElementById("move-distance").value;
    send_data(`MOVE:${direction}:${duration}:${distance}`);
}

function send_data(input) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("Sending data:", input);
        socket.send(input);
    } else {
        console.error('WebSocket is not connected');
    }
}

// Function to periodically update the car information
function updateCarInfo() {
    send_data("UPDATE");
}

// Set up event listeners and periodic updates
window.onload = function() {
    console.log("connecting...");
    connectWebSocket();
    document.onkeydown = updateKey;
    document.onkeyup = resetKey;
    document.getElementById("custom-move-btn").addEventListener("click", send_custom_move);
    document.getElementById("connection-type").addEventListener("change", connectWebSocket);
    
    // Set up periodic updates
    setInterval(updateCarInfo, 5000); // Update every 5 seconds
};