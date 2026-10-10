#!/usr/bin/env bash
# Start Tramice721. Assumes Ollama is running and models are pulled.
set -euo pipefail

cd "$(dirname "$0")"

_venv_broken() {
  [ ! -x venv/bin/python ] && return 0
  venv/bin/python -c "import discord" >/dev/null 2>&1 && return 1
  return 0
}

_create_venv() {
  echo "Creating virtual environment..."
  if python3 -c "import ensurepip" >/dev/null 2>&1; then
    python3 -m venv venv
  else
    # Ubuntu 26.04+ often ships python3 without python3-venv / ensurepip.
    python3 -m venv --without-pip venv
    python3 -m pip --python venv/bin/python install --upgrade pip
  fi
}

if [ ! -d venv ]; then
  _create_venv
elif _venv_broken; then
  echo "Virtual environment is broken (common after an OS/Python upgrade). Recreating..."
  rm -rf venv
  _create_venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.example to .env and set DISCORD_TOKEN." >&2
  exit 1
fi

exec python -m bot.main
