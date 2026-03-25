import json
import logging
import os
import random
from datetime import datetime, timezone

from flask import Flask, jsonify

app = Flask(__name__)

# --------------------------------------------------
# Environment / config
# --------------------------------------------------
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "app04")
APP_LOG_FILE = os.getenv("APP_LOG_FILE", "/var/log/demo/app04.jsonl")
PORT = int(os.getenv("PORT", "8003"))

# 0.0 to 1.0, default 0.25 means ~25% failure rate
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.25"))

# --------------------------------------------------
# Logging setup
# --------------------------------------------------
os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)

class JsonFileFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)

        return json.dumps(payload)

logger = logging.getLogger("app04")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(APP_LOG_FILE, mode="a")
    file_handler.setFormatter(JsonFileFormatter())
    logger.addHandler(file_handler)

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/")
def home():
    logger.info(
        "Home endpoint called",
        extra={"extra_fields": {"endpoint": "/", "service": SERVICE_NAME}},
    )
    return jsonify(
        {
            "message": "app04 is running",
            "service": SERVICE_NAME,
            "role": "dependency-check-service",
        }
    )

@app.route("/health")
def health():
    logger.info(
        "Health endpoint called",
        extra={"extra_fields": {"endpoint": "/health", "service": SERVICE_NAME}},
    )
    return jsonify(
        {
            "status": "ok",
            "service": SERVICE_NAME,
        }
    )

@app.route("/check")
def check():
    should_fail = random.random() < FAILURE_RATE

    if should_fail:
        logger.error(
            "Dependency check failed",
            extra={
                "extra_fields": {
                    "endpoint": "/check",
                    "service": SERVICE_NAME,
                    "failure_rate": FAILURE_RATE,
                    "result": "failed",
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "service": SERVICE_NAME,
                "message": "Dependency check failed",
            }
        ), 500

    logger.info(
        "Dependency check passed",
        extra={
            "extra_fields": {
                "endpoint": "/check",
                "service": SERVICE_NAME,
                "failure_rate": FAILURE_RATE,
                "result": "passed",
            }
        },
    )
    return jsonify(
        {
            "status": "success",
            "service": SERVICE_NAME,
            "message": "Dependency check passed",
        }
    )

if __name__ == "__main__":
    logger.info(
        "app04 starting",
        extra={"extra_fields": {"event": "startup", "service": SERVICE_NAME}},
    )
    app.run(host="0.0.0.0", port=PORT)