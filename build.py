"""夜更文化部の HP（GitHub Pages）を作る。

data/events.json（告知のときに足す）と note の RSS から、HP のページと _site/data.json を書き出す。
GitHub Actions が毎朝6時（日本時間）と push のたびにこれを動かし、_site を GitHub Pages に出す。

    python3 build.py            # _site/ に書き出す
    python3 build.py --today 2026-11-21   # 日付を指定して試す

ページの中の <!--@名前--> は、ここで中身に置き換える（共通のヘッダー・フッター、次の会、会の一覧、記事）。
site/_parts/ は部品なので _site には出さない。
"""
import argparse
import html
import json
import re
import shutil
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
JST = timezone(timedelta(hours=9))
UA = "yofukashi-bunkabu-site/1.0 (+https://github.com/yofukashi-bunkabu)"
WD = "月火水木金土日"
WD_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
esc = lambda s: html.escape(str(s or ""), quote=True)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        return r.read()


def is_https(url, host):
    return isinstance(url, str) and re.match(rf"^https://([a-z0-9-]+\.)*{re.escape(host)}/", url) is not None


def tunagate_price(e, fee):
    """つなげーとで申し込んだときに払う額。つなげーとは利用料（fee）が足されるので Peatix と金額が違う。
    events.json に price_tunagate があればそれを使う。"""
    if "price_tunagate" in e:
        return e["price_tunagate"]
    price = e.get("price")
    if isinstance(price, int) and isinstance(fee, int) and is_https(e.get("tunagate"), "tunagate.com"):
        return price + fee
    return None


def load_events(today, fee=None):
    """公開中の会を、これからの会（upcoming）と終わった会（past）に分ける。中止は除く。"""
    events = json.loads((ROOT / "data/events.json").read_text(encoding="utf-8"))
    upcoming, past, held = [], [], set()
    for e in events:
        if not e.get("published") or e.get("canceled"):
            continue
        row = {
            "no": e["no"],
            "date": e["date"],
            "start": e.get("start", ""),
            "end": e.get("end", ""),
            "title": e["title"],
            "place": e.get("place", ""),
            "genre": e.get("genre", ""),
            "price": e.get("price"),
            "price_tunagate": tunagate_price(e, fee),
            "peatix": e["peatix"] if is_https(e.get("peatix"), "peatix.com") else "",
            "tunagate": e["tunagate"] if is_https(e.get("tunagate"), "tunagate.com") else "",
        }
        if e["date"] >= today:
            upcoming.append(row)
        else:
            past.append(row)
            # 06-1・06-2・06-3 のような同じ日の連続企画は1回と数える
            held.add(str(e["no"]).split("-")[0])
    upcoming.sort(key=lambda e: (e["date"], e["start"]))
    past.sort(key=lambda e: (e["date"], e["start"]), reverse=True)
    return upcoming, past, len(held)


def load_journal(cfg):
    """note のマガジンの RSS から記事を取る。"""
    if not cfg.get("note_rss"):
        return []
    root = ET.fromstring(fetch(cfg["note_rss"]))
    items = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        if not is_https(link, "note.com"):
            continue
        d = ""
        if it.findtext("pubDate"):
            d = parsedate_to_datetime(it.findtext("pubDate")).astimezone(JST).strftime("%Y-%m-%d")
        items.append({"title": (it.findtext("title") or "").strip(), "link": link, "date": d})
    return items


def previous_journal(cfg):
    """RSS が読めなかったとき、いま公開中の data.json から記事一覧を引き継ぐ。"""
    try:
        return json.loads(fetch(cfg["site_url"] + "data.json")).get("journal", {}).get("all", [])
    except Exception:
        return []


# ---------- ページの部品 ----------

def jdate(s):
    d = date.fromisoformat(s)
    return d, f"{d.month}月{d.day}日（{WD[d.weekday()]}）"


def title1(t):
    return esc(t).replace("／", "")


def title_br(t):
    return esc(t).replace("／", "<br>")


def price_text(e):
    p, t = e.get("price"), e.get("price_tunagate")
    if not isinstance(p, int):
        return ""
    s = f"参加費 {p:,}円"
    if isinstance(t, int) and t != p:
        s += f"（つなげーとは {t:,}円）"
    return s


def ev_buttons(e, cfg):
    b = []
    if e["peatix"]:
        b.append(f'<a class="btn fill" href="{esc(e["peatix"])}">Peatix で予約</a>')
    if e["tunagate"]:
        b.append(f'<a class="btn" href="{esc(e["tunagate"])}">つなげーと で予約</a>')
    if not b:
        b.append(f'<a class="btn fill" href="{esc(cfg["peatix_group"])}">予約ページを見る</a>')
    return "".join(b)


def next1_html(up, cfg):
    if not up:
        return ('<div class="next1 empty"><p>次の会は準備中です。Peatix のグループをフォローすると、お知らせが届きます。</p>'
                f'<a class="btn fill" href="{esc(cfg["peatix_group"])}">Peatix のグループを見る</a></div>')
    e = up[0]
    d, _ = jdate(e["date"])
    return f'''<div class="next1">
  <div class="d">{d.month}.{d.day:02d}<small>{WD_EN[d.weekday()]} {esc(e["start"])}</small></div>
  <div><span class="lab">NEXT</span><div class="t">{title1(e["title"])}</div><div class="pl">{esc(e["place"])}</div></div>
  <a class="btn fill" href="{esc(e["peatix"] or cfg["peatix_group"])}">予約ページを見る</a>
</div>'''


def gcal_url(e):
    """Google カレンダーに予定を入れるリンク。終わりの時刻は events.json の end（なければ開始の2時間後）"""
    if not e.get("start"):
        return ""
    st = datetime.fromisoformat(f'{e["date"]}T{e["start"]}')
    en = datetime.fromisoformat(f'{e["date"]}T{e["end"]}') if e.get("end") else st + timedelta(hours=2)
    f = lambda t: t.strftime("%Y%m%dT%H%M%S")
    details = "夜更文化部の会です。予約・くわしくは " + (e.get("peatix") or e.get("tunagate") or "")
    q = urllib.parse.urlencode({"action": "TEMPLATE", "text": f'夜更文化部 No.{e["no"]} {e["title"].replace("／", "")}',
                                "dates": f"{f(st)}/{f(en)}", "ctz": "Asia/Tokyo", "location": e.get("place", ""), "details": details})
    return "https://calendar.google.com/calendar/render?" + q


def ev_links(e, base, past):
    """会のカードの下に付ける小さなリンク：予習シート・レポート・カレンダー"""
    out = []
    no = str(e["no"])
    if (ROOT / "data/yoshu" / f"{no}.json").exists():
        out.append(f'<a href="{base}yoshu/{esc(no)}/">予習シートを読む</a>')
    if past and (ROOT / "data/reports" / f"{no}.json").exists() and json.loads((ROOT / "data/reports" / f"{no}.json").read_text(encoding="utf-8")).get("published"):
        out.append(f'<a href="{base}reports/{esc(no)}/">開催レポート</a>')
    if not past and gcal_url(e):
        out.append(f'<a href="{esc(gcal_url(e))}" target="_blank" rel="noopener">カレンダーに追加</a>')
    return f'<p class="ev-links">{"".join(out)}</p>' if out else ""


def ev_card(e, cfg, past=False, base="{{base}}"):
    d, jd = jdate(e["date"])
    no = f"No.{esc(e['no'])}"
    meta = " ・ ".join(x for x in [esc(e["genre"]), price_text(e) if not past else ""] if x)
    btns = ev_links(e, base, past) + ("" if past else f'<div class="btns">{ev_buttons(e, cfg)}</div>')
    return f'''<article class="ev{' past' if past else ''}">
  <div class="ev-d"><b>{d.month}.{d.day:02d}</b><span>{WD[d.weekday()]}{(" " + esc(e["start"])) if e["start"] else ""}</span></div>
  <div class="ev-b"><span class="lab">{no}</span><h3>{title_br(e["title"])}</h3><p class="pl">{esc(e["place"])}</p>{f'<p class="meta">{meta}</p>' if meta else ""}{btns}</div>
</article>'''


def list_html(rows, cfg, past=False, limit=None, empty=""):
    rows = rows[:limit] if limit else rows
    if not rows:
        return f'<p class="empty">{empty}</p>'
    return '<div class="evs">' + "".join(ev_card(e, cfg, past) for e in rows) + "</div>"


def journal_html(articles, cfg, limit=None):
    rows = articles[:limit] if limit else articles
    if not rows:
        return ('<p class="empty">記事は準備中です。最初の記事を note に書いています。</p>')
    out = []
    for a in rows:
        out.append(f'<a class="art" href="{esc(a["link"])}"><i>{esc(a["date"].replace("-", "."))}</i><b>{esc(a["title"])}</b></a>')
    return '<div class="arts">' + "".join(out) + "</div>"


def stats_html(held, venues, cfg):
    if held < cfg["stats_min"]:
        return ""
    return (f'<div class="stats"><div class="stat"><b>{held}</b><span>これまでの開催</span></div>'
            f'<div class="stat"><b>{venues}</b><span>記録した館</span></div></div>')


def jsonld(upcoming, cfg):
    """検索エンジン向けの「イベント」の印（schema.org/Event）。これからの会だけ"""
    items = []
    for e in upcoming:
        st = f'{e["date"]}T{e["start"] or "10:00"}:00+09:00'
        ev = {"@type": "Event", "name": f'夜更文化部 No.{e["no"]} {e["title"].replace("／", "")}', "startDate": st,
              "eventStatus": "https://schema.org/EventScheduled",
              "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
              "location": {"@type": "Place", "name": e["place"], "address": {"@type": "PostalAddress", "addressRegion": "東京都", "addressCountry": "JP"}},
              "organizer": {"@type": "Organization", "name": "夜更文化部", "url": cfg["site_url"]},
              "image": cfg["site_url"] + "assets/ogp.jpg",
              "description": "社会人のための鑑賞の部活。予習シートを1枚持って行き、それぞれのペースで観て、観たあとに少しだけ感想を話します。"}
        if e.get("end"):
            ev["endDate"] = f'{e["date"]}T{e["end"]}:00+09:00'
        if isinstance(e.get("price"), int) and e.get("peatix"):
            ev["offers"] = {"@type": "Offer", "price": e["price"], "priceCurrency": "JPY", "url": e["peatix"], "availability": "https://schema.org/InStock"}
        items.append(ev)
    if not items:
        return ""
    data = {"@context": "https://schema.org", "@graph": items}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def br(t):
    return esc(t).replace("／", "<br>")


def render_yoshu(d, parts):
    """data/yoshu/<no>.json から予習シートのページ（/yoshu/<no>/）を作る"""
    dt = date.fromisoformat(d["date"])
    hl = "".join(
        f'<article><span class="no">{i + 1:02d}</span><span class="big">{esc(h["big"])}'
        + (f'<span style="font-size:.6em">{esc(h["unit"])}</span>' if h.get("unit") else "")
        + f'<small>{esc(h.get("cap", ""))}</small></span><h3>{esc(h["title"])}</h3><p>{esc(h["text"])}</p></article>'
        for i, h in enumerate(d["highlights"]))
    nums = "".join(
        f'<div class="num"><b>{esc(n["big"])}' + (f'<span class="jp">{esc(n["jp"])}</span>' if n.get("jp") else "")
        + f'</b><span>{esc(n["cap"])}</span></div>' for n in d.get("nums", []))
    bg = "".join(f"<li>{esc(x)}</li>" for x in d["background"])
    memo = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in d["memo"])
    years = "<br>".join(esc(y) for y in d.get("years", [])) or f"{dt.month}.{dt.day:02d}"
    photo = (f'<div class="photo" style="background-image:url(\'../../{esc(d["photo"])}\')" role="img" aria-label="{esc(d["venue"])}の外観"></div>'
             f'<p class="credit">{esc(d.get("photo_credit", ""))}</p>') if d.get("photo") else ""
    head = parts["head"].replace("{{base}}", "../../")
    return f"""<!doctype html>
<html lang="ja">
<head>
{head}
<title>予習シート No.{esc(d["no"])} {esc(d["venue"])}｜夜更文化部</title>
<meta name="description" content="夜更文化部 No.{esc(d["no"])}（{dt.year}年{dt.month}月{dt.day}日）の予習シート。{esc(d["title"].replace("／", ""))}。行きの電車で5分で読めます。">
<meta name="robots" content="noindex">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&display=swap">
<link rel="stylesheet" href="../../assets/yoshu.css">
</head>
<body>
<article class="sheet">
  <div class="strip"><span>YOFUKASHI BUNKABU — No.{esc(d["no"])}</span><span>{dt.year}.{dt.month:02d}.{dt.day:02d} {WD_EN[dt.weekday()][:3]}</span><span>{esc(d["venue"])}</span></div>
  <div class="kicker"><b>予習シート</b><span>READ IN 5 MIN</span></div>
  <div class="top">
    <div class="years"><small>{esc(d.get("venue_en", ""))}</small>{years}</div>
    <img class="logo" src="../../assets/logo_ai.svg" alt="夜更文化部">
  </div>
  <h1>{br(d["title"])}</h1>
  <p class="lead">{esc(d["lead"])}</p>
  {photo}
  <section class="sec">
    <div class="sh"><i>01 — HIGHLIGHTS</i><h2>見どころ3つ</h2></div>
    <div class="hl">{hl}</div>
  </section>
  <section class="sec">
    <div class="sh"><i>02 — BACKGROUND</i><h2>3行でわかる背景</h2></div>
    {f'<div class="nums">{nums}</div>' if nums else ''}
    <ul class="bg">{bg}</ul>
  </section>
  <section class="sec">
    <div class="q"><i>03 — QUESTION｜感想タイムの問い</i><p>{br(d["question"])}</p><small>観たあとの感想の時間に、この問いから話し始めます。</small></div>
  </section>
  <section class="sec">
    <div class="sh"><i>04 — MEMO</i><h2>行く人へのメモ</h2></div>
    <dl class="memo">{memo}</dl>
  </section>
  <footer class="end">
    確かめた日：{esc(d["checked"])}　出典：{esc(d["sources"])}。開館時間などは行く前に公式サイトでお確かめください。{esc(d["venue"])}の公式イベントではありません。
    <div class="sig"><span>YOFUKASHI BUNKABU</span><a href="../../">夜更文化部</a></div>
  </footer>
</article>
</body>
</html>
"""


def render_report(r, parts):
    """data/reports/<no>.json から開催レポート（/reports/<no>/）を作る。published が true のものだけ"""
    dt = date.fromisoformat(r["date"])
    base = "../../"
    talk = "".join(f"<li>{esc(t)}</li>" for t in r.get("talk", []))
    photos = "".join(f'<figure><img src="{base}{esc(p["src"])}" alt="{esc(p.get("alt", ""))}" loading="lazy"><figcaption>{esc(p.get("cap", ""))}</figcaption></figure>' for p in r.get("photos", []))
    links = []
    if (ROOT / "data/yoshu" / f'{r["no"]}.json').exists():
        links.append(f'<a class="btn" href="{base}yoshu/{esc(r["no"])}/">この回の予習シート</a>')
    links.append(f'<a class="btn" href="{base}events/">会の一覧</a>')
    page = f"""<!doctype html>
<html lang="ja">
<head>
{parts["head"]}
<title>開催レポート No.{esc(r["no"])} {esc(r["title"].replace("／", ""))}｜夜更文化部</title>
<meta name="description" content="{esc(r.get("lead", ""))}">
<meta property="og:title" content="開催レポート No.{esc(r["no"])}｜夜更文化部">
<style>
.rep-photos {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); margin: 6px 0 26px; }}
.rep-photos img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: cover; filter: grayscale(.15); }}
.rep-photos figcaption {{ font-family: var(--goth); font-size: 12px; color: var(--haiai); margin-top: 6px; }}
.talk {{ list-style: none; padding: 0; margin: 0 0 24px; }}
.talk li {{ font-size: 16px; line-height: 1.9; padding: 12px 0 12px 22px; border-bottom: 1px dashed #1c233833; position: relative; }}
.talk li::before {{ content: "“"; position: absolute; left: 0; top: 6px; font: 400 28px var(--num); color: #b0902e; }}
</style>
</head>
<body>
{parts["bar"]}
<div class="ph"><div class="wrap"><span class="lab">REPORT — No.{esc(r["no"])}</span><h1>{br(r["title"])}</h1><p>{dt.year}年{dt.month}月{dt.day}日（{WD[dt.weekday()]}）　{esc(r["place"])}</p></div></div>
<section class="sec"><div class="wrap">
  <p style="font-size:16px">{esc(r.get("lead", ""))}</p>
  {f'<div class="rep-photos">{photos}</div>' if photos else ''}
  {f'<div class="head"><h2>感想の時間に出た話</h2><span class="lab">TALK</span></div><ul class="talk">{talk}</ul>' if talk else ''}
  <div class="btns">{"".join(links)}</div>
</div></section>
{parts["foot"]}
</body>
</html>
"""
    return page.replace("{{base}}", base)


def render_pages(ctx):
    parts = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "site/_parts").glob("*.html")}
    for page in OUT.rglob("*.html"):
        s = page.read_text(encoding="utf-8")
        if "<!--@" not in s:
            continue
        depth = len(page.relative_to(OUT).parts) - 1
        base = "../" * depth or "./"

        def sub(m):
            key = m.group(1)
            if key in parts:
                return parts[key].replace("{{base}}", base)
            return ctx.get(key, "")

        s = re.sub(r"<!--@([a-z0-9_]+)-->", sub, s)
        page.write_text(s.replace("{{base}}", base), encoding="utf-8")


def write_domain_files(cfg):
    """公開先の URL（config.json の site_url）を各ページに入れ、CNAME・sitemap.xml・robots.txt を書く。"""
    site = cfg["site_url"].rstrip("/") + "/"
    urls = []
    for page in sorted(OUT.rglob("*.html")):
        s = page.read_text(encoding="utf-8")
        if "{{site}}" in s:
            s = s.replace("{{site}}", site)
            page.write_text(s, encoding="utf-8")
        if 'name="robots" content="noindex"' in s:
            continue
        rel = page.relative_to(OUT).as_posix()
        urls.append(site + (rel[: -len("index.html")] if rel.endswith("index.html") else rel))
    host = urllib.parse.urlparse(site).hostname
    if not host.endswith(".github.io"):
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{esc(u)}</loc></url>" for u in urls]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site}sitemap.xml\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="YYYY-MM-DD（試すとき用）")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    now = datetime.now(JST)
    today = args.today or now.strftime("%Y-%m-%d")

    upcoming, past, held = load_events(today, cfg.get("tunagate_fee"))

    try:
        articles = load_journal(cfg)
        journal_ok = True
    except Exception as err:
        print(f"note の RSS が読めませんでした（前回の内容を使います）: {err}")
        articles, journal_ok = previous_journal(cfg), False

    series = [a for a in articles if cfg["journal_series"] in a["title"]]
    data = {
        "updated": now.isoformat(timespec="minutes"),
        "today": today,
        "links": {k: cfg[k] for k in ("peatix_group", "tunagate_circle", "note_url")},
        # 全件を渡し、始まった会を除いてからページ側で max_events 件に絞る（窓 widget/ 用）
        "next": upcoming,
        "past": past,
        "max_events": cfg["max_events"],
        "journal": {"all": articles, "latest": articles[: cfg["max_articles"]], "fresh": journal_ok},
        "stats": {"held": held, "venues": len(series), "show": held >= cfg["stats_min"]},
    }

    ctx = {
        "next1": next1_html(upcoming, cfg),
        "next3": list_html(upcoming, cfg, limit=cfg["max_events"], empty="次の会は準備中です。Peatix のグループをフォローすると、お知らせが届きます。"),
        "upcoming": list_html(upcoming, cfg, empty="次の会は準備中です。"),
        "past": list_html(past, cfg, past=True, empty="まだありません。"),
        "journal3": journal_html(articles, cfg, cfg["max_articles"]),
        "journal": journal_html(articles, cfg),
        "stats": stats_html(held, len(series), cfg),
        "jsonld": jsonld(upcoming, cfg),
        "count_up": str(len(upcoming)),
        "count_past": str(len(past)),
        "updated": now.strftime("%Y年%-m月%-d日"),
        "note_url": esc(cfg["note_url"]),
        "peatix_group": esc(cfg["peatix_group"]),
        "tunagate_circle": esc(cfg["tunagate_circle"]),
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "site", OUT, ignore=shutil.ignore_patterns("_parts", ".DS_Store"))
    render_pages(ctx)
    parts = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "site/_parts").glob("*.html")}
    for f in sorted((ROOT / "data/yoshu").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out = OUT / "yoshu" / d["no"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_yoshu(d, parts), encoding="utf-8")
    for f in sorted((ROOT / "data/reports").glob("*.json")) if (ROOT / "data/reports").exists() else []:
        r = json.loads(f.read_text(encoding="utf-8"))
        if not r.get("published"):
            continue
        out = OUT / "reports" / r["no"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_report(r, parts), encoding="utf-8")
    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_domain_files(cfg)
    print(f"{today}: 次の会 {len(upcoming)}件／終わった会 {len(past)}件（開催 {held}回）／記事 {len(articles)}本 → {OUT}")


if __name__ == "__main__":
    main()
