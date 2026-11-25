# 夜更けの地図：Firebase の準備（秋輝が1回だけ行う）

> **2026-11-18 済み**（秋輝と Claude で Chrome から実施）：部の Google アカウント（yofukashi.bunkabu）でプロジェクト `yofukashi-bunkabu` を作成（Spark・無料、アナリティクス／Gemini／デベロッパープログラムはオフ）。Google ログインを有効化（公開名「夜更文化部」、サポートメールは部の Gmail）、承認済みドメインに `yofukashi-bunkabu.github.io`、Firestore（Standard・東京 asia-northeast1・本番モード）に `firestore.rules` を公開、ウェブアプリ「夜更けの地図」を登録して `site/map/firebase-config.js` に設定を入れた。同日、秋輝の個人アカウントでログインし、管理者（admins）に登録済み。記録の保存・読み出し・削除が本番で動くことも確かめた（仮の記録は消した）。
>
> **ログインのつまずき**：Google の画面は「アカウントを選ぶ」→「yofukashi-bunkabu.firebaseapp.com にログイン（名前・メールを共有）」の2段。2段目で「次へ」を押さないとログインが終わらない。参加者に案内するときは「2回目の画面で『次へ』」と書く。

`site/map/` は、Firebase の設定（`site/map/firebase-config.js`）が空のあいだ「試し表示」で動きます。
本番にするには、秋輝さんの Google アカウントで次を行います（所要20分ほど・無料の Spark プラン）。
Claude はアカウントやプロジェクトを作れないので、ここだけは秋輝さんの操作です。終わったら 5. の値を Claude に渡してください。

## 1. プロジェクトを作る
1. https://console.firebase.google.com/ を開き、「プロジェクトを作成」
2. 名前：`yofukashi-bunkabu`（使えなければ候補の名前でよい）
3. Google アナリティクス：**オフ**（使わない。privacy.html にも「解析なし」と書いている）

## 2. Google ログインを有効にする
1. 左の「構築」→「Authentication」→「始める」
2. 「Sign-in method」→「Google」→ 有効にする → プロジェクトのサポートメールを選んで保存
3. 「Settings」→「承認済みドメイン」に `yofukashi-bunkabu.github.io` を追加（独自ドメインにしたら `yofukashi-bunkabu.com` と `www.yofukashi-bunkabu.com` も追加）

## 3. データベースを作る
1. 「構築」→「Firestore Database」→「データベースの作成」
2. 場所：`asia-northeast1（東京）`、**本番環境モード**で開始
3. 「ルール」タブに、このリポジトリの `firestore.rules` の全文を貼って「公開」

## 4. 管理者を入れる（コンソールの「データ」タブで手で作る）
1. 本番の地図に一度 Google でログインしたあと、Authentication の「Users」に出る自分の「ユーザー UID」をコピー
2. コレクション `admins` → ドキュメント ID ＝ その UID → フィールド `since`（文字列）＝ 今日の日付
   → 管理者は、公開された口コミを非表示（削除）にできます。自分だけの口コミは管理者でも読めません

## 5. ウェブアプリを登録して、設定を渡す
1. プロジェクトの概要 →「</>（ウェブ）」でアプリを追加。名前：`夜更けの地図`。Firebase Hosting は**使わない**（GitHub Pages で出す）
2. 出てくる `firebaseConfig` の `apiKey`・`authDomain`・`projectId`・`appId` を Claude に渡す
   - これらは公開して困らない値です（守りは 3. のルールで行う）
3. Claude が `site/map/firebase-config.js` に入れて push → 本番になります
