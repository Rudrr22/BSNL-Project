import random
import time
import httpx
import asyncio
from datetime import datetime

# Realistic BSNL network components
TOWERS = ["BTS_042", "BTS_019", "BTS_091", "BTS_103", "BTS_077"]
ROUTERS = ["Core_Router_7", "Edge_Router_2", "Router_Delhi_1"]
REGIONS = ["Jaipur", "Delhi", "Mumbai", "Roorkee", "Lucknow"]
SEVERITIES = ["INFO", "WARNING", "CRITICAL"]
SEVERITY_WEIGHTS = [0.6, 0.3, 0.1]  # 60% info, 30% warning, 10% critical

# Different types of events
EVENT_TEMPLATES = {
    "CRITICAL": [
        {"type": "Signal_Drop", "metric": "RSSI", "value": lambda: random.randint(-100, -88)},
        {"type": "Handover_Failed", "metric": "Subscribers_Affected", "value": lambda: random.randint(100, 1000)},
        {"type": "Tower_Down", "metric": "Uptime", "value": lambda: 0},
    ],
    "WARNING": [
        {"type": "High_Latency", "metric": "Latency_ms", "value": lambda: random.randint(150, 400)},
        {"type": "Packet_Loss", "metric": "Loss_Percent", "value": lambda: random.randint(10, 30)},
        {"type": "High_Load", "metric": "CPU_Percent", "value": lambda: random.randint(75, 95)},
    ],
    "INFO": [
        {"type": "Handover_Success", "metric": "RSSI", "value": lambda: random.randint(-80, -50)},
        {"type": "Tower_Online", "metric": "Uptime", "value": lambda: random.randint(99, 100)},
        {"type": "Normal_Operation", "metric": "Latency_ms", "value": lambda: random.randint(10, 50)},
    ]
}

def generate_log():
    """Generate one realistic BSNL log entry"""
    severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0]
    event = random.choice(EVENT_TEMPLATES[severity])
    component = random.choice(TOWERS + ROUTERS)
    region = random.choice(REGIONS)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metric_value = event["value"]()

    return {
        "timestamp": timestamp,
        "severity": severity,
        "component": component,
        "region": region,
        "event_type": event["type"],
        "metric": event["metric"],
        "value": metric_value,
        "raw": f"[{timestamp}] {severity} {component} {event['type']} {event['metric']}={metric_value} Region={region}"
    }

async def send_logs():
    """Continuously send logs to backend"""
    print("🚀 TeleGuard Log Simulator Started")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                log = generate_log()
                await client.post(
                    "http://backend:8000/api/logs/ingest",
                    json=log
                )
                print(f"📡 Sent: {log['raw']}")
            except Exception as e:
                print(f"⚠️ Backend not ready yet: {e}")
            await asyncio.sleep(random.uniform(1.5, 3.5))

if __name__ == "__main__":
    asyncio.run(send_logs())