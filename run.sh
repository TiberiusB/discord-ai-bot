#!/usr/bin/env bash
# Start Tramice721. Assumes Ollama is running and models are pulled.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.example to .env and set DISCORD_TOKEN." >&2
  exit 1
fi

exec python -m bot.main
