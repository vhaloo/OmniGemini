#!/bin/bash

# OmniGemini Unix/macOS Installer

echo "=========================================="
echo "    OmniGemini Unix Auto-Installer"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] python3 could not be found."
    echo "Please install Python 3.10+ and ensure it's in your PATH."
    exit 1
fi

# 2. Check for pip / venv module
if ! python3 -c "import venv" &> /dev/null
then
    echo "[ERROR] python3-venv is missing."
    echo "On Debian/Ubuntu, run: sudo apt install python3-venv"
    exit 1
fi

echo "[1/3] Creating Python Virtual Environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
else
    echo "Virtual environment already exists. Skipping creation."
fi

echo ""
echo "[2/3] Activating Virtual Environment and Upgrading PIP..."
source venv/bin/activate
python3 -m pip install --upgrade pip > /dev/null 2>&1

echo ""
echo "[3/3] Installing Required Dependencies..."
echo "This may take a few minutes depending on your internet connection."
# Some Linux systems require python3-pyaudio and portaudio dependencies for mic
# but we use sounddevice. On Linux, libportaudio2 is required. We can try to install the pip packages.
pip install google-genai sounddevice numpy opencv-python mss Pillow PyQt6 qasync rich

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to install dependencies."
    echo "Note: If 'sounddevice' fails on Linux, you might need to install PortAudio first:"
    echo "   sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev"
    exit 1
fi

echo ""
echo "=========================================="
echo "    Installation Completed Successfully!"
echo "=========================================="
echo ""
echo "To launch OmniGemini, you can run:"
echo "./launch_unix.sh"
echo ""

read -p "Do you want to launch OmniGemini now? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]
then
    ./launch_unix.sh
fi
