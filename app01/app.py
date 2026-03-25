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

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "app01")
APP_LOG_FILE = os.getenv("APP_LOG_FILE", "/var/log/demo/app01.jsonl")
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

logger = logging.getLogger("app01")
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


def insert_dummy_customer():
    user = make_dummy_customer()
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO customers_app01 (name, email, city)
                VALUES (:name, :email, :city)
            """),
            user
        )
        user["id"] = result.lastrowid
    return user

def get_customer_by_id(user_id):
    with engine.connect() as conn:
        result = conn.execute(text("""SELECT id, name, email, city, created_at
                FROM customers_app01
                WHERE id = :id
            """), 
                {"id": user_id}
        ).mappings().first()
        
        return dict(result) if result else None
    
@app.route("/create-user")
def create_user():
    try:
        user = insert_dummy_customer()
        logger.info(
            "Created new customer",
            extra={"extra_fields": {"operation": "insert", "user_id": user["id"], "email": user["email"]}},
        )
        return jsonify({"status": "success", "user": user})
    except SQLAlchemyError as exc:
        logger.exception(
            "Database error during user creation",
            extra={"extra_fields": {"operation": "insert", "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": "Failed to create user"}), 500

@app.route("/get-user/<int:user_id>")
def get_user(user_id):
    try:
        user = get_customer_by_id(user_id)
        if not user:
            logger.warning(
                "User not found",
                extra={"extra_fields": {"operation": "select", "user_id": user_id}},
            )
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        logger.info(
            "Retrieved customer",
            extra={"extra_fields": {"operation": "select", "user_id": user_id}},)
        return jsonify({"status": "success", "user": user})
    except SQLAlchemyError as exc:
        logger.exception(
            "Database error during user retrieval",
            extra={"extra_fields": {"operation": "select", "user_id": user_id, "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": "Failed to retrieve user"}), 500


@app.route("/get-user-then-fail/<int:user_id>")
def get_user_then_fail(user_id):
    try:
        user = get_customer_by_id(user_id)
        if not user:
            logger.warning(
                "User not found",
                extra={"extra_fields": {"operation": "select", "user_id": user_id}},
            )
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        logger.info(
            "Retrieved customer Triggering intentional failure",
            extra={"extra_fields": {"operation": "select", "user_id": user_id}},)
        raise RuntimeError("Intentional failure after user retrieval")
    except SQLAlchemyError as exc:
        logger.exception(
            "Database error during user retrieval",
            extra={"extra_fields": {"operation": "select", "user_id": user_id, "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": "Failed to retrieve user"}), 500
    



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

@app.route("/work")
def work():
    duration = random.uniform(100, 600)
    time.sleep(duration / 1000.0)
    logger.info(
        "Work endpoint completed",
        extra={"extra_fields": {"endpoint": "/work", "duration_ms": round(duration, 2)}},
    )
    return jsonify({"status": "done", "duration_ms": round(duration, 2)})

@app.route("/error")
def error():
    try:
        raise RuntimeError("Intentional demo error")
    except Exception as exc:
        logger.exception(
            "Error endpoint triggered",
            extra={"extra_fields": {"endpoint": "/error", "error": str(exc)}},
        )
        return jsonify({"status": "error", "message": str(exc)}), 500

if __name__ == "__main__":
    logger.info("App01 starting", extra={"extra_fields": {"event": "startup"}})
    app.run(host="0.0.0.0", port=PORT)