#!/bin/bash
# start.sh — Quick start script for AI Memory System
# Usage:
#   ./start.sh              # production mode (Docker)
#   ./start.sh dev          # development mode (local)
#   ./start.sh build        # build Docker image only
#   ./start.sh stop         # stop containers

set -e

MODE=${1:-"docker"}

case "$MODE" in
  docker | prod)
    echo "[AI Memory] Starting in production mode (Docker)..."
    docker compose up -d --build
    echo ""
    echo "  API:    http://localhost:8765"
    echo "  UI:     http://localhost:8765/ui"
    echo "  Docs:   http://localhost:8765/docs"
    echo ""
    echo "  Logs:   docker compose logs -f"
    echo "  Stop:   docker compose down"
    ;;

  dev)
    echo "[AI Memory] Starting in development mode..."
    echo "  Starting FastAPI engine..."
    cd engine && python main.py &
    ENGINE_PID=$!
    cd ..

    echo "  Starting Vite UI dev server..."
    cd ui && npm run dev &
    UI_PID=$!
    cd ..

    echo ""
    echo "  API:    http://localhost:8765"
    echo "  UI:     http://localhost:5173"
    echo "  Docs:   http://localhost:8765/docs"
    echo ""
    echo "  Press Ctrl+C to stop all services"

    trap "kill $ENGINE_PID $UI_PID 2>/dev/null; exit 0" INT TERM
    wait
    ;;

  build)
    echo "[AI Memory] Building Docker image..."
    docker compose build
    echo "Build complete."
    ;;

  stop)
    echo "[AI Memory] Stopping containers..."
    docker compose down
    echo "Stopped."
    ;;

  *)
    echo "Usage: $0 [docker|dev|build|stop]"
    exit 1
    ;;
esac
