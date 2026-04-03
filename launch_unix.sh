#!/bin/bash

# OmniGemini Unix/macOS Launcher

echo "=========================================="
echo "    Starting OmniGemini"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Please run install_unix.sh first."
    exit 1
fi

source venv/bin/activate
python3 -m src.main
