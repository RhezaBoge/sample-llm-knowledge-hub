@echo off
rem Start Project Knowledge Hub (Windows). Double-click this file.
setlocal
cd /d "%~dp0"

echo.
echo Project Knowledge Hub - starting
echo.

rem 1. Is Docker installed and running?
where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed. Please install Docker Desktop first ^(see README.md, step 1^).
  goto :end
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker is installed but not running.
  echo Open Docker Desktop, wait until it says "running", then double-click start.bat again.
  goto :end
)

rem 2. Settings file
if not exist .env (
  copy .env.example .env >nul
  echo Created your settings file ^(.env^) from .env.example.
)
set "MODEL=qwen2.5:3b"
for /f "tokens=1,* delims==" %%a in ('findstr /b "LLM_MODEL=" .env') do set "MODEL=%%b"
set "BASE_URL="
for /f "tokens=1,* delims==" %%a in ('findstr /b "LLM_BASE_URL=" .env') do set "BASE_URL=%%b"

rem 3. Build and start (the first time this downloads a few GB - please be patient)
echo.
echo Step 1 of 3 - preparing the app (first time: 5-15 minutes)
docker compose up -d --build backend frontend
if errorlevel 1 (
  echo Could not start the app. See the messages above.
  goto :end
)

rem 4. The AI model - only when we use the built-in Ollama
echo.
echo %BASE_URL% | findstr /c:"ollama:11434" >nul
if errorlevel 1 if defined BASE_URL (
  echo Step 2 of 3 - using the AI service set in .env ^(%BASE_URL%^)
  goto :open
)
echo Step 2 of 3 - checking the AI model (%MODEL%)
docker compose up -d ollama
docker compose exec -T ollama ollama show %MODEL% >nul 2>&1
if errorlevel 1 (
  echo Downloading the AI model once ^(about 1-5 GB, depends on the model^). Please wait...
  docker compose run --rm ollama-pull
  if errorlevel 1 echo Model download failed. Check your internet connection and run start.bat again. "Simple rules" still works without the AI.
) else (
  echo The AI model is already downloaded.
)

:open
rem 5. Wait until the web app answers, then open it
echo.
echo Step 3 of 3 - opening the app
for /l %%i in (1,1,60) do (
  curl -fs http://localhost:5173/api/health >nul 2>&1 && goto :ready
  timeout /t 2 /nobreak >nul
)
:ready
start "" http://localhost:5173
echo.
echo Ready!  The app is open at http://localhost:5173
echo When you are finished, double-click stop.bat
echo.

:end
pause
