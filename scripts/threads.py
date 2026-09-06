#!/usr/bin/env python3
"""
Threads API クライアント（占いアカウント「灯」用）

サブコマンド:
  auth            OAuth認可フローを対話式に実行し、長期アクセストークンを取得して .env に保存する
  whoami          トークンが有効か確認し、アカウント情報を表示する
  post <text>     テキストをThreadsに投稿する
  refresh         長期アクセストークンを更新し .env に書き戻す

認証情報は同じディレクトリの .env から読む（THREADS_ACCESS_TOKEN, THREADS_USER_ID）。
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://graph.threads.net/v1.0"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env():
    """.env（ローカル開発用）があれば読み、無ければ環境変数（GitHub Actions等）を使う"""
    env = dict(os.environ)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def save_env(updates: dict):
    lines = []
    seen = set()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
            if m and m.group(1) in updates:
                key = m.group(1)
                lines.append(f"{key}={updates[key]}")
                seen.add(key)
            else:
                lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def api_request(method: str, path: str, params: dict):
    url = f"{API_BASE}{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"APIエラー ({e.code}): {body}", file=sys.stderr)
        sys.exit(1)


def cmd_whoami(env):
    token = env.get("THREADS_ACCESS_TOKEN")
    if not token:
        print(".env に THREADS_ACCESS_TOKEN がありません", file=sys.stderr)
        sys.exit(1)
    result = api_request("GET", "/me", {"fields": "id,username,threads_profile_picture_url", "access_token": token})
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_post(env, text: str):
    token = env.get("THREADS_ACCESS_TOKEN")
    user_id = env.get("THREADS_USER_ID")
    if not token or not user_id:
        print(".env に THREADS_ACCESS_TOKEN / THREADS_USER_ID が必要です", file=sys.stderr)
        sys.exit(1)

    created = api_request(
        "POST",
        f"/{user_id}/threads",
        {"media_type": "TEXT", "text": text, "access_token": token},
    )
    creation_id = created.get("id")
    if not creation_id:
        print(f"投稿コンテナの作成に失敗しました: {created}", file=sys.stderr)
        sys.exit(1)

    import time

    time.sleep(5)  # Meta推奨: publish前に数秒待つ

    published = api_request(
        "POST",
        f"/{user_id}/threads_publish",
        {"creation_id": creation_id, "access_token": token},
    )
    if "id" not in published:
        print(f"投稿の公開に失敗しました: {published}", file=sys.stderr)
        sys.exit(1)

    print(f"投稿完了: post id = {published['id']}")


REDIRECT_URI = "https://localhost/"


def cmd_auth():
    import getpass
    import subprocess
    import webbrowser

    print("Meta App Dashboard > 左メニュー「App settings」>「Basic」で確認できる値を入力してください。\n")
    app_id = input("Threads App ID: ").strip()
    app_secret = getpass.getpass("Threads App Secret（入力は画面に表示されません）: ").strip()
    if not app_id or not app_secret:
        print("App ID / App Secret が空です。もう一度実行してください。", file=sys.stderr)
        sys.exit(1)

    authorize_url = (
        "https://threads.net/oauth/authorize"
        f"?client_id={urllib.parse.quote(app_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        "&scope=threads_basic,threads_content_publish"
        "&response_type=code"
    )
    print("\n事前に「App Dashboard > アプリの設定 > 詳細設定」の")
    print(f"「コールバックURLを許可」に {REDIRECT_URI} を追加・保存しておいてください。\n")

    copied = False
    try:
        subprocess.run(["pbcopy"], input=authorize_url.encode(), check=True)
        copied = True
    except Exception:
        pass

    opened = False
    try:
        opened = webbrowser.open(authorize_url)
    except Exception:
        pass

    print("1. 認可用URLをブラウザで開いて、Threadsアカウントでログイン・許可してください。")
    if opened:
        print("   → ブラウザを自動で開きました。開かなければ下のURLを使ってください。")
    if copied:
        print("   → URLはクリップボードにコピー済みです（そのまま貼り付け可）。")
    print(f"\n   {authorize_url}\n")
    print("   ※ 手動でコピーする場合、URLが長く途中で切れやすいので、")
    print("     可能な限り上記のクリップボードコピー機能を使ってください。\n")
    print("2. 許可すると https://localhost/?code=XXXX...#_ のようなURLに")
    print("   遷移しようとします（ページが表示されずエラーになりますが問題ありません）。")
    print("   アドレスバーに表示された code= から #_ の手前までの文字列をコピーしてください。\n")
    code = input("コピーした code の値を貼り付けてください: ").strip()
    if not code:
        print("code が空です。もう一度実行してください。", file=sys.stderr)
        sys.exit(1)

    token_data = urllib.parse.urlencode(
        {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }
    ).encode()
    req = urllib.request.Request(
        "https://graph.threads.net/oauth/access_token", data=token_data, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            short_lived = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"短期トークンの取得に失敗しました: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    short_token = short_lived.get("access_token")
    if not short_token:
        print(f"短期トークンの取得に失敗しました: {short_lived}", file=sys.stderr)
        sys.exit(1)

    long_lived = api_request(
        "GET",
        "/access_token",
        {
            "grant_type": "th_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token,
        },
    )
    long_token = long_lived.get("access_token")
    if not long_token:
        print(f"長期トークンへの交換に失敗しました: {long_lived}", file=sys.stderr)
        sys.exit(1)

    save_env({"THREADS_ACCESS_TOKEN": long_token})
    print(f"\n長期アクセストークンを .env に保存しました（有効期限: 約{long_lived.get('expires_in', '?')}秒後）")

    who = api_request("GET", "/me", {"fields": "id,username", "access_token": long_token})
    print(json.dumps(who, ensure_ascii=False))
    if who.get("id"):
        save_env({"THREADS_USER_ID": who["id"]})
        print("THREADS_USER_ID も .env に保存しました")


def cmd_refresh(env):
    token = env.get("THREADS_ACCESS_TOKEN")
    if not token:
        print(".env に THREADS_ACCESS_TOKEN がありません", file=sys.stderr)
        sys.exit(1)
    result = api_request(
        "GET",
        "/refresh_access_token",
        {"grant_type": "th_refresh_token", "access_token": token},
    )
    new_token = result.get("access_token")
    if not new_token:
        print(f"更新に失敗しました: {result}", file=sys.stderr)
        sys.exit(1)
    save_env({"THREADS_ACCESS_TOKEN": new_token})
    print(f"トークンを更新しました（有効期限: 約{result.get('expires_in', '?')}秒後）")


def main():
    env = load_env()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "auth":
        cmd_auth()
    elif cmd == "whoami":
        cmd_whoami(env)
    elif cmd == "post":
        if len(sys.argv) < 3:
            print("使い方: threads.py post \"投稿テキスト\"", file=sys.stderr)
            sys.exit(1)
        cmd_post(env, sys.argv[2])
    elif cmd == "refresh":
        cmd_refresh(env)
    else:
        print(f"不明なコマンド: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
