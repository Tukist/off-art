# -*- coding: utf-8 -*-
"""
OFF 站点生成器（docs/）
- index.html       画廊主页（平滑滚动分区 + 资料库入口）
- lore.html        设定文本页（分类卡片 + 折叠全文）
- interviews.html  访谈页（卡片 + 折叠全文）
生成：python scripts/build_gallery.py（幂等，重跑覆盖）
"""
import os
import re
import shutil
import random
from html import escape

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE, "docs")
THUMB_DIR = os.path.join(DOCS, "img", "thumbs")
FULL_DIR = os.path.join(DOCS, "img", "full")
WIKI_DIR = os.path.join(BASE, "wiki")
INTV_DIR = os.path.join(BASE, "interviews")
THUMB_W = 420
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")

# ---------------- 共享 CSS / 页头页脚 ----------------

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior:smooth; }
:root { --ink:#e8e6e1; --bg:#0d0d0f; --dim:#9a978e; --line:#2a2a30; --card:#151519; --accent:#f2f2f2; }
body { background:var(--bg); color:var(--ink); font-family:'Courier New',monospace; line-height:1.7; }
a { color:var(--ink); }
.topbar { position:sticky; top:0; z-index:50; background:rgba(13,13,15,.92); backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line); }
.topbar nav { max-width:1200px; margin:0 auto; display:flex; flex-wrap:wrap; gap:4px 22px;
  padding:14px 20px; align-items:center; font-size:.82rem; letter-spacing:.1em; }
.topbar nav a { color:var(--dim); text-decoration:none; white-space:nowrap; }
.topbar nav a:hover { color:var(--ink); }
.topbar .brand { color:var(--ink); font-weight:bold; letter-spacing:.25em; margin-right:8px; }
header.hero { padding:72px 20px 48px; text-align:center; border-bottom:1px solid var(--line); }
header.hero h1 { font-size:2.4rem; letter-spacing:.4em; text-transform:uppercase; }
header.hero p.tagline { color:var(--dim); margin-top:16px; max-width:640px; margin-left:auto; margin-right:auto; font-size:.95rem; }
header.sub { padding:48px 20px 28px; text-align:center; border-bottom:1px solid var(--line); }
header.sub h1 { font-size:1.6rem; letter-spacing:.3em; text-transform:uppercase; }
header.sub p { color:var(--dim); margin-top:10px; font-size:.9rem; }
main { max-width:1200px; margin:0 auto; padding:16px 20px 40px; }
section { scroll-margin-top:64px; }
.group { margin:52px 0; }
.group h2 { font-size:1.25rem; letter-spacing:.2em; border-left:4px solid var(--ink); padding-left:12px; }
.group .count { color:var(--dim); font-size:.8rem; margin-left:10px; letter-spacing:.1em; }
.group .intro { color:var(--dim); font-size:.9rem; margin:12px 0 20px 16px; max-width:780px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:10px; }
.card-img { display:block; background:var(--line); overflow:hidden; aspect-ratio:1/1; }
.card-img img { width:100%; height:100%; object-fit:cover; display:block; filter:grayscale(.18);
  transition:transform .25s, filter .25s; }
.card-img:hover img { transform:scale(1.05); filter:grayscale(0); }
.cardlist { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
.lcard { background:var(--card); border:1px solid var(--line); transition:border-color .2s; }
.lcard:hover { border-color:var(--dim); }
.lcard summary { list-style:none; cursor:pointer; padding:18px 20px; }
.lcard summary::-webkit-details-marker { display:none; }
.lcard summary h3 { font-size:1rem; letter-spacing:.08em; }
.lcard summary .meta { color:var(--dim); font-size:.78rem; margin-top:6px; }
.lcard summary .tag { display:inline-block; border:1px solid var(--dim); color:var(--dim);
  font-size:.68rem; padding:1px 8px; letter-spacing:.12em; margin-right:8px; }
.lcard .body { border-top:1px solid var(--line); padding:16px 20px 20px; color:var(--dim); font-size:.88rem; }
.lcard .body h2, .lcard .body h3 { color:var(--ink); margin:14px 0 6px; font-size:1rem; }
.lcard .body h1 { color:var(--ink); font-size:1.1rem; margin:14px 0 6px; }
.lcard .body p { margin:8px 0; }
.lcard .body ul { margin:8px 0 8px 22px; }
.lcard .body table { border-collapse:collapse; margin:10px 0; width:100%; font-size:.8rem; }
.lcard .body th, .lcard .body td { border:1px solid var(--line); padding:4px 10px; text-align:left; }
.lcard .body code { background:var(--line); padding:1px 5px; font-size:.8rem; }
.lcard .body pre { background:#0a0a0c; border:1px solid var(--line); padding:12px; overflow-x:auto; font-size:.78rem; margin:10px 0; }
.lcard .body a { color:var(--ink); text-decoration:underline; text-underline-offset:3px; }
.entry { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; margin-top:8px; }
.entry a { display:block; border:1px solid var(--line); background:var(--card); padding:28px 24px;
  text-decoration:none; transition:border-color .2s, transform .2s; }
.entry a:hover { border-color:var(--ink); transform:translateY(-2px); }
.entry h2 { font-size:1.15rem; letter-spacing:.2em; }
.entry p { color:var(--dim); font-size:.85rem; margin-top:10px; }
.entry .n { font-size:2.2rem; color:var(--dim); letter-spacing:.1em; margin-bottom:8px; }
footer { border-top:1px solid var(--line); margin-top:80px; padding:36px 20px 60px;
  text-align:center; color:var(--dim); font-size:.78rem; line-height:2.1; }
footer code { background:var(--line); padding:1px 6px; }
#lightbox { position:fixed; inset:0; background:rgba(0,0,0,.93); display:none; align-items:center;
  justify-content:center; z-index:99; cursor:zoom-out; }
#lightbox img { max-width:92vw; max-height:86vh; }
#lightbox .cap { position:fixed; bottom:22px; left:0; right:0; text-align:center; color:var(--dim); font-size:.78rem; }
@media (max-width:640px){ header.hero h1{ font-size:1.5rem; letter-spacing:.25em; } .grid{ grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); } }
"""

FOOTER = """
<footer>
<p>《OFF》© Mortis Ghost / Unproductive Fun Time · 音乐：Alias Conrad Coldwood · 实体版：Fangamer</p>
<p>本站仅供个人研究收藏，图片与文字版权归原作者所有，禁止商用与二次发布。</p>
<p>资料源：<a href="https://offtherpg.com">offtherpg.com</a> · <a href="https://www.fangamer.com/collections/off">Fangamer</a> ·
<a href="https://mortisghost.tumblr.com">Mortis Ghost</a> · <a href="https://off.fandom.com">OFF Wiki</a></p>
</footer>
"""

NAV_LINKS = [
    ("官方宣传", "index.html#g0"), ("概念图", "index.html#g1"), ("角色", "index.html#g2"),
    ("区域", "index.html#g3"), ("封面标志", "index.html#g4"), ("粉丝档案", "index.html#g5"),
    ("周边收藏", "index.html#g6"), ("设定文本", "lore.html"), ("访谈", "interviews.html"),
]


def topbar(brand_link="index.html", extra_links=None):
    links = list(NAV_LINKS)
    if extra_links:
        links = extra_links + links
    items = [f'<a class="brand" href="{brand_link}">OFF</a>']
    for name, href in links:
        items.append(f'<a href="{href}">{name}</a>')
    return f'<div class="topbar"><nav>{"".join(items)}</nav></div>'


def page(hero, main_html, brand_link="index.html", extra_links=None):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{hero["title"]}</title>
<style>{CSS}</style>
</head>
<body>
{topbar(brand_link, extra_links)}
{hero["html"]}
<main>
{main_html}
</main>
{FOOTER}
{hero["script"] or ""}
</body>
</html>"""


# ---------------- 图片处理 ----------------

def list_images(folder):
    out = []
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if f.startswith("_"):
                continue
            if f.lower().endswith(IMG_EXT):
                out.append(os.path.join(folder, f))
    return out


GLOBAL_IDX = 0
GROUPS = []


def thumb_and_copy(src):
    global GLOBAL_IDX
    idx = GLOBAL_IDX
    GLOBAL_IDX += 1
    ext = os.path.splitext(src)[1].lower()
    stem = f"g{idx:04d}"
    full_rel = os.path.join("img", "full", stem + ext).replace("\\", "/")
    thumb_rel = os.path.join("img", "thumbs", stem + ".jpg").replace("\\", "/")
    shutil.copy2(src, os.path.join(FULL_DIR, stem + ext))
    try:
        im = Image.open(src)
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            thumb_rel = os.path.join("img", "thumbs", stem + ".png").replace("\\", "/")
            im.thumbnail((THUMB_W, THUMB_W))
            im.save(os.path.join(THUMB_DIR, stem + ".png"), "PNG", optimize=True)
        else:
            im = im.convert("RGB")
            im.thumbnail((THUMB_W, THUMB_W))
            im.save(os.path.join(THUMB_DIR, stem + ".jpg"), "JPEG", quality=78, optimize=True)
    except Exception as e:
        print(f"  [thumb fail] {src}: {e}")
        shutil.copy2(src, os.path.join(THUMB_DIR, stem + ".jpg"))
    return thumb_rel, full_rel


def add_group(title, intro, paths, max_n=None, seed=1):
    if max_n and len(paths) > max_n:
        random.Random(seed).shuffle(paths)
        paths = paths[:max_n]
    items = []
    for p in paths:
        t, f = thumb_and_copy(p)
        items.append((t, f, os.path.basename(p)))
    GROUPS.append({"title": title, "intro": intro, "items": items})


# ---------------- 画廊选图 ----------------

WIKI_KW = {
    "角色": (["batter", "judge", "zacharie", "dedan", "japhet", "eloha", "sugar", "elsen",
              "spectre", "enoch", "queen", "vader", "almighty", "player"], 40),
    "区域": (["zone", "purified", "room", "nothingness"], 18),
    "封面标志": (["logo", "cover", "teaser", "remake", "album", "artwork", "visual", "^off"], 15),
}


def pick_wiki():
    pool = list_images(os.path.join(BASE, "art", "wiki"))
    used = set()
    result = []
    for cat, (kws, limit) in WIKI_KW.items():
        chosen = []
        for p in pool:
            if p in used:
                continue
            if any(re.search(k, os.path.basename(p), re.I) for k in kws):
                used.add(p)
                chosen.append(p)
        random.Random(42).shuffle(chosen)
        result.append((cat, chosen[:limit]))
    return result


def pick_fan():
    pool = list_images(os.path.join(BASE, "art", "fan"))
    by_post = {}
    for p in pool:
        m = re.match(r"post_(\d+)_", os.path.basename(p))
        by_post.setdefault(m.group(1) if m else "x", []).append(p)
    firsts = [v[0] for v in by_post.values()]
    random.Random(7).shuffle(firsts)
    return firsts[:30]


# ---------------- Markdown → HTML（简易） ----------------

def md_inline(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  r'<a href="\1" target="_blank" rel="noopener">\1</a>', text)
    return text


def md_to_html(md_text):
    lines = md_text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            j, code = i + 1, []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code.append(lines[j]); j += 1
            out.append("<pre><code>" + escape("\n".join(code)) + "</code></pre>")
            i = j + 1
        elif re.match(r"^(#{1,4})\s+", line):
            lvl = min(len(re.match(r"^(#{1,4})", line).group(1)) + 1, 4)
            out.append(f"<h{lvl}>{md_inline(escape(line.split(' ', 1)[1]))}</h{lvl}>")
            i += 1
        elif re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append("<li>" + md_inline(escape(re.sub(r"^\s*[-*]\s+", "", lines[i]))) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
        elif "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|", lines[i + 1]):
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i]:
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(escape(c))}</th>" for c in header)
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{md_inline(escape(c))}</td>" for c in row) + "</tr>"
                           for row in rows) + "</tbody></table>")
        elif not line.strip():
            i += 1
        else:
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4})\s", lines[i]) \
                    and not re.match(r"^\s*[-*]\s+", lines[i]) and "```" not in lines[i] \
                    and not ("|" in lines[i] and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|", lines[i + 1])):
                para.append(lines[i].strip()); i += 1
            out.append("<p>" + md_inline(escape(" ".join(para))) + "</p>")
    return "\n".join(out)


# ---------------- 设定文本页 ----------------

LORE_GROUPS = [
    ("角色", ["The_Batter", "The_Judge", "Zacharie", "The_Player", "Dedan", "Japhet",
              "Vader_Eloha", "Sugar", "Spectres", "Elsen", "Enoch", "The_Queen"]),
    ("区域", ["Zones", "Zone_0", "Zone_1", "Zone_2", "Zone_3", "Purified_Zones", "The_Room", "The_Nothingness"]),
    ("世界观", ["OFF", "Add-Ons", "Mortis_Ghost"]),
]


def display_name(fname):
    return fname.replace("_", " ").replace(".md", "")


def lore_excerpt(md_text):
    skip = False
    cleaned = []
    for ln in md_text.split("\n"):
        low = ln.strip().lower()
        if low.startswith("contents"):
            skip = True
        if skip and low == "references":
            skip = False
        if skip or "spoiler warning" in low or not ln.strip():
            continue
        cleaned.append(ln)
    text = re.sub(r"\s+", " ", " ".join(cleaned)).strip()
    text = re.sub(r"^#+\s*", "", text)
    return text[:200] + ("…" if len(text) > 200 else "")


def build_lore():
    sections = []
    for cat, names in LORE_GROUPS:
        cards = []
        for name in names:
            path = os.path.join(WIKI_DIR, name + ".md")
            if not os.path.exists(path):
                continue
            raw = open(path, encoding="utf-8").read()
            body = re.sub(r"^#\s+.+", "", raw, count=1, flags=re.M).strip()
            cards.append(
                f'<details class="lcard"><summary><span class="tag">{escape(cat)}</span>'
                f'<h3>{escape(display_name(name))}</h3>'
                f'<div class="meta">{escape(lore_excerpt(raw))}</div></summary>'
                f'<div class="body">{md_to_html(body)}</div></details>')
        if cards:
            sections.append(f'<section class="group" id="{escape(cat)}">'
                            f'<h2>{escape(cat)}<span class="count">{len(cards)} 篇</span></h2>'
                            f'<div class="cardlist">{"".join(cards)}</div></section>')
    main = "".join(sections)
    hero = {"title": "OFF 设定文本 · Lore",
            "html": f'<header class="sub"><h1>设定文本 / Lore</h1>'
                    f'<p>来自 OFF Wiki（Fandom）的 23 页世界观设定 · 点击卡片展开全文</p></header>',
            "script": ""}
    extra = [(c, f"lore.html#{c}") for c, _ in LORE_GROUPS]
    return page(hero, main, brand_link="index.html", extra_links=extra)


# ---------------- 访谈页 ----------------

def build_interviews():
    cards = []
    for path in sorted(os.listdir(INTV_DIR)):
        if not path.endswith(".md") or path.startswith("_"):
            continue
        raw = open(os.path.join(INTV_DIR, path), encoding="utf-8").read()
        title = re.search(r"^# (.+)$", raw, re.M)
        title = title.group(1).strip() if title else display_name(path)
        src = re.search(r"^-\s*来源:\s*(.+)$", raw, re.M)
        date = re.search(r"^-\s*日期:\s*(.+)$", raw, re.M)
        key = re.search(r"## 中文要点摘要\s*\n(.*?)(?=\n## )", raw, re.S)
        points = re.findall(r"^\s*-\s+(.+)$", key.group(1), re.M) if key else []
        full = re.search(r"## 全文\s*\n(.*)$", raw, re.S)
        body = md_to_html(full.group(1)) if full else "<p>（全文缺失）</p>"
        point_html = "".join(f"<li>{md_inline(escape(p))}</li>" for p in points) or "<li>（无摘要）</li>"
        cards.append(
            f'<details class="lcard"><summary><h3>{escape(title)}</h3>'
            f'<div class="meta">{escape(date.group(1).strip()) if date else ""} · '
            f'<a href="{escape(src.group(1).strip()) if src else "#"}" target="_blank" rel="noopener">来源</a></div>'
            f'<ul>{"".join(point_html)}</ul></summary>'
            f'<div class="body">{body}</div></details>')
    main = f'<section class="group" id="interviews"><div class="cardlist">{"".join(cards)}</div></section>'
    hero = {"title": "OFF 作者访谈 · Interviews",
            "html": f'<header class="sub"><h1>作者访谈 / Interviews</h1>'
                    f'<p>7 篇访谈全文 · Mortis Ghost、Toby Fox、Morusque、Quinn K.、Nightmargin 与 15 周年直播整理</p></header>',
            "script": ""}
    return page(hero, main, brand_link="index.html")


# ---------------- 主页 ----------------

def build_index():
    for g in GROUPS:
        cards = "".join(
            f'<a class="card-img" href="{escape(f)}" data-caption="{escape(name)}">'
            f'<img loading="lazy" src="{escape(t)}" alt="{escape(name)}"></a>'
            for t, f, name in g["items"])
        g["html"] = (f'<section class="group" id="g{GROUPS.index(g)}">'
                     f'<h2>{escape(g["title"])}<span class="count">{len(g["items"])} 张</span></h2>'
                     f'<p class="intro">{escape(g["intro"])}</p>'
                     f'<div class="grid">{cards}</div></section>')

    gallery = "".join(g["html"] for g in GROUPS)
    entries = (
        '<div class="entry">'
        '<a href="lore.html"><div class="n">23</div><h2>设定文本 / Lore</h2>'
        '<p>角色、区域与世界观的完整设定：Batter 的净化使命、四区域守护者、Sugar 与 The Room…</p></a>'
        '<a href="interviews.html"><div class="n">07</div><h2>作者访谈 / Interviews</h2>'
        '<p>Mortis Ghost、Toby Fox、Morusque 等人的 7 篇访谈全文，含 15 周年直播完整文字稿。</p></a>'
        '</div>')
    main = gallery + '<section class="group"><h2>资料库 / Archive</h2>' \
        '<p class="intro">设定文本与作者访谈单独成页，保持浏览的结构感。</p>' + entries + '</section>'
    hero = {"title": "OFF 美术画廊 · OFF Art Gallery",
            "html": ('<header class="hero"><h1>OFF</h1>'
                     '<p class="tagline">《OFF》(2008) · Mortis Ghost 美术设定画廊<br>'
                     'The Batter 净化之旅的设定图、概念草稿、官方美术与周边档案</p></header>'),
            "script": """
<script>
const lb=document.getElementById('lightbox'),img=document.getElementById('lb-img'),cap=document.getElementById('lb-cap');
document.querySelectorAll('.card-img').forEach(a=>{a.addEventListener('click',e=>{e.preventDefault();
img.src=a.href;cap.textContent=a.dataset.caption+' · '+a.href.split('/').pop();lb.style.display='flex';});});
lb.addEventListener('click',()=>lb.style.display='none');
document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.style.display='none';});
</script>
<div id="lightbox"><img id="lb-img" alt=""><div class="cap" id="lb-cap"></div></div>
"""}
    return page(hero, main, brand_link="index.html")


# ---------------- 主流程 ----------------

def build():
    os.makedirs(THUMB_DIR, exist_ok=True)
    os.makedirs(FULL_DIR, exist_ok=True)
    # 重新生成缩略图/原图时先清空，避免残留旧序号
    for d in (FULL_DIR, THUMB_DIR):
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    add_group("官方宣传",
              "2025 年重制版官方截图与宣传美术（offtherpg.com）：The Batter 的净化之旅——金属农场、游乐场、糖果工厂。",
              list_images(os.path.join(BASE, "art", "official")), max_n=30, seed=1)
    mortis = [p for p in list_images(os.path.join(BASE, "art", "official"))
              if "mortis" in os.path.basename(p).lower()]
    add_group("作者概念图",
              "Mortis Ghost 本人博客（Tumblr）发布的 OFF 概念图与涂鸦，含重制版公告时期的创作。",
              mortis)
    for cat, paths in pick_wiki():
        intro = {"角色": "核心角色：The Batter（棒球手）、The Judge（猫）、Zacharie 商人、四区域守护者 Dedan / Japhet / Vader Eloha、隐藏 BOSS Sugar 等。",
                 "区域": "世界观区域：Zone 0-3、净化之地、The Room 与虚无等概念图与截图。",
                 "封面标志": "封面、Logo 与 2024-2025 重制版宣传素材。"}[cat]
        add_group(f"Wiki · {cat}", intro, paths)
    add_group("粉丝档案精选",
              "粉丝整理的官方艺术档案（Tumblr: off-art-archive）抽样：概念草图、笔记本扫描与怪物设计。",
              pick_fan())
    add_group("周边与收藏版",
              "Fangamer 发行：OFF 收藏版「Bad Human Edition」内容物（摇头公仔、前传漫画《OF》、星座卡）与官方周边。",
              list_images(os.path.join(BASE, "art", "merch")), max_n=25, seed=3)

    open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(build_index())
    open(os.path.join(DOCS, "lore.html"), "w", encoding="utf-8").write(build_lore())
    open(os.path.join(DOCS, "interviews.html"), "w", encoding="utf-8").write(build_interviews())
    print(f"生成完成：index.html / lore.html / interviews.html，共 {sum(len(g['items']) for g in GROUPS)} 张图")


if __name__ == "__main__":
    build()
