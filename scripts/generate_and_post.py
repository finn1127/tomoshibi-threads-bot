#!/usr/bin/env python3
"""
占いアカウント「灯」用: Claude APIで投稿文を生成し、Threadsに投稿する。

環境変数:
  ANTHROPIC_API_KEY    (必須) Claude APIキー
  THREADS_ACCESS_TOKEN (必須) threads.pyが使用
  THREADS_USER_ID      (必須) threads.pyが使用
  SLOT                 (任意) morning / noon / night。省略時は morning
"""
import json
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import threads as threads_client  # noqa: E402

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"

PERSONA = (
    "あなたは「灯（あかり）」。もともとはどこにでもいる会社員だったが、"
    "二十九のときに心が折れて山に通うようになり、そこで風や精霊の声が聴こえる"
    "ようになった。精霊は不思議な言い方をする人物で、お金のことを「巡りのしるし」、"
    "涙を「余った雨」と呼ぶ。灯は、その言葉を日常の言葉に訳して届ける通訳のような"
    "存在で、当てることはしない。ただ、読み手の奥でずっと鳴っている音を、"
    "風ごしに聞き取ってそっと渡す。良いこともそうでないことも隠さず伝えるが、"
    "押しつけはしない。今扱っているテーマは、恋愛・金運・仕事・家族・人間関係・"
    "自分自身のこと・これからの選択の7つ。"
)

CATEGORIES = ["恋愛", "金運", "仕事", "家族", "人間関係", "自分自身のこと", "これからの選択"]

SLOT_STYLES = {
    "morning": "今日一日の始まりにふさわしい、前向きな視点で。",
    "noon": "日中にふと立ち止まったときに、そっと響くような視点で。",
    "night": "今日一日を振り返り、明日への一言を添える視点で。",
}


def build_prompt(slot: str) -> str:
    category = random.choice(CATEGORIES)
    style = SLOT_STYLES.get(slot, SLOT_STYLES["morning"])
    theme = f"「{category}」というテーマで、{style}"
    return (
        f"{PERSONA}\n\n"
        "この人物として、Threadsに投稿する文章を1つ作成してください。\n\n"
        f"テーマ: {theme}\n\n"
        "条件:\n"
        "- 日本語、200〜400文字程度\n"
        "- 「〜やで」のような特定の方言は使わず、静かで詩的な語り口にする\n"
        "- 「巡りのしるし」「余った雨」のように、精霊の言葉を独自の比喩に言い換える表現を"
        "1つ以上入れる\n"
        "- 絵文字は使わないか、使っても1個までにする\n"
        "- 過度に断定的な健康・金銭・恋愛の助言は避け、あくまでエンタメとして楽しめる文体にする\n"
        "- 投稿本文のみを出力する（前置き・説明・鍵カッコは付けない）\n"
    )


def generate_text(slot: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = json.dumps(
        {
            "model": MODEL,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": build_prompt(slot)}],
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Claude APIエラー ({e.code}): {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    text = "".join(
        block["text"] for block in result["content"] if block.get("type") == "text"
    ).strip()
    if not text:
        print(f"Claudeから本文を取得できませんでした: {result}", file=sys.stderr)
        sys.exit(1)
    return text


def main():
    slot = os.environ.get("SLOT", "morning")
    text = generate_text(slot)
    print(f"[{slot}] 生成された投稿文:\n{text}\n")

    env = threads_client.load_env()
    threads_client.cmd_post(env, text)


if __name__ == "__main__":
    main()
