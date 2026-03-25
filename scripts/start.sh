#!/usr/bin/env bash
set -euo pipefail

echo "Starting local observability demo..."
docker compose up -d --build
echo
echo "Containers:"
docker compose ps
echo
echo "URLs:"
echo "  App:        http://localhost:8000"
echo "  Grafana:    http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo "  Jaeger UI:  http://localhost:16686"
echo
echo "Grafana credentials: admin / admin"

