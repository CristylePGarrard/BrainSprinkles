#!/bin/bash

# BrainSprinkles Desktop Launcher

cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 >/dev/null 2>&1; then
    osascript -e 'display dialog "Python 3 is required to run BrainSprinkles." buttons {"OK"}'
    exit 1
fi

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate environment
source .venv/bin/activate

# Install dependencies
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements.txt

# Launch desktop application
python desktop.py
