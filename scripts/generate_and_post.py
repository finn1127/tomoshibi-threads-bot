#!/usr/bin/env python3
"""
占いアカウント「灯」用: Claude APIで投稿文を生成し、Threadsに投稿する。

環境変数:
  ANTHROPIC_API_KEY    (必須) Claude APIキー
  THREADS_ACCESS_TOKEN (必須) threads.pyが使用
  THREADS_USER_ID      (必須) threads.pyが使用
  SLOT                 (任意) morning / noon / night。省略時は morning
                       morning・nightは無料鑑定の募集投稿、noonはランダム投稿
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
    "存在。フォロワーのことは「風待ちさん」と呼ぶ（風の便りを待っている人、という意味）。"
)

CATEGORIES = ["恋愛", "金運", "仕事", "家族", "人間関係", "自分自身のこと", "これからの選択"]

# 反応の良かった他アカウントの投稿を分析して抽出した「型」。
# 詳細・具体例は notes/reference-posts.md を参照。増えたらここに追記する。
FORMATS = [
    {
        "name": "ranking",
        "instructions": (
            "【ランキング型】煽り文句のフックで始める→生まれ月×星座、または星座のみの"
            "ランキング表（🥇🥈🥉等の絵文字メダルを使う）→該当者への説明で締める。"
            "以下のバリエーションから自由に選んでよい: "
            "(a) 上位5〜10位までのランキング＋全員共通または個別（「→」で一言）の説明、"
            "(b) 12星座すべてを載せ、各順位に「今日中に」「5時間以内に」のような"
            "バラバラの期限を付けるバージョン（全員が自分の順位を見つけられる）。"
            "締めに『✨』等の絵文字をコメントに置いてもらうCTAを添えてもよい。"
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
    {
        "name": "ultra_short",
        "instructions": (
            "【超短文型】本文はできる限り短く、10〜20文字程度の一文だけで終える。"
            "読んだ瞬間に「うん、そうだよね」と心の中で同意したくなるような、"
            "断定でも質問でもない静かな一言にする（例のような直接的な文言はそのまま"
            "使わず、灯らしい言い回しで新しく考える）。"
            "本文の後に一行空けて、いいねやコメントに意味を持たせる一言を添えてもよい"
            "（例:「いいねは、風に届いた合図」「コメントに一言くれたら、風待ちさんの"
            "声から先に届けます」など）。"
        ),
    },
    {
        "name": "pre_celebration",
        "instructions": (
            "【予祝コメント型】まだ起きていない読み手の願いを、先に「おめでとう」と"
            "祝う形で始める→「叶えたいことをコメントに書いてください」と促す→"
            "「書いてくれた風待ちさんから先に、風に尋ねます」のように、コメントする"
            "meritを示して背中を押す、という3段構成。"
        ),
    },
]

SLOT_STYLES = {
    "morning": "今日一日の始まりにふさわしい、前向きな視点で。",
    "noon": "日中にふと立ち止まったときに、そっと響くような視点で。",
    "night": "今日一日を振り返り、明日への一言を添える視点で。",
}

# 無料鑑定の募集投稿（朝・夜枠）用。詳細は notes/reference-posts.md の
# 「無料鑑定募集型」を参照。
RECRUITMENT_INSTRUCTIONS = (
    "無料の個別鑑定への応募を募る投稿を作成してください。\n"
    "以下の要素を必ず含め、毎回少し違う言い回しで書いてください（同じ文章の"
    "使い回しは避ける）:\n"
    "- 良いことだけでなく、風から聞こえたことを全部伝える、という誠実さのアピール\n"
    "- 鑑定の言葉は一人ひとり違う、テンプレートは使わない、というアピール\n"
    "- フォロー・いいねをしてくれた「風待ちさん」から先に風に尋ねる、という優先順位の説明\n"
    "- 応募方法として「🕯️を置いて、固定ポストのリンクからお越しください」という"
    "趣旨のCTA（URLそのものは書かない。リンクは固定投稿にのみ貼ってあるため。"
    "LINEという言葉は使わず、リンク先が何かは明言しない）\n"
)


def build_recruitment_prompt() -> str:
    return (
        f"{PERSONA}\n\n"
        "この人物として、Threadsに投稿する文章を1つ作成してください。\n\n"
        f"{RECRUITMENT_INSTRUCTIONS}\n"
        "条件:\n"
        "- 日本語、200〜400文字程度\n"
        "- 静かで丁寧な語り口。「巡りのしるし」のような灯らしい比喩を1つ以上入れてよい\n"
        "- 絵文字は🕯️を含めて1〜2個程度\n"
        "- 投稿本文のみを出力する（前置き・説明・鍵カッコは付けない）\n"
    )


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
        "- 日本語。文字数は型の指示に従う（指示がなければ200〜400文字程度）\n"
        "- 上記の型の構成・テクニックに忠実に、読み手が「自分ごと」だと感じて"
        "続きが気になる文章にする\n"
        "- ただし断定するときも、素の断定ではなく「風がそう言っている」"
        "「精霊がそう伝えてくる」のように風・精霊からの伝聞という体にする。"
        "「巡りのしるし」「余った雨」のような、灯らしい独自の比喩表現を"
        "1つ以上入れる\n"
        "- 具体的な数字（日付・順位・生まれ月・星座・イニシャル等）は型に応じて"
        "自然になるよう自分で考えて入れる\n"
        "- 絵文字は型の雰囲気に合わせて適度に使ってよい\n"
        "- 投稿本文のみを出力する（前置き・説明・鍵カッコは付けない）\n"
    )


def call_claude(prompt: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = json.dumps(
        {
            "model": MODEL,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
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
    env = threads_client.load_env()

    if slot in ("morning", "night"):
        text = call_claude(build_recruitment_prompt())
        print(f"[{slot}] 募集投稿:\n{text}\n")
        post_id = threads_client.post_text(env, text)
        print(f"投稿完了: post id = {post_id}")
    else:
        text = call_claude(build_prompt(slot))
        print(f"[{slot}] 生成された投稿文:\n{text}\n")
        post_id = threads_client.post_text(env, text)
        print(f"投稿完了: post id = {post_id}")


if __name__ == "__main__":
    main()
