#!/usr/bin/env python3
"""
普通話聲母、韻母、聲調 發音遊戲
用 Google TTS 讀音，通過 WhatsApp 互動
"""

import os, random, subprocess, hashlib
import json
import urllib.request
import urllib.parse

AUDIO_DIR = "/home/ubuntu/.nanobot-mama/workspace/projects/pinyin-game/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# 1. 教學內容
# ─────────────────────────────────────────────

# 聲母 (全部)
INITIALS = [
    ("b", "玻"), ("p", "潑"), ("m", "摸"), ("f", "佛"),
    ("d", "得"), ("t", "特"), ("n", "呢"), ("l", "勒"),
    ("g", "哥"), ("k", "科"), ("h", "喝"),
    ("j", "基"), ("q", "欺"), ("x", "希"),
    ("zh", "知"), ("ch", "蚩"), ("sh", "詩"), ("r", "日"),
    ("z", "資"), ("c", "雌"), ("s", "思"),
    ("y", "呀"), ("w", "蛙"),
]

# 韻母 (全部) - 分組
FINALS_SIMPLE = [
    ("a", "啊"), ("o", "哦"), ("e", "鵝"), ("i", "衣"), ("u", "屋"), ("ü", "魚"),
]
FINALS_COMPOUND = [
    ("ai", "愛"), ("ei", "欸"), ("ui", "堆"),
    ("ao", "奧"), ("ou", "歐"), ("iu", "優"),
    ("ie", "椰"), ("üe", "月"), ("er", "耳"),
    ("an", "安"), ("en", "恩"), ("in", "音"), ("un", "溫"), ("ün", "雲"),
    ("ang", "昂"), ("eng", "鞥"), ("ing", "英"), ("ong", "翁"),
]
ALL_FINALS = FINALS_SIMPLE + FINALS_COMPOUND

# 四聲 (音調) - 示範音節
TONES = {
    1: ("mā", "媽", "第一聲 / 高平"),   # ā
    2: ("má", "麻", "第二聲 / 升"),
    3: ("měi", "美", "第三聲 / 降升"),
    4: ("mà", "罵", "第四聲 / 降"),
}
TONE_SYMBOLS = {"1": "ˉ", "2": "ˊ", "3": "ˇ", "4": "ˋ"}

# 已學 ✅ 已覆蓋
LEARNED_INITIALS = {"b","p","m","f","d","t","n"}
LEARNED_FINALS = {"a","o","e","i","u","ü","er"}

# 未學 ❌
NEW_INITIALS = [s for s in INITIALS if s[0] not in LEARNED_INITIALS]
NEW_FINALS_COMPOUND = FINALS_COMPOUND  # 全部未學

# ─────────────────────────────────────────────
# 2. 音頻生成 (Google TTS)
# ─────────────────────────────────────────────

def tts(text: str, lang: str = "zh-CN") -> str | None:
    """用 Google Translate TTS 合成音頻，返回本地檔路徑"""
    safe_name = hashlib.md5(f"{lang}:{text}".encode()).hexdigest()
    path = os.path.join(AUDIO_DIR, f"{safe_name}.mp3")
    if os.path.exists(path):
        return path
    try:
        url = (f"https://translate.google.com/translate_tts"
               f"?ie=UTF-8&q={urllib.parse.quote(text)}&tl={lang}&client=tw-ob")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp, open(path, "wb") as f:
            f.write(resp.read())
        return path
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return None

# ─────────────────────────────────────────────
# 3. 遊戲題庫
# ─────────────────────────────────────────────

class QuizBank:
    """題庫，支援多種題型"""

    @staticmethod
    def tone_quiz():
        """聲調識別：播音，問第幾聲"""
        tone_idx = random.randint(1, 4)
        pinyin, char, desc = TONES[tone_idx]
        # 用普通音節 + 對應聲調
        question_syllable = f"m{pinyin[1:]}"  # m + 去掉m = mā/má/měi/mà
        # 實際用標準音節
        std = {1: "mā", 2: "má", 3: "měi", 4: "mà"}
        std_syllable = std[tone_idx]
        return {
            "type": "tone",
            "question": f"聽聽呢個音，係第幾聲？🔊\n（第1/2/3/4聲）",
            "audio_text": std_syllable,
            "answer": str(tone_idx),
            "hint": f"係 {char} 呢個字嘅音",
        }

    @staticmethod
    def initial_quiz():
        """聲母識別：播音，問係邊個聲母"""
        initials_set = list(INITIALS)
        # 混合：已學 + 未學
        options = random.sample(initials_set, min(4, len(initials_set)))
        correct_init, correct_char = random.choice(options)
        # 造一個音節：聲母 + 韻母
        final = random.choice(["a", "i", "u"])
        syllable = f"{correct_init}{final}"
        return {
            "type": "initial",
            "question": f"聽聽呢個音，係邊個聲母？🔊\n{''.join('[ ' + i[0] + ' ]' for i in options)}",
            "audio_text": syllable,
            "answer": correct_init,
            "options": [i[0] for i in options],
            "hint": f"提示：{correct_char} 字開頭",
        }

    @staticmethod
    def final_quiz():
        """韻母識別：播音，問係邊個韻母"""
        # 全部韻母
        options = random.sample(ALL_FINALS, min(4, len(ALL_FINALS)))
        correct_final, correct_char = random.choice(options)
        # 造音節：b + 韻母
        syllable = f"b{correct_final}"
        return {
            "type": "final",
            "question": f"聽聽呢個音，係邊個韻母？🔊\n{''.join('[ ' + f[0] + ' ]' for f in options)}",
            "audio_text": syllable,
            "answer": correct_final,
            "options": [f[0] for f in options],
            "hint": f"提示：{correct_char} 尾音",
        }

    @staticmethod
    def tone_distinguish():
        """聲調分辨：播放兩個音，問係否同聲"""
        t1 = random.randint(1, 4)
        t2 = random.randint(1, 4)
        correct = "係" if t1 == t2 else "唔係"
        syllables = {1: "mā", 2: "má", 3: "měi", 4: "mà"}
        return {
            "type": "tone_compare",
            "question": f"聽聽兩個音，佢哋聲調相同嗎？🔊\n1️⃣ {syllables[t1]}   2️⃣ {syllables[t2]}",
            "audio_text": f"{syllables[t1]} {syllables[t2]}",
            "answer": correct,
            "options": ["係", "唔係"],
            "hint": f"第1個聲：第{t1}聲  |  第2個聲：第{t2}聲",
        }


# ─────────────────────────────────────────────
# 4. 遊戲狀態機
# ─────────────────────────────────────────────

GAMES = {
    "1": ("聲調識別", QuizBank.tone_quiz),
    "2": ("聲母識別", QuizBank.initial_quiz),
    "3": ("韻母識別", QuizBank.final_quiz),
    "4": ("聲調分辨", QuizBank.tone_distinguish),
}


def new_question(game_type: str = None):
    if game_type and game_type in GAMES:
        _, generator = GAMES[game_type]
    else:
        _, generator = random.choice(list(GAMES.values()))
    return generator()


def format_question(q: dict, score: int, streak: int, total: int) -> str:
    emoji = "🎯" if q["type"] == "initial" else \
            "🎶" if q["type"] in ("tone","tone_compare") else \
            "🔤"
    return (
        f"{emoji} 問題 {total}\n"
        f"─────────────────\n"
        f"{q['question']}\n"
        f"─────────────────\n"
        f"🏆 {score}分  |  🔥 {streak}連勝\n\n"
        f"回覆數字作答，或傳送：\n"
        f"・「提示」- 顯示提示\n"
        f"・ replay - 再聽一次\n"
        f"・ menu - 返回主目錄\n"
        f"・ quit - 結束遊戲"
    )


def format_result(q: dict, correct: bool, answer: str) -> str:
    if correct:
        return (f"✅ 正確！ {q['answer']}\n"
                f"─────────────────\n"
                f"好嘢！下一題...")
    else:
        return (f"❌ 正確答案：{q['answer']}\n"
                f"─────────────────\n"
                f"你答咗：{answer}\n"
                f"📝 {q.get('hint', '')}\n\n"
                f"下一題...")


def main_menu() -> str:
    menu = (
        "🇨🇳 普通話發音學習遊戲\n"
        "─────────────────\n"
        "你想練習邊個部分？\n\n"
        "1️⃣ 聲調識別（聽音，答1-4聲）\n"
        "2️⃣ 聲母識別（聽音，答聲母）\n"
        "3️⃣ 韻母識別（聽音，答韻母）\n"
        "4️⃣ 聲調分辨（兩音是否同聲）\n"
        "5️⃣ 全部混合練習\n\n"
        "傳送數字 1-5 開始！"
    )
    return menu


# ─────────────────────────────────────────────
# 5. CLI / WhatsApp handler (for nanobot)
# ─────────────────────────────────────────────

class PinyinGame:
    """WhatsApp 對話狀態機"""

    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.state = "menu"          # menu | playing | waiting_answer
        self.game_type = None       # "1"-"4" or "mixed"
        self.score = 0
        self.streak = 0
        self.total = 0
        self.current_q = None
        self.round = 0

    def handle(self, text: str) -> dict:
        """處理用戶輸入，返回回覆訊息 + (可選)音頻檔"""
        text = text.strip()

        # quit
        if text.lower() in ("quit", "q", "exit", "結束", "停"):
            self.state = "menu"
            result = (
                f"👋 遊戲結束！\n"
                f"最終成績：{self.score}分 / {self.total}題\n"
                f"最佳連勝：{self.streak}\n\n"
                f"再玩請傳送數字 1-5"
            )
            return {"text": result}

        # menu
        if text.lower() in ("menu", "m", "主目錄", "目錄"):
            self.state = "menu"
            return {"text": main_menu()}

        # menu state
        if self.state == "menu":
            if text in ("1","2","3","4"):
                self.game_type = text
                self._start_game()
            elif text == "5":
                self.game_type = "mixed"
                self._start_game()
            else:
                return {"text": main_menu()}
            return self._send_question()

        # playing state
        if self.state == "waiting_answer":
            # Special commands
            if text.lower() == "replay":
                audio = tts(self.current_q["audio_text"])
                return {"text": f"🔊 再聽一次：{self.current_q['audio_text']}", "audio": audio}

            if text in ("提示", "hint", "💡"):
                hint = self.current_q.get("hint", "無提示")
                return {"text": f"💡 {hint}\n\n請繼續作答："}

            # Check answer
            self.total += 1
            correct_ans = str(self.current_q["answer"]).lower()
            user_ans = text.strip().lower()

            correct = (user_ans == correct_ans)
            if correct:
                self.score += 1
                self.streak += 1
                streak_bonus = f" 🔥 {self.streak}連勝！" if self.streak >= 2 else ""
                result_text = (
                    f"✅ 正確！ {self.current_q['answer']}{streak_bonus}\n"
                )
            else:
                self.streak = 0
                hint = self.current_q.get("hint", "")
                result_text = (
                    f"❌ 正確答案：{self.current_q['answer']}\n"
                    f"你答咗：{text} {hint}\n"
                )

            # Next question
            self.round += 1
            if self.round >= 10:
                self.state = "menu"
                return {
                    "text": (
                        f"🎉 完成10題！\n"
                        f"得分：{self.score}/10\n"
                        f"─────────────────\n"
                        f"再玩請傳送 1-5"
                    ),
                    "audio": None
                }

            self._next_question()
            resp = self._send_question()
            resp["text"] = result_text + "\n" + resp["text"]
            return resp

        return {"text": main_menu()}

    def _start_game(self):
        self.state = "waiting_answer"
        self.score = 0
        self.streak = 0
        self.total = 0
        self.round = 0
        self._next_question()

    def _next_question(self):
        if self.game_type == "mixed":
            self.current_q = new_question()
        elif self.game_type in GAMES:
            _, generator = GAMES[self.game_type]
            self.current_q = generator()
        else:
            self.current_q = new_question()

    def _send_question(self) -> dict:
        audio = tts(self.current_q["audio_text"])
        text = format_question(self.current_q, self.score, self.streak, self.total)
        return {"text": text, "audio": audio}


# ─────────────────────────────────────────────
# 6. 主程式 / CLI 測試
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🎮 普通話發音學習遊戲 — CLI 測試模式")
    print(main_menu())
    game = PinyinGame("cli")
    game.state = "menu"

    while True:
        user_input = input("\n👉 你：")
        resp = game.handle(user_input)
        print(f"\n🤖 機器人：\n{resp['text']}")
        if resp.get("audio"):
            print(f"🔊 音頻：{resp['audio']}")
        if game.state == "menu" and user_input not in ("1","2","3","4","5","menu","m"):
            break
