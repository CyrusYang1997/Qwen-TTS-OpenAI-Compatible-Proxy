#!/bin/bash

echo "===================================="
echo "  Qwen-TTS OpenAI Compatible Proxy"
echo "===================================="
echo

# === Check Python ===
if ! command -v python3 &> /dev/null; then
    echo "[WARN] Python3 not found. Attempting to install..."
    echo

    if command -v apt-get &> /dev/null; then
        echo "[INFO] Installing Python 3.10 via apt..."
        sudo apt-get update && sudo apt-get install -y python3.10 python3.10-venv python3-pip
    elif command -v yum &> /dev/null; then
        echo "[INFO] Installing Python 3.10 via yum..."
        sudo yum install -y python3.10 python3-pip
    elif command -v dnf &> /dev/null; then
        echo "[INFO] Installing Python 3.10 via dnf..."
        sudo dnf install -y python3.10 python3-pip
    elif command -v pacman &> /dev/null; then
        echo "[INFO] Installing Python via pacman..."
        sudo pacman -Sy --noconfirm python python-pip
    elif command -v brew &> /dev/null; then
        echo "[INFO] Installing Python 3.10 via brew..."
        brew install python@3.10
    else
        echo "[ERROR] No supported package manager found."
        echo "        Please install Python 3.10+ manually: https://www.python.org/downloads/"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] Python still not available after install attempt."
        echo "        Please install Python 3.10+ manually."
        exit 1
    fi
    echo "[INFO] Python installed successfully."
    echo
fi

echo "[INFO] $(python3 --version)"

# === Check .env ===
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[WARN] .env not found. Copying from .env.example..."
        cp .env.example .env
        echo "[INFO] Please edit .env and set your DASHSCOPE_API_KEY."
        echo
    fi
fi

# === Port Selection (5s timeout) ===
PORT=8000
echo "[INFO] Default port: 8000"
echo -n "[INFO] Enter custom port within 5 seconds, or press Enter to use default: "

if read -t 5 USER_PORT; then
    if [[ "$USER_PORT" =~ ^[0-9]+$ ]] && [ "$USER_PORT" -gt 0 ] && [ "$USER_PORT" -lt 65536 ]; then
        PORT=$USER_PORT
    fi
fi

echo
echo "[INFO] Using port: $PORT"
echo

export SERVER_PORT=$PORT

# === Install Dependencies ===
echo "[INFO] Checking dependencies..."
pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q 2>/dev/null
echo "[INFO] Dependencies OK."
echo

# === Start Server ===
echo "[INFO] Starting server..."
echo "[INFO] API endpoint: http://localhost:$PORT/v1/audio/speech"
echo "[INFO] Docs:         http://localhost:$PORT/docs"
echo "[INFO] Press Ctrl+C to stop."
echo

python3 main.py
