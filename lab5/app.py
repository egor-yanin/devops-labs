from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import random
import time
import math

app = Flask(__name__)

REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total number of requests"
)

REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Request latency"
)

@app.route("/")
def home():
    start = time.time()

    REQUEST_COUNT.inc()

    # Искусственная CPU-нагрузка
    value = 0
    for i in range(500000):
        value += math.sqrt(i)

    # Искусственная задержка
    delay = random.uniform(0.1, 0.5)
    time.sleep(delay)

    REQUEST_LATENCY.observe(time.time() - start)

    return jsonify({
        "status": "ok",
        "delay": delay
    })


@app.route("/health")
def health():
    return "healthy"


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {
        "Content-Type": "text/plain"
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)