@echo off
REM start.bat — Quick start for AI Memory System (Windows)
REM Usage:
REM   start.bat              ^> production mode (Docker)
REM   start.bat dev          ^> development mode (local)
REM   start.bat stop         ^> stop containers

SET MODE=%1
IF "%MODE%"=="" SET MODE=docker

IF "%MODE%"=="docker" GOTO DOCKER
IF "%MODE%"=="prod" GOTO DOCKER
IF "%MODE%"=="dev" GOTO DEV
IF "%MODE%"=="stop" GOTO STOP

echo Usage: start.bat [docker^|dev^|stop]
EXIT /B 1

:DOCKER
echo [AI Memory] Starting in production mode (Docker)...
docker compose up -d --build
echo.
echo   API:    http://localhost:8765
echo   UI:     http://localhost:8765/ui
echo   Docs:   http://localhost:8765/docs
echo.
echo   Logs:   docker compose logs -f
echo   Stop:   start.bat stop
GOTO END

:DEV
echo [AI Memory] Starting in development mode...
echo   Starting FastAPI engine (background)...
start "AI Memory Engine" cmd /c "cd engine && python main.py"
echo   Starting Vite UI dev server (background)...
start "AI Memory UI" cmd /c "cd ui && npm run dev"
echo.
echo   API:    http://localhost:8765
echo   UI:     http://localhost:5173
echo   Docs:   http://localhost:8765/docs
echo.
echo   Close the opened terminal windows to stop services.
GOTO END

:STOP
echo [AI Memory] Stopping containers...
docker compose down
echo Stopped.
GOTO END

:END
