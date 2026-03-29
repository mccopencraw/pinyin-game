#!/usr/bin/env python3
"""
普通話發音遊戲 — WhatsApp Bridge 插件
用法: python3 pinyin-bot.py
需要 nanobot 已連接同一個 WhatsApp bridge
"""

import asyncio, json, os, sys, hashlib, mimetypes
import urllib.request, urllib.parse

# ── Add project dir to path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from game import PinyinGame, main_menu

# ── Config ────────────────────────────────────────────────────────────
BRIDGE_URL   = os.environ.get("WA_BRIDGE_URL",  "ws://localhost:3001")
BRIDGE_TOKEN = os.environ.get("WA_BRIDGE_TOKEN", "")
AUDIO_DIR    = os.path.join(os.path.dirname(__file__), "audio")

# ── State ─────────────────────────────────────────────────────────────
games: dict[str, PinyinGame] = {}   # chat_id → game instance

# ── Helpers ───────────────────────────────────────────────────────────

def get_game(chat_id: str) -> PinyinGame:
    if chat_id not in games:
        games[chat_id] = PinyinGame(chat_id)
    return games[chat_id]

async def send_text(ws, chat_id: str, text: str) -> None:
    payload = {"type": "send", "to": chat_id, "text": text}
    await ws.send(json.dumps(payload, ensure_ascii=False))

async def send_audio(ws, chat_id: str, audio_path: str) -> None:
    if not audio_path or not os.path.exists(audio_path):
        return
    mime, _ = mimetypes.guess_type(audio_path)
    payload = {
        "type":      "send_media",
        "to":        chat_id,
        "filePath":  audio_path,
        "mimetype":  mime or "audio/mpeg",
        "fileName":  os.path.basename(audio_path),
    }
    await ws.send(json.dumps(payload, ensure_ascii=False))

async def handle_message(ws, data: dict) -> None:
    msg_type  = data.get("type", "")
    if msg_type != "message":
        return

    content   = data.get("content", "")
    chat_id   = data.get("sender", "")      # 回復到發送者
    msg_id    = data.get("id", "")
    pn        = data.get("pn", "")
    is_group  = data.get("isGroup", False)

    if not content and not msg_id:
        return

    # 語音消息
    if content == "[Voice Message]":
        await send_text(ws, chat_id,
            "🎤 語音消息我聽唔到，請打文字！")
        return

    # 跳過媒體消息（只有文字）
    if content.startswith("[image:") or content.startswith("[file:"):
        return

    text = content.strip()
    if not text:
        return

    # 忽略普通對話（除非用遊戲指令觸發）
    trigger_keywords = ["普通話", "pinyin", "拼音", "聲母", "韻母", "聲調", "發音", "🇨🇳"]
    is_game_msg = any(kw in text for kw in trigger_keywords)

    # 萬用指令
    lower = text.lower()
    if lower in ("pinyin", "普通話") or "普通話" in text or "pinyin" in lower:
        is_game_msg = True
    if lower in ("menu", "主目錄", "目錄"):
        is_game_msg = True
    if lower in ("quit", "停止", "停"):
        is_game_msg = True

    if not is_game_msg and chat_id in games:
        g = games[chat_id]
        # 如果在遊戲中，隨時接受答案
        if g.state != "menu":
            is_game_msg = True

    if not is_game_msg:
        return  # 忽略普通消息

    # 啟動遊戲
    if text.lower() in ("普通話", "pinyin", "開始", "玩", "遊戲", "發音", "聲母", "韻母", "聲調"):
        g = get_game(chat_id)
        g.state = "menu"
        resp = g.handle("menu")
        await send_text(ws, chat_id, resp["text"])
        if resp.get("audio"):
            await send_audio(ws, chat_id, resp["audio"])
        return

    # 處理遊戲
    if chat_id in games:
        g = games[chat_id]
        resp = g.handle(text)
        await send_text(ws, chat_id, resp["text"])
        if resp.get("audio"):
            await send_audio(ws, chat_id, resp["audio"])
    else:
        await send_text(ws, chat_id, main_menu())

# ── Main loop ────────────────────────────────────────────────────────

async def main() -> None:
    print(f"🎮 普通話遊戲 Bot — 連接 {BRIDGE_URL}")
    while True:
        try:
            import websockets
            async with websockets.connect(BRIDGE_URL) as ws:
                print("✅ 已連接 WhatsApp Bridge")

                if BRIDGE_TOKEN:
                    auth = {"type": "auth", "token": BRIDGE_TOKEN}
                    await ws.send(json.dumps(auth))
                    print(f"🔑 已發送 auth token")

                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        await handle_message(ws, data)
                    except json.JSONDecodeError:
                        print(f"[WARN] Invalid JSON: {raw[:100]}")
        except Exception as e:
            print(f"[ERROR] 斷線: {e}，5秒後重連...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        import websockets
    except ImportError:
        print("需要 websockets：pip install websockets")
        sys.exit(1)
    asyncio.run(main())
