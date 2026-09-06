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
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import threads as threads_client  # noqa: E402

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"

SLOT_THEMES = {
    "morning": "今日一日の総合運。前向きに一日を始められるような言葉を添える。",
    "noon": "恋愛運または人間関係運。具体的な行動のヒントを1つ入れる。",
    "night": "今日一日を振り返る運勢と、明日に向けた開運アクション。",
}


def build_prompt(slot: str) -> str:
    theme = SLOT_THEMES.get(slot, SLOT_THEMES["morning"])
    return (
        "あなたは占いアカウント「灯（ともしび）」の運営者です。"
        "Threadsに投稿する占いの文章を1つ作成してください。\n\n"
        f"テーマ: {theme}\n\n"
        "条件:\n"
        "- 日本語、200〜400文字程度\n"
        "- 絵文字は控えめに1〜2個まで\n"
        "- ラッキーカラー/アイテム/一言アドバイスなど、読み手が今日試したくなる"
        "具体的な要素を1つ入れる\n"
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
