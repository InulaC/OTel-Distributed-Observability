import json
import logging
import os
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# --------------------------------------------------
# Environment / config
# --------------------------------------------------
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "app03")
APP_LOG_FILE = os.getenv("APP_LOG_FILE", "/var/log/demo/app03.jsonl")
PORT = int(os.getenv("PORT", "8002"))

APP02_BASE_URL = os.getenv("APP02_BASE_URL", "http://app02:8001")
APP04_BASE_URL = os.getenv("APP04_BASE_URL", "http://app04:8003")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "demo_mongo")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "received_customers")

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))

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

logger = logging.getLogger("app03")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(APP_LOG_FILE, mode="a")
    file_handler.setFormatter(JsonFileFormatter())
    logger.addHandler(file_handler)

# --------------------------------------------------
# MongoDB setup
# --------------------------------------------------
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
mongo_collection = mongo_db[MONGO_COLLECTION_NAME]

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def store_received_user(source_user: dict) -> dict:
    doc = {
        "source_service": "app01",
        "via_service": "app02",
        "source_user_id": source_user["id"],
        "name": source_user["name"],
        "email": source_user["email"],
        "city": source_user["city"],
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    result = mongo_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

def check_app04() -> requests.Response:
    return requests.get(f"{APP04_BASE_URL}/check", timeout=REQUEST_TIMEOUT)

def get_user_via_app02(user_id: int) -> requests.Response:
    return requests.get(f"{APP02_BASE_URL}/proxy-user/{user_id}", timeout=REQUEST_TIMEOUT)

def get_user_via_app02_then_fail(user_id: int) -> requests.Response:
    return requests.get(f"{APP02_BASE_URL}/proxy-user-then-fail/{user_id}", timeout=REQUEST_TIMEOUT)

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
            "message": "app03 is running",
            "service": SERVICE_NAME,
            "role": "orchestrator",
        }
    )

@app.route("/health")
def health():
    try:
        mongo_client.admin.command("ping")
        logger.info(
            "Health check passed",
            extra={"extra_fields": {"endpoint": "/health", "mongodb": "connected"}},
        )
        return jsonify(
            {
                "status": "ok",
                "service": SERVICE_NAME,
                "mongodb": "connected",
            }
        )
    except Exception as exc:
        logger.exception(
            "Health check failed",
            extra={"extra_fields": {"endpoint": "/health", "error": str(exc)}},
        )
        return jsonify(
            {
                "status": "error",
                "service": SERVICE_NAME,
                "message": str(exc),
            }
        ), 500

@app.route("/fetch-and-store/<int:user_id>")
def fetch_and_store(user_id: int):
    try:
        # Step 1: app04 must succeed, otherwise fail the whole request
        app04_response = check_app04()
        if app04_response.status_code >= 400:
            logger.error(
                "app04 check failed, request aborted",
                extra={
                    "extra_fields": {
                        "endpoint": "/fetch-and-store",
                        "user_id": user_id,
                        "dependency": "app04",
                        "app04_status_code": app04_response.status_code,
                    }
                },
            )
            return jsonify(
                {
                    "status": "error",
                    "message": "app04 dependency check failed",
                    "app04_status_code": app04_response.status_code,
                }
            ), 500

        logger.info(
            "app04 check passed",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store",
                    "user_id": user_id,
                    "dependency": "app04",
                    "app04_status_code": app04_response.status_code,
                }
            },
        )
        

        # Step 2: ask app02 to fetch the user (which gets it from app01)
        app02_response = get_user_via_app02(user_id)
        app02_response.raise_for_status()

        payload = app02_response.json()
        user = payload.get("user")

        if not user:
            logger.warning(
                "User not returned by app02",
                extra={
                    "extra_fields": {
                        "endpoint": "/fetch-and-store",
                        "user_id": user_id,
                        "dependency": "app02",
                    }
                },
            )
            return jsonify(
                {
                    "status": "error",
                    "message": "User not returned by app02",
                }
            ), 404

        # Step 3: store in MongoDB
        stored_doc = store_received_user(user)

        logger.info(
            "User fetched through app02/app01 and stored in MongoDB",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store",
                    "user_id": user_id,
                    "source_user_id": user["id"],
                    "mongo_id": stored_doc["_id"],
                    "dependency": "app02",
                }
            },
        )

        return jsonify(
            {
                "status": "success",
                "message": "User fetched and stored",
                "user": user,
                "stored_document": stored_doc,
            }
        )

    except requests.RequestException as exc:
        logger.exception(
            "HTTP dependency call failed",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "message": str(exc),
            }
        ), 500

    except PyMongoError as exc:
        logger.exception(
            "MongoDB insert failed",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "message": "Failed to store user in MongoDB",
            }
        ), 500

    except Exception as exc:
        logger.exception(
            "Unexpected error in fetch-and-store",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "message": "Unexpected internal error",
            }
        ), 500
    
@app.route("/fetch-and-store-then-fail/<int:user_id>")
def fetch_and_store_then_fail(user_id: int):
    try:
        app04_response = check_app04()
        if app04_response.status_code >= 400:
            logger.error(
                "app04 check failed, request aborted",
                extra={
                    "extra_fields": {
                        "endpoint": "/fetch-and-store-then-fail",
                        "user_id": user_id,
                        "dependency": "app04",
                        "app04_status_code": app04_response.status_code,
                    }
                },
            )
            return jsonify(
                {
                    "status": "error",
                    "message": "app04 dependency check failed",
                    "app04_status_code": app04_response.status_code,
                }
            ), 500

        logger.info(
            "app04 check passed",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store-then-fail",
                    "user_id": user_id,
                    "dependency": "app04",
                    "app04_status_code": app04_response.status_code,
                }
            },
        )

        app02_response = get_user_via_app02_then_fail(user_id)
        app02_response.raise_for_status()

        return jsonify(
            {
                "status": "success",
                "message": "Unexpected success on failing path",
            }
        )

    except requests.RequestException as exc:
        logger.exception(
            "HTTP dependency call failed on failing path",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store-then-fail",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "message": str(exc),
            }
        ), 500

    except Exception as exc:
        logger.exception(
            "Unexpected error in fetch-and-store-then-fail",
            extra={
                "extra_fields": {
                    "endpoint": "/fetch-and-store-then-fail",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify(
            {
                "status": "error",
                "message": "Unexpected internal error",
            }
        ), 500
    
    
if __name__ == "__main__":
    logger.info(
        "app03 starting",
        extra={"extra_fields": {"event": "startup", "service": SERVICE_NAME}},
    )
    app.run(host="0.0.0.0", port=PORT)