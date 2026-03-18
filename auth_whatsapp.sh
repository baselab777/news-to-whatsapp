#!/usr/bin/env bash
# auth_whatsapp.sh — First-time WhatsApp QR authentication
# Usage: bash auth_whatsapp.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/whatsapp_bridge"

echo ""
echo "=== WhatsApp QR Authentication ==="
echo "A QR code will appear below."
echo "Open WhatsApp → Settings → Linked Devices → Link a Device → Scan."
echo ""

node -e "
const { Client, LocalAuth } = require('whatsapp-web.js');
const qr = require('qrcode-terminal');
const client = new Client({ authStrategy: new LocalAuth() });
client.on('qr', q => qr.generate(q, { small: true }));
client.on('ready', () => {
  console.log('');
  console.log('✅ Authenticated! Session saved — no QR needed next time.');
  client.destroy();
});
client.on('auth_failure', msg => { console.error('Auth failed:', msg); process.exit(1); });
client.initialize();
"
