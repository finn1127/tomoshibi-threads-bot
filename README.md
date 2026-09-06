# 灯（占いアカウント）Threads自動運用

GitHub Actions + Claude API + Threads API で、占いアカウントの投稿を
完全自動化する仕組み。PCの電源に関係なく、GitHub側で1日3回自動投稿される。

## 構成

```
.github/workflows/post.yml   GitHub Actionsの定時実行設定（毎日 朝8:00/昼12:30/夜20:00 JST）
scripts/threads.py           Threads APIクライアント（whoami / post / refresh）
scripts/generate_and_post.py Claude APIで投稿文を生成し、Threadsに投稿するメイン処理
.env.example                 ローカル動作確認用の環境変数テンプレート
```

本番の投稿はGitHub Actions上で動くため、`.env`はローカルでの動作確認用。
実際の秘密情報はGitHubリポジトリの「Secrets」に登録する。

## セットアップ手順

### 1. Threads APIの認証情報を取得（あなたの操作が必要・ログイン必須）

1. Threadsアプリ → プロフィール → 設定 → アカウントの種類を切り替える →
   「プロフェッショナルアカウント」にする
2. https://developers.facebook.com/apps → 「アプリを作成」→ 種類は「その他」
3. アプリダッシュボード →「製品を追加」→「Threads API」を追加
4. 「Threads API」→「API設定」画面で「Threadsテスターを追加」→ 自分の
   Threadsアカウントを招待 → Threadsアプリ側の設定 → アカウント →
   プロフェッショナルの各種設定から招待を承認
5. 同じ画面の「トークンを生成」で `threads_basic` と
   `threads_content_publish` をチェックしてアクセストークンを生成
   → このトークンは**チャットに貼らず**、直接 `.env` かGitHub Secretsに保存

### 2. Anthropic APIキーを取得

https://console.anthropic.com/ → API Keys → 新規作成
（Claude Codeのサブスクリプションとは別に、API従量課金が発生します）

### 3. ローカルで一度だけ動作確認（任意だが推奨）

```bash
cp .env.example .env
# .env を開いて THREADS_ACCESS_TOKEN を貼り付け

python3 scripts/threads.py whoami
# 表示された id を .env の THREADS_USER_ID に追記

python3 scripts/threads.py post "テスト投稿です"
# Threadsに実際に投稿されるので確認したら削除してOK
```

### 4. GitHubリポジトリを作成してSecretsを登録

`gh` コマンドのインストール・ログインが必要です（あなたの操作が必要）。

```bash
brew install gh
gh auth login
```

ログインできたら教えてください。そこから先（リポジトリ作成・push・
Secrets登録の下準備）は私が進められますが、以下の3つの値は
**あなた自身の端末で**登録してください（チャットに秘密情報を貼らないため）。

```bash
gh secret set ANTHROPIC_API_KEY
gh secret set THREADS_ACCESS_TOKEN
gh secret set THREADS_USER_ID
```

（それぞれ実行すると値の入力を求められます）

### 5. 動作確認

GitHubリポジトリの Actions タブ →「灯 自動投稿」→「Run workflow」で
手動実行して、Threadsに投稿されるか確認する。

## 投稿の時間帯とテーマ

`scripts/generate_and_post.py` の `SLOT_THEMES` で管理。

- morning（朝8:00）: 今日一日の総合運
- noon（昼12:30）: 恋愛運・人間関係運
- night（夜20:00）: 一日の振り返り＋明日の開運アクション

文言や時間帯はここを編集すれば変更できる。

## トークンの更新（月1回程度）

Threadsの長期アクセストークンは60日で失効する。以下をローカルで実行し、
出力された新しいトークンを `gh secret set THREADS_ACCESS_TOKEN` で
登録し直す。

```bash
python3 scripts/threads.py refresh
```

## 今後の改善候補（必要になったら）

- 直近の投稿内容をリポジトリ内に記録し、内容の重複を避ける
- 投稿前にNGワード・トーンチェックを挟む
- 反応の良かった投稿パターンを分析して自動で改善する
