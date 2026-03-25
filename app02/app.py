import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from faker import Faker
import requests

from flask import Flask, jsonify

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor



app = Flask(__name__)
fake = Faker()

#Logging setup
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))
APP01_BASE_URL = os.getenv("APP01_BASE_URL", "http://app01:8000")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "app02")
APP_LOG_FILE = os.getenv("APP_LOG_FILE", "/var/log/demo/app02.jsonl")
PORT = int(os.getenv("PORT", "8000"))

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

logger = logging.getLogger("app02")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(APP_LOG_FILE, mode="a")
file_handler.setFormatter(JsonFileFormatter())
logger.addHandler(file_handler)

#db setup

DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "demo_db")
DB_USER = os.getenv("DB_USER", "demo_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "demo_pass")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

#instrument sqlalchemy
SQLAlchemyInstrumentor().instrument(engine=engine)
SessionLocal = sessionmaker(bind=engine)

def make_dummy_customer():
    
    return {
        "name": fake.name(),
        "email": fake.email(),
        "city": fake.city().replace("\n", ", "),
    }

def insert_pass_event(endpoint: str):
    """insert the pass event of the 2 procy methods to the db table(proxy_details) 
    for demo purposes, to have some db events to show in the demo dashboards
    """
    endpoint = endpoint[:255]  # Ensure endpoint fits in the database column

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO proxy_details (event_endpoint)
                VALUES (:endpoint)
            """),
            {"endpoint": endpoint}
        )

def insert_copied_customer(source_user):
    copied_user = {
        "source_user_id": source_user["id"],
        "name": source_user["name"],
        "email": source_user["email"],
        "city": source_user["city"],
    }

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO customers_app02 (source_user_id, name, email, city)
                VALUES (:source_user_id, :name, :email, :city)
            """),
            copied_user
        )
        copied_user["id"] = result.lastrowid

    return copied_user


@app.route("/trigger-app01-error")
def trigger_app01_error():
    try:
        response = requests.get(f"{APP01_BASE_URL}/error")
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception(
            "Error occurred while triggering app01 error",
            extra={"extra_fields": {"endpoint": "/trigger-app01-error", "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": str(exc)}), 500
    
@app.route("/copy-user/<int:user_id>")
def copy_user(user_id):
    try:
        # First, retrieve the user from app01
        response = requests.get(f"{APP01_BASE_URL}/get-user/{user_id}")
        response.raise_for_status()
        user = response.json().get("user")

        if not user:
            logger.warning(
                "User not found in app01",
                extra={"extra_fields": {"operation": "select", "user_id": user_id}},
            )
            return jsonify({"status": "error", "message": "User not found in app01"}), 404

        # Then, insert the user into app02
        inserted_user = insert_copied_customer(user)
        logger.info(
            "Copied customer from app01 to app02",
            extra={"extra_fields": {"operation": "insert", "user_id": inserted_user["id"], "email": inserted_user["email"]}},
        )
        return jsonify({"status": "success", "user": inserted_user})
    except requests.RequestException as exc:
        logger.exception(
            "Error occurred while copying user",
            extra={"extra_fields": {"endpoint": "/copy-user", "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": str(exc)}), 500

@app.route("/")
def home():
    logger.info("Home endpoint called", extra={"extra_fields": {"endpoint": "/"}})
    return jsonify(
        {
            "message": "Local OpenTelemetry demo is running",
            "service": SERVICE_NAME,
        }
    )

@app.route("/health")
def health():
    logger.info("Health endpoint called", extra={"extra_fields": {"endpoint": "/health"}})
    return jsonify({"status": "ok"})

@app.route("/proxy-user/<int:user_id>")
def proxy_user(user_id):
    insert_pass_event("/proxy-user")
   
    try:
        response = requests.get(f"{APP01_BASE_URL}/get-user/{user_id}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        payload = response.json()
        user = payload.get("user")

        if not user:
            logger.warning(
                "User not returned by app01",
                extra={"extra_fields": {"endpoint": "/proxy-user", "user_id": user_id}},
            )
            return jsonify({"status": "error", "message": "User not returned by app01"}), 404

        logger.info(
            "Proxied user from app01",
            extra={
                "extra_fields": {
                    "endpoint": "/proxy-user",
                    "user_id": user_id,
                    "source_service": "app01",
                }
            },
        )
      
        return jsonify({"status": "success", "user": user})

    except requests.RequestException as exc:
        logger.exception(
            "Error occurred while proxying user from app01",
            extra={
                "extra_fields": {
                    "endpoint": "/proxy-user",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify({"status": "error", "message": str(exc)}), 500

@app.route("/proxy-user-then-fail/<int:user_id>")
def proxy_user_then_fail(user_id):
    insert_pass_event("/proxy-user-then-fail")
    try:
        response = requests.get(
            f"{APP01_BASE_URL}/get-user-then-fail/{user_id}",
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return jsonify(response.json())

    except requests.RequestException as exc:
        logger.exception(
            "Error occurred while proxying user from app01 failing endpoint",
            extra={
                "extra_fields": {
                    "endpoint": "/proxy-user-then-fail",
                    "user_id": user_id,
                    "error": str(exc),
                }
            },
        )
        return jsonify({"status": "error", "message": str(exc)}), 500
    
    
if __name__ == "__main__":
    logger.info("App02 starting", extra={"extra_fields": {"event": "startup"}})
    app.run(host="0.0.0.0", port=PORT)