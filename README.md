# 灯（占いアカウント）Threads自動運用

GitHub Actions + Claude API + Threads API で、占いアカウントの投稿を
完全自動化する仕組み。PCの電源に関係なく、GitHub側で1日3回自動投稿される。

## 構成

```
.github/workflows/post.yml   GitHub Actionsの定時実行設定（毎日 朝6:30/昼11:55/夜20:00 JST）
scripts/threads.py           Threads APIクライアント（auth / whoami / post / refresh）
scripts/generate_and_post.py Claude APIで投稿文を生成し、Threadsに投稿するメイン処理
.env.example                 ローカル動作確認用の環境変数テンプレート
```

本番の投稿はGitHub Actions上で動くため、`.env`はローカルでの動作確認用。
実際の秘密情報はGitHubリポジトリの「Secrets」に登録する。

## セットアップ手順

### 1. Threads APIの認証情報を取得（あなたの操作が必要・ログイン必須）

Threads APIにはダッシュボードに「トークンを生成」ボタンは無く、OAuth認可という
手順を踏む必要があります。手順3以降は`scripts/threads.py auth`が自動でやって
くれるので、curlを手打ちする必要はありません。

1. Threadsアプリ → プロフィール → 設定 → アカウントの種類を切り替える →
   「プロフェッショナルアカウント」にする
2. https://developers.facebook.com/apps → 「アプリを作成」→ 種類は「その他」
   →「製品を追加」→「Threads API」を追加
3. **自分をテスターとして追加する**
   - App Dashboard 左メニュー →「App roles」（アプリの役割）→「Roles」タブ
   - 「Add People」ボタン →ロールで「Threads Tester」を選択→自分のThreads
     ユーザー名を入力して招待を送る
   - スマホのThreadsアプリ →プロフィール→設定とアクティビティ→アカウント→
     「ウェブサイトの権限」(Website permissions) →届いている招待を承認
4. **リダイレクトURLを登録する**
   - App Dashboard →「Threads API」→「Settings」タブ →
     「Redirect Callback URLs」に `https://localhost/` を追加して保存
5. **App IDとApp Secretを控える**
   - App Dashboard →「App settings」→「Basic」に表示されている
     Threads App ID / Threads App Secret
6. **トークンを取得する**（チャットに秘密情報を貼らずに済むよう対話式）
   ```bash
   python3 scripts/threads.py auth
   ```
   App ID / App Secretを入力すると認可用URLが表示されるので、ブラウザで開いて
   ログイン・許可 → リダイレクト先URLの `code=` の値を貼り付ける、という流れ
   で長期アクセストークンとユーザーIDが自動で`.env`に保存されます。

### 2. Anthropic APIキーを取得

https://console.anthropic.com/ → API Keys → 新規作成
（Claude Codeのサブスクリプションとは別に、API従量課金が発生します）

### 3. ローカルで一度だけ動作確認（推奨）

```bash
cp .env.example .env
python3 scripts/threads.py auth
# 手順1-6で取得したApp ID/Secretを入力 → .env に自動保存される

python3 scripts/threads.py whoami
# アカウント情報が表示されればOK

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

`scripts/generate_and_post.py` で管理。

- morning（朝6:30）: 無料鑑定の募集投稿（「固定ポストのリンクから」と案内）
- noon（昼11:55）: 7テーマ×フォーマットからランダムに1つ選んで生成
- night（夜20:00）: 無料鑑定の募集投稿（「固定ポストのリンクから」と案内）

文言や時間帯はここを編集すれば変更できる。参考にした投稿の型は
`notes/reference-posts.md` を参照。

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
