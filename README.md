# 夜更文化部のホームページ

夜更文化部（よふかしぶんかぶ）の HP です。GitHub Pages で公開しています（2026-11-18 から。それまでは STUDIO に埋め込む「窓」だけのリポジトリ `hp-widget` でした）。

- 公開先：https://yofukashi-bunkabu.com/ （独自ドメイン、2026-11-25 取得。旧 https://yofukashi-bunkabu.github.io/ は自動でこちらへ転送）
  - 公開先の URL は `config.json` の `site_url` だけで決まる。ページ内では `{{site}}` と書くと build.py が置き換え、`CNAME`・`sitemap.xml`・`robots.txt` も書き出す
- 更新：毎朝6時（日本時間）と、`main` に push したとき（GitHub Actions「窓を更新」）。会を公開して `data/events.json` に足すと、トップの「次の会」と「会の一覧」が自動で増える
- 文章の正本：`../夜更文化部/HP/構成と文章_v2.md`（8段）。デザインは A「夜の縦組み」

## ページ
| パス | 中身 |
|---|---|
| `/` | トップ（8段：トップ／こんな人へ／1回の流れ／はじめての方へ／続いている記録／次の会／主催のこと／フッター） |
| `/events/` | これからの会・これまでの会（`data/events.json` から作る） |
| `/yoshu/` | 予習シートの見本（No.01 東京都美術館） |
| `/journal/` | note「美術館制覇記」の記事（RSS から作る）と、地図の「みんなに公開」の口コミ |
| `/map/` | 夜更けの地図（下の節） |
| `/widget/` | 埋め込み用の小さな窓（旧 hp-widget のトップ。いまは使っていない） |

## 作り
- **予習シート**：`data/yoshu/<No>.json` から `/yoshu/<No>/` を作る。JSON は `../夜更文化部/運営/予習シート/作る.py <会のフォルダ>/予習シート.md` が書き出す（同時に A4 の印刷用 PDF も）。JSON がある会は、会の一覧のカードに「予習シートを読む」が出る
- **開催レポート**：`data/reports/<No>.json`（ひな形は `_template.json`）を作って `published: true` にすると `/reports/<No>/` ができ、「これまでの会」のカードに「開催レポート」が出る。写真は `site/assets/reports/`、参加者の顔・名前は載せない
- **カレンダーに追加**：これからの会のカードに Google カレンダーのリンク。終わりの時刻は `events.json` の `end`（なければ開始の2時間後）
- **検索向けの印**：トップと会の一覧に schema.org の Event（JSON-LD）を入れている
- **共有画像（OGP）**：`site/assets/ogp.jpg`（1200×630）。作り直すときは `tools/ogp.html` を Chrome で 1200×630 に撮る
- `site/` を `_site/` に写し、ページの中の `<!--@名前-->` を `build.py` が置き換える（`head`・`bar`・`foot` は `site/_parts/` の部品、`next1`・`next3`・`upcoming`・`past`・`journal3`・`journal`・`stats` などは中身）
- 共通の見た目は `site/assets/site.css`。色はブランドカラー（濃藍・生成り・月光・夜霧・灰藍）

## 窓（/widget/）の表示の切り替え（URL の後ろに付ける）
| 付けるもの | 表示 |
|---|---|
| `?part=next` | 次の会（最大3件。始まった会は自動で消える） |
| `?part=journal` | note「美術館制覇記」の最新3本 |
| `?part=stats` | 開いた会の回数・記録した館の数（`stats_min` 回以上になったら表示） |
| `?part=all` | 全部（既定） |
| `&bg=kinari` / `&bg=none` | 生成りの地／透明の地（既定は濃藍） |

## 会を足すとき（event-launch スキルが行う）
`data/events.json` に1件足して push するだけです。

| 項目 | 例 |
|---|---|
| `id` | `2026-11-20_tobikan100`（バナーの `イベント.json` と同じ） |
| `no` | `01`（同じ日の連続企画は `06-1` のように枝番。回数は1回と数える） |
| `date` / `start` | `2026-11-20` / `19:00` |
| `title` | 改行位置は「／」（バナーと同じ） |
| `place` / `genre` / `price` | `東京都美術館（上野）` / `美術館` / `500`（Peatix の金額） |
| `price_tunagate`（なくてよい） | つなげーとの申込欄の金額。書かなければ `price`＋`config.json` の `tunagate_fee` で計算し、`price` と違えば「参加費 500円（つなげーとは 1,000円）」と並べて出す |
| `peatix` / `tunagate` | 公開ページの URL |
| `published` | 両サイトで公開したら `true`（下書きの間は `false` で表示しない） |
| `canceled` | 中止・見送りにしたら `true`（表示も回数の数えからも外れる） |

終わった会は消さずに残します（開催回数に数えるため）。

## 設定（config.json）
- `note_rss`：note のマガジンの RSS の URL（マガジンのトップの RSS アイコンから取る）。空なら記録の枠は出ない
- `note_url`：マガジンの URL（「記録をすべて note で読む」のリンク先）
- `max_events` / `max_articles` / `stats_min`：表示件数と、数字を出し始める回数
- `tunagate_fee`：つなげーとで参加者に足される利用料（2026-11-17 時点 500円）。チケット500円なら申込欄は 1,000円になる

## 手元で見る
```bash
python3 build.py
python3 -m http.server 8765
```
http://localhost:8765/_site/ でHP、http://localhost:8765/dev/test.html で窓を見る（`python3 build.py --today 2026-12-20` で日付を変えて試せる）。

## 夜更けの地図（site/map/、2026-11-18〜）
参加者が、行った美術館・博物館の記録と口コミを地図に残すページ。公開先は https://yofukashi-bunkabu.com/map/
- 地図は OpenStreetMap（Leaflet）。館の一覧は `site/map/venues.json`（イベント候補ダッシュボードの `venues` から、名前・種類・地域・緯度経度・公式URLだけを書き出したもの）
- ログインと保存は Firebase（Google ログイン＋Firestore）。準備の手順は `FIREBASE.md`、守りは `firestore.rules`
- `site/map/firebase-config.js` が空のあいだは試し表示（ログインはまねだけ、記録はその端末の中だけ）
- 口コミは「自分だけ」が既定。「みんなに公開」にしたものは、ログインしていない人も読める（2026-11-18 秋輝の決定）。名前・メールは保存しない（`site/map/privacy.html`）
