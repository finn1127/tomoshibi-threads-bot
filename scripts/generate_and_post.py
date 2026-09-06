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

PERSONA = "あなたは占いアカウント「灯（あかり）」の中の人です。"

CATEGORIES = ["恋愛", "金運", "仕事", "家族", "人間関係", "自分自身のこと", "これからの選択"]

# 反応の良かった他アカウントの投稿を分析して抽出した「型」。
# 詳細・具体例は notes/reference-posts.md を参照。増えたらここに追記する。
FORMATS = [
    {
        "name": "ranking",
        "instructions": (
            "【ランキング型】煽り文句のフックで始める→生まれ月×星座の組み合わせに"
            "よるランキング表（1位〜5〜10位、🥇🥈🥉等の絵文字メダルを使う）→"
            "該当者への説明で締める。全員共通の説明でもよいし、各順位に「→」で"
            "個別の一言を付けてもよい。星座のみ・生まれ月なしのシンプル版でもよい。"
        ),
    },
    {
        "name": "declarative",
        "instructions": (
            "【断定・宣言型】ヘッジや前置きなしで、短い改行区切りの文で強く言い切る。"
            "「覚悟してください」「はっきりと結論が出ました」のような前置きから始め、"
            "断定的な短文を積み重ね、最後は絵文字で希望を示して締める。"
        ),
    },
    {
        "name": "urgent_announcement",
        "instructions": (
            "【緊急発表・日付予告型】「緊急発表！」等の強い一言と感嘆符の連打で始め、"
            "具体的な日付（今日から数日以内）を出して期待感を煽り、「超」等の強調語を"
            "繰り返し、最後は読み手に問いかける一文で締める。"
        ),
    },
    {
        "name": "like_conditional",
        "instructions": (
            "【いいね連動型】「私は嘘は言いません」等の信頼フックで始め、「◯月◯日から"
            "◯日にいいねできたあなた」のように直近の日付範囲でのいいね行動を条件にして"
            "自分ごと化させ、断定的な励ましと反復フレーズ（「大丈夫、大丈夫」等）で締める。"
        ),
    },
    {
        "name": "initial_based",
        "instructions": (
            "【イニシャル型】「ごめんなさい。強力なので注意してください」等の警告フックで"
            "始め、イニシャルの組み合わせ（多くの文字を含めて該当率を高くする）で対象を"
            "絞り、三段列挙（〜たり、〜たり、〜たり、で具体例を3つ並べる）を使い、"
            "最後に断定で締める。"
        ),
    },
]

SLOT_STYLES = {
    "morning": "今日一日の始まりにふさわしい、前向きな視点で。",
    "noon": "日中にふと立ち止まったときに、そっと響くような視点で。",
    "night": "今日一日を振り返り、明日への一言を添える視点で。",
}


def build_prompt(slot: str) -> str:
    category = random.choice(CATEGORIES)
    fmt = random.choice(FORMATS)
    style = SLOT_STYLES.get(slot, SLOT_STYLES["morning"])
    return (
        f"{PERSONA}\n\n"
        "Threadsに投稿する占いの文章を1つ作成してください。\n\n"
        f"テーマ: 「{category}」について。{style}\n\n"
        f"{fmt['instructions']}\n\n"
        "条件:\n"
        "- 日本語、200〜400文字程度\n"
        "- 上記の型の構成・テクニックに忠実に、読み手が「自分ごと」だと感じて"
        "続きが気になる文章にする\n"
        "- 具体的な数字（日付・順位・生まれ月・星座・イニシャル等）は型に応じて"
        "自然になるよう自分で考えて入れる\n"
        "- 絵文字は型の雰囲気に合わせて適度に使ってよい\n"
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
