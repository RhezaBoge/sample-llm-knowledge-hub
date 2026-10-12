@echo off
rem Stop Project Knowledge Hub (Windows). Double-click this file. Your saved projects are kept.
setlocal
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is not running, so the app is already stopped.
  goto :end
)

docker compose --profile setup down

echo.
echo Stopped. Your projects are saved in the "data" folder.
echo You can now also quit Docker Desktop to free your computer's memory.
echo.

:end
pause
