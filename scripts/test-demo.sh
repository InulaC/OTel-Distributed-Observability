#!/bin/bash

APP01_URL="http://localhost:8000"
APP02_URL="http://localhost:8001"
APP03_URL="http://localhost:8002"
APP04_URL="http://localhost:8003"

echo "Starting demo traffic generator..."
echo "app01: $APP01_URL"
echo "app02: $APP02_URL"
echo "app03: $APP03_URL"
echo "app04: $APP04_URL"
echo "Press CTRL+C to stop."
echo ""

while true
do
    # --------------------------------------------------
    # app01 basic traffic
    # --------------------------------------------------
    curl -s "$APP01_URL/" > /dev/null
    curl -s "$APP01_URL/health" > /dev/null
    curl -s "$APP01_URL/work" > /dev/null

    # Create one random user in app01
    CREATE_RESPONSE=$(curl -s "$APP01_URL/create-user")

    # Extract inserted user id
    USER_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[[:space:]]*[0-9]*' | head -1 | grep -o '[0-9]*')

    # app01 direct get-user
    if [ -n "$USER_ID" ]; then
        curl -s "$APP01_URL/get-user/$USER_ID" > /dev/null
    fi

    # --------------------------------------------------
    # app02 traffic
    # --------------------------------------------------
    # app02 direct home/health if available
    curl -s "$APP02_URL/" > /dev/null
    curl -s "$APP02_URL/health" > /dev/null

    # app02 proxy-user from app01
    if [ -n "$USER_ID" ]; then
        curl -s "$APP02_URL/proxy-user/$USER_ID" > /dev/null
    fi

    # app02 copy-user into app02 table
    if [ -n "$USER_ID" ]; then
        curl -s "$APP02_URL/copy-user/$USER_ID" > /dev/null
    fi

    # Occasionally trigger app02 -> app01 error chain
    if [ $((RANDOM % 4)) -eq 0 ]; then
        curl -s "$APP02_URL/trigger-app01-error" > /dev/null
    fi

    # --------------------------------------------------
    # app04 direct checks
    # --------------------------------------------------
    # occasional direct check to app04
    if [ $((RANDOM % 3)) -eq 0 ]; then
        curl -s "$APP04_URL/check" > /dev/null
    fi

    # --------------------------------------------------
    # app03 full chain
    # app03 -> app04
    # app03 -> app02 -> app01 -> MySQL
    # app03 -> MongoDB
    # --------------------------------------------------
    curl -s "$APP03_URL/" > /dev/null
    curl -s "$APP03_URL/health" > /dev/null

    if [ -n "$USER_ID" ]; then
        curl -s "$APP03_URL/fetch-and-store/$USER_ID" > /dev/null
    fi

    # Occasionally trigger full-chain failure:
    # app03 -> app02 -> app01 -> MySQL -> fail after DB
    if [ -n "$USER_ID" ] && [ $((RANDOM % 4)) -eq 0 ]; then
        curl -s "$APP03_URL/fetch-and-store-then-fail/$USER_ID" > /dev/null
    fi
    # --------------------------------------------------
    # occasional direct app01 error too
    # --------------------------------------------------
    if [ $((RANDOM % 5)) -eq 0 ]; then
        curl -s "$APP01_URL/error" > /dev/null
    fi

    sleep 1
done