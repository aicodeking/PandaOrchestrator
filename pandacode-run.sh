#!/bin/sh
# Panda Router v2: local routing API (POST /route, /escalate, /outcome; GET /health) on port 8765.
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python -m panda_router.serve --port 8765 --artifacts artifacts/panda-router-v3
