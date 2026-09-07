import time
import random
import requests

API_URL = "http://127.0.0.1:8000/api"
BATCH_ID = "HONEY-2026-BATCH-001"

def register_batch():
    payload = {
        "batch_id": BATCH_ID,
        "beekeeper_id": "BEE-KEEPER-77",
        "location": "30.3165, 78.0322",  # GPS coordinates
        "floral_source": "Wildflower"
    }
    response = requests.post(f"{API_URL}/batches", json=payload)
    if response.status_code in (200, 400):
        print(f"[Init] Batch status: {response.json()}")

def simulate_telemetry():
    base_weight = 45.0  # kg

    print(f"\n[Simulator] Starting telemetry stream for {BATCH_ID}...")
    register_batch()

    while True:
        # Simulate minor ambient fluctuations and harvest weight changes
        weight = round(base_weight + random.uniform(-0.1, 0.1), 2)
        temp = round(28.0 + random.uniform(-1.5, 1.5), 1)
        humidity = round(55.0 + random.uniform(-3.0, 3.0), 1)

        payload = {
            "batch_id": BATCH_ID,
            "weight_kg": weight,
            "temperature_c": temp,
            "humidity_pct": humidity
        }

        try:
            res = requests.post(f"{API_URL}/telemetry", json=payload)
            print(f"[Sent] Temp: {temp}°C | Humidity: {humidity}% | Weight: {weight}kg -> Response: {res.status_code}")
        except Exception as e:
            print(f"[Error] Failed to connect to backend: {e}")

        time.sleep(3)  # Transmit payload every 3 seconds

if __name__ == "__main__":
    simulate_telemetry()
