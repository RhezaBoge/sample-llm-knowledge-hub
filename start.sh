#!/usr/bin/env bash
# Start Project Knowledge Hub (Mac and Linux).
# Usage: open a Terminal in this folder and type:   bash start.sh

set -u
cd "$(dirname "$0")"

say()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31m%s\033[0m\n\n' "$1"; exit 1; }

say "Project Knowledge Hub - starting"

# 1. Is Docker installed and running?
if ! command -v docker >/dev/null 2>&1; then
  fail "Docker is not installed. Please install Docker Desktop first (see README.md, step 1)."
fi
if ! docker info >/dev/null 2>&1; then
  fail "Docker is installed but not running. Open Docker Desktop, wait until it says 'running', then try again."
fi

# 2. Settings file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created your settings file (.env) from .env.example."
fi
MODEL=$(grep -E '^LLM_MODEL=' .env | tail -1 | cut -d= -f2- | tr -d '[:space:]')
MODEL=${MODEL:-qwen2.5:3b}
BASE_URL=$(grep -E '^LLM_BASE_URL=' .env | tail -1 | cut -d= -f2- | tr -d '[:space:]')

# 3. Build and start (the first time this downloads a few GB - please be patient)
say "Step 1 of 3 - preparing the app (first time: 5-15 minutes)"
docker compose up -d --build backend frontend || fail "Could not start the app. See the messages above."

# 4. The AI model - only when we use the built-in Ollama
case "$BASE_URL" in
  *ollama:11434*|"")
    say "Step 2 of 3 - checking the AI model ($MODEL)"
    docker compose up -d ollama || fail "Could not start the AI model service."
    if docker compose exec -T ollama ollama show "$MODEL" >/dev/null 2>&1; then
      echo "The AI model is already downloaded."
    else
      echo "Downloading the AI model once (about 1-5 GB, depends on the model). Please wait..."
      docker compose run --rm ollama-pull || echo "Model download failed. Check your internet connection and run this script again. 'Simple rules' still works without the AI."
    fi
    ;;
  *)
    say "Step 2 of 3 - using the AI service set in .env ($BASE_URL)"
    ;;
esac

# 5. Wait until the web app answers, then open it
say "Step 3 of 3 - opening the app"
for _ in $(seq 1 60); do
  if curl -fs http://localhost:5173/api/health >/dev/null 2>&1; then break; fi
  sleep 2
done

URL="http://localhost:5173"
if command -v open >/dev/null 2>&1; then open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
fi

say "Ready!  Open $URL in your browser."
echo "When you are finished, run:   bash stop.sh"
echo
