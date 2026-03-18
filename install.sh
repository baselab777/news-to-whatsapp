#!/usr/bin/env bash
# install.sh — One-shot setup for ai-curator
# Usage: bash install.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=== AI Curator Setup ==="
echo ""

# ── 1. Python venv ────────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "[1/4] Creating Python virtual environment..."
  python3 -m venv venv
else
  echo "[1/4] venv already exists — skipping."
fi

source venv/bin/activate

# ── 2. Python packages ────────────────────────────────────────────────────────
echo "[2/4] Installing Python packages..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "      ✅ Python packages installed."

# ── 3. Node.js / WhatsApp bridge ─────────────────────────────────────────────
echo "[3/4] Installing WhatsApp bridge (Node.js)..."
if ! command -v node &>/dev/null; then
  echo "      ⚠️  node not found. Install Node.js (https://nodejs.org) then re-run."
else
  (cd whatsapp_bridge && npm install --silent)
  echo "      ✅ WhatsApp bridge installed."
fi

# ── 4. .env file ──────────────────────────────────────────────────────────────
echo "[4/4] Setting up .env..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "      ✅ .env created — open it and fill in ANTHROPIC_API_KEY."
else
  echo "      .env already exists — skipping."
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env  → set ANTHROPIC_API_KEY and WHATSAPP_CHAT_NAME"
echo "  2. Authenticate WhatsApp (once):  bash auth_whatsapp.sh"
echo "  3. Test run:  source venv/bin/activate && python run.py --dry-run"
echo "  4. Schedule:  bash setup_cron.sh"
echo ""
