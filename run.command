#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/"
  read -p "Press Return to close..."
  exit 1
fi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements.txt
python app.py &
APP_PID=$!
sleep 2
open http://127.0.0.1:5057
wait $APP_PID
