#!/bin/bash
# =============================================================================
# Office DMS - Startup Script (Linux/macOS)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  Office DMS - AI Document Management System"
echo "  Version 1.0.0"
echo "============================================================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[WARN] .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "[WARN] Please review and update .env with your settings."
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "[SETUP] Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check Tesseract
echo "[CHECK] Verifying Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    TESS_VERSION=$(tesseract --version 2>/dev/null | head -1 || echo "unknown")
    echo "[CHECK] Tesseract: $TESS_VERSION"
    echo "[CHECK] Languages: $(tesseract --list-langs 2>/dev/null | grep mya > /dev/null && echo 'Myanmar (mya) available' || echo 'WARNING: Myanmar language pack not installed. Run: sudo apt install tesseract-ocr-mya')"
else
    echo "[WARN] Tesseract not found. OCR will not work."
    echo "[WARN] Install: sudo apt-get install tesseract-ocr tesseract-ocr-mya"
fi

# Initialize database and seed data
echo "[INIT] Initializing database..."
python run.py --init

# Start file watcher in background
echo "[WATCHER] Starting file watcher..."
python run.py --watcher &
WATCHER_PID=$!
echo "[WATCHER] PID: $WATCHER_PID"

# Trap to cleanup on exit
cleanup() {
    echo "[SHUTDOWN] Stopping services..."
    kill $WATCHER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Start the web server
echo "[SERVER] Starting FastAPI server..."
echo "[SERVER] Access the application at: http://localhost:8000"
echo "[SERVER] Default login: admin / admin123"
echo "============================================================"

python run.py --host 0.0.0.0 --port 8000 "$@"
