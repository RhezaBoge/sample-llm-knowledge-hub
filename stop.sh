#!/usr/bin/env bash
# Stop Project Knowledge Hub (Mac and Linux). Your saved projects are kept.
# Usage: open a Terminal in this folder and type:   bash stop.sh

cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running, so the app is already stopped."
  exit 0
fi

docker compose --profile setup down

echo
echo "Stopped. Your projects are saved in the 'data' folder."
echo "You can now also quit Docker Desktop to free your computer's memory."
echo
