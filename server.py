import asyncio
import websockets
import serial
import json
import time
import threading
import queue

# ---- CONFIG ----
COM_PORT = "COM6"
BAUD_RATE = 9600
WS_PORT = 8765
# ----------------

# Shared queue between serial thread and websocket
data_queue = queue.Queue()

def classify_waste(ir, metal, moisture):
    if ir == 1:
        return {"type": "NONE", "label": "No Waste Detected", "color": "#64748b", "confidence": 0, "points": 0, "section": -1}
    if metal == 0:
        return {"type": "METAL", "label": "Metal / E-Waste", "color": "#ef4444", "confidence": 95, "points": 10, "section": 3}
    if moisture < 400:
        return {"type": "WET", "label": "Wet / Biodegradable Waste", "color": "#22c55e", "confidence": 90, "points": 10, "section": 0}
    if moisture < 650:
        return {"type": "UNKNOWN", "label": "Ambiguous - Check Required", "color": "#94a3b8", "confidence": 45, "points": 5, "section": 4}
    return {"type": "DRY", "label": "Dry Recyclable (Plastic / Paper)", "color": "#3b82f6", "confidence": 85, "points": 10, "section": 1}


def serial_reader():
    """Runs in a separate thread - reads Arduino serial data into queue"""
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        print(f"Arduino connected on {COM_PORT}")
        time.sleep(2)

        while True:
            try:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                parts = {}
                for part in line.split(','):
                    if ':' in part:
                        key, val = part.split(':')
                        parts[key.strip()] = int(val.strip())
                if parts:
                    data_queue.put(("live", parts))
            except (ValueError, KeyError, UnicodeDecodeError):
                continue
            except Exception as e:
                print(f"Serial error: {e}")
                break

    except serial.SerialException as e:
        print(f"Could not open {COM_PORT}: {e}")
        print("Running in DEMO MODE")
        data_queue.put(("demo", {}))


def demo_generator():
    """Puts simulated data into queue when Arduino not available"""
    import random
    scenarios = [
        {"IR": 0, "METAL": 0, "MOISTURE": 900},
        {"IR": 0, "METAL": 1, "MOISTURE": 200},
        {"IR": 0, "METAL": 1, "MOISTURE": 800},
        {"IR": 0, "METAL": 1, "MOISTURE": 500},
        {"IR": 1, "METAL": 1, "MOISTURE": 1023},
    ]
    while True:
        data_queue.put(("demo", random.choice(scenarios)))
        time.sleep(2)


async def handler(websocket):
    print(f"Client connected: {websocket.remote_address}")
    try:
        while True:
            try:
                mode, parts = data_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

            if mode == "demo" and not parts:
                # Start demo generator thread
                t = threading.Thread(target=demo_generator, daemon=True)
                t.start()
                await asyncio.sleep(0.1)
                continue

            ir = parts.get('IR', 1)
            metal = parts.get('METAL', 1)
            moisture = parts.get('MOISTURE', 1023)

            result = classify_waste(ir, metal, moisture)
            payload = {
                "sensors": {"ir": ir, "metal": metal, "moisture": moisture},
                "classification": result,
                "timestamp": time.time(),
                "demo": mode == "demo"
            }
            await websocket.send(json.dumps(payload))

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")


async def main():
    print(f"SmartSeg WebSocket server starting on ws://localhost:{WS_PORT}")
    print(f"Attempting Arduino connection on {COM_PORT}...")

    # Start serial reader in background thread
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    async with websockets.serve(handler, "localhost", WS_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())