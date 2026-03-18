/**
 * whatsapp_bridge/index.js
 *
 * Minimal WhatsApp sender using whatsapp-web.js.
 * Reads a JSON payload from stdin:
 *   { "chatName": "AI Papers Daily", "message": "..." }
 * Sends the message to the named chat, then exits.
 *
 * First-run: displays a QR code in the terminal for authentication.
 * Subsequent runs: uses saved session from .wwebjs_auth/ (no QR needed).
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

// ── Config ──────────────────────────────────────────────────────────────────
const AUTH_DIR = path.join(__dirname, ".wwebjs_auth");

// 이전 실행에서 남은 좀비 Chromium 정리
try {
  execSync("pkill -f '.wwebjs_auth' 2>/dev/null || true", { stdio: "ignore" });
} catch (_) {}

// SingletonLock 파일 제거 (Chromium이 남긴 잠금 파일)
const lockFile = path.join(AUTH_DIR, "session", "SingletonLock");
if (fs.existsSync(lockFile)) {
  try { fs.unlinkSync(lockFile); } catch (_) {}
}
const SESSION_TIMEOUT_MS = 90_000; // 90 seconds max wait for QR auth

// ── Read stdin payload ───────────────────────────────────────────────────────
let rawInput = "";

process.stdin.setEncoding("utf-8");
process.stdin.on("data", (chunk) => (rawInput += chunk));
process.stdin.on("end", () => {
  let payload;
  try {
    payload = JSON.parse(rawInput);
  } catch (e) {
    console.error("Failed to parse input JSON:", e.message);
    process.exit(1);
  }

  const { chatName, message } = payload;
  if (!chatName || !message) {
    console.error("Input must have 'chatName' and 'message' fields.");
    process.exit(1);
  }

  sendMessage(chatName, message);
});

// ── 시스템 Chrome 경로 자동 탐지 ─────────────────────────────────────────────
function findChrome() {
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  // macOS
    "/Applications/Chromium.app/Contents/MacOS/Chromium",            // macOS Chromium
    "/usr/bin/google-chrome",                                         // Linux
    "/usr/bin/chromium-browser",                                      // Linux
    "/usr/bin/chromium",                                              // Linux
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// ── WhatsApp client ──────────────────────────────────────────────────────────
function sendMessage(chatName, message) {
  const chromePath = findChrome();
  if (!chromePath) {
    console.error("Chrome을 찾을 수 없습니다. Google Chrome을 설치해주세요.");
    process.exit(1);
  }
  console.log(`Chrome: ${chromePath}`);

  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: AUTH_DIR }),
    puppeteer: {
      headless: true,
      executablePath: chromePath,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
      ],
    },
  });

  let authenticated = false;
  let timer = null;

  // QR code display (only needed on first run)
  client.on("qr", (qr) => {
    console.log("\n📱 Scan this QR code with WhatsApp to authenticate:\n");
    qrcode.generate(qr, { small: true });
    console.log(
      "\nOpen WhatsApp on your phone → Settings → Linked Devices → Link a Device\n"
    );

    // Timeout if QR not scanned in time
    timer = setTimeout(() => {
      if (!authenticated) {
        console.error(`QR code not scanned within ${SESSION_TIMEOUT_MS / 1000}s. Exiting.`);
        client.destroy().finally(() => process.exit(1));
      }
    }, SESSION_TIMEOUT_MS);
  });

  client.on("authenticated", () => {
    authenticated = true;
    if (timer) clearTimeout(timer);
    console.log("✅ WhatsApp authenticated.");
  });

  client.on("auth_failure", (msg) => {
    console.error("Authentication failed:", msg);
    process.exit(1);
  });

  client.on("ready", async () => {
    console.log("✅ WhatsApp client ready.");
    try {
      await doSend(client, chatName, message);
    } catch (err) {
      console.error("Failed to send message:", err.message);
      process.exit(1);
    }
    // destroy()가 hang하는 경우를 대비해 강제 종료
    client.destroy().catch(() => {}).finally(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000);
  });

  client.on("disconnected", (reason) => {
    console.error("Client disconnected:", reason);
  });

  client.initialize();
}

async function doSend(client, chatName, message) {
  const chats = await client.getChats();

  // Find chat by exact name (case-insensitive)
  let chat = chats.find(
    (c) => c.name?.toLowerCase() === chatName.toLowerCase()
  );

  // Fallback: partial match
  if (!chat) {
    chat = chats.find((c) =>
      c.name?.toLowerCase().includes(chatName.toLowerCase())
    );
  }

  if (!chat) {
    const names = chats.slice(0, 10).map((c) => c.name).join(", ");
    throw new Error(
      `Chat "${chatName}" not found. Available chats (first 10): ${names}`
    );
  }

  console.log(`Sending to chat: "${chat.name}" (${chat.id._serialized})`);
  await chat.sendMessage(message);

  // 전송 완료될 때까지 잠깐 대기 (즉시 destroy하면 메시지가 누락될 수 있음)
  await new Promise((resolve) => setTimeout(resolve, 3000));
  console.log("✅ Message sent.");
}
