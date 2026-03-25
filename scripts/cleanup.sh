#!/usr/bin/env bash
set -euo pipefail

echo "Stopping stack and removing containers..."
docker compose down
echo "Done."
