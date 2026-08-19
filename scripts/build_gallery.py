# -*- coding: utf-8 -*-
"""
OFF 画廊网站生成器
- 从本地 art/ 各目录精选代表性图片
- Pillow 生成缩略图 + 复制原图到 docs/img/
- 生成 docs/index.html（深色 OFF 风格画廊 + 分组介绍 + lightbox）
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
THUMB_W = 420

IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def list_images(folder):
    out = []
    if not os.path.isdir(folder):
        return out
    for f in sorted(os.listdir(folder)):
        if f.startswith("_"):
            continue
        if f.lower().endswith(IMG_EXT):
            out.append(os.path.join(folder, f))
    return out


# ---------- 精选规则 ----------

def pick_official():
    """官方宣传图：全部（截图/logo/bg/trailer）"""
    return list_images(os.path.join(BASE, "art", "official"))


def pick_merch():
    """周边与收藏版：全部"""
    return list_images(os.path.join(BASE, "art", "merch"))


WIKI_KEYWORDS = {
    "角色": [r"batter", r"judge", r"zacharie", r"dedan", r"japhet", r"eloha",
             r"sugar", r"elsen", r"spectre", r"enoch", r"queen", r"vader",
             r"almighty", r"player"],
    "区域": [r"zone", r"purified", r"room", r"nothingness"],
    "封面与标志": [r"logo", r"cover", r"teaser", r"remake", r"^off", r"album",
                  r"artwork", r"visual"],
}


def pick_wiki():
    """Wiki 图按关键词分组精选，每类限 N 张"""
    pool = list_images(os.path.join(BASE, "art", "wiki"))
    groups = {}
    for cat, kws in WIKI_KEYWORDS.items():
        groups[cat] = []
        for p in pool:
            name = os.path.basename(p)
            if any(re.search(k, name, re.I) for k in kws):
                groups[cat].append(p)
    # 去重（一张图可能命中多个类，归到第一个命中的类）
    used = set()
    result = []
    for cat, kws in WIKI_KEYWORDS.items():
        chosen = []
        for p in pool:
            if p in used:
                continue
            name = os.path.basename(p)
            if any(re.search(k, name, re.I) for k in kws):
                used.add(p)
                chosen.append(p)
        random.Random(42).shuffle(chosen)  # 固定随机种子，结果可复现
        limit = {"角色": 40, "区域": 18, "封面与标志": 15}[cat]
        result.append((cat, chosen[:limit]))
    return result


def pick_fan():
    """粉丝档案：每帖取第一张 + 随机补足，共 ~30 张"""
    pool = list_images(os.path.join(BASE, "art", "fan"))
    if not pool:
        return []
    # 按帖子分组（文件名 post_<id>_<n>）
    by_post = {}
    for p in pool:
        m = re.match(r"post_(\d+)_", os.path.basename(p))
        key = m.group(1) if m else "x"
        by_post.setdefault(key, []).append(p)
    firsts = [v[0] for v in by_post.values()]
    random.Random(7).shuffle(firsts)
    return firsts[:30]


# ---------- 图片处理 ----------

GLOBAL_IDX = 0


def thumb_and_copy(src):
    """生成缩略图 + 复制原图到 docs/img/，返回 (thumb_rel, full_rel)（全局递增序号）"""
    global GLOBAL_IDX
    idx = GLOBAL_IDX
    GLOBAL_IDX += 1
    ext = os.path.splitext(src)[1].lower()
    stem = f"g{idx:04d}"
    full_name = stem + ext
    full_rel = os.path.join("img", "full", full_name).replace("\\", "/")
    thumb_name = stem + ".jpg"
    thumb_rel = os.path.join("img", "thumbs", thumb_name).replace("\\", "/")

    # 复制原图
    shutil.copy2(src, os.path.join(FULL_DIR, full_name))

    # 生成缩略图（GIF 取第一帧；透明 PNG 保留透明转成 PNG 缩略图）
    try:
        im = Image.open(src)
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            thumb_path = os.path.join(THUMB_DIR, stem + ".png")
            thumb_rel = os.path.join("img", "thumbs", stem + ".png").replace("\\", "/")
            im.thumbnail((THUMB_W, THUMB_W))
            im.save(thumb_path, "PNG", optimize=True)
        else:
            im = im.convert("RGB")
            im.thumbnail((THUMB_W, THUMB_W))
            im.save(os.path.join(THUMB_DIR, thumb_name), "JPEG", quality=78, optimize=True)
    except Exception as e:
        print(f"  [thumb fail] {src}: {e}")
        shutil.copy2(src, os.path.join(THUMB_DIR, thumb_name))
    return thumb_rel, full_rel


GROUPS = []


def add_group(title, intro, paths, max_n=None, shuffle_seed=None):
    if max_n and len(paths) > max_n:
        random.Random(shuffle_seed).shuffle(paths)
        paths = paths[:max_n]
    items = []
    for p in paths:
        t, f = thumb_and_copy(p)
        items.append((t, f, os.path.basename(p)))
    GROUPS.append({"title": title, "intro": intro, "items": items})


def build():
    os.makedirs(THUMB_DIR, exist_ok=True)
    os.makedirs(FULL_DIR, exist_ok=True)

    add_group(
        "官方宣传",
        "2025 年重制版官方截图与宣传美术（offtherpg.com）：The Batter 的净化之旅——金属农场、游乐场、糖果工厂。",
        pick_official(),
        max_n=30, shuffle_seed=1,
    )
    add_group(
        "作者概念图",
        "Mortis Ghost 本人博客（Tumblr）发布的 OFF 概念图与涂鸦，含重制版公告时期的创作。",
        list_images(os.path.join(BASE, "art", "official")) and
        [p for p in list_images(os.path.join(BASE, "art", "official")) if "mortis" in os.path.basename(p).lower()],
    )
    for cat, paths in pick_wiki():
        if cat == "角色":
            intro = "核心角色：The Batter（棒球手）、The Judge（猫）、Zacharie 商人、四区域守护者 Dedan / Japhet / Vader Eloha、隐藏 BOSS Sugar 等。"
        elif cat == "区域":
            intro = "世界观区域：Zone 0-3、净化之地、The Room 与虚无等概念图与截图。"
        else:
            intro = "封面、Logo 与 2024-2025 重制版宣传素材。"
        add_group(f"Wiki · {cat}", intro, paths)
    add_group(
        "粉丝档案精选",
        "粉丝整理的官方艺术档案（Tumblr: off-art-archive）抽样：概念草图、笔记本扫描与怪物设计。",
        pick_fan(),
    )
    add_group(
        "周边与收藏版",
        "Fangamer 发行：OFF 收藏版「Bad Human Edition」内容物（摇头公仔、前传漫画《OF》、星座卡）与官方周边。",
        pick_merch(),
        max_n=25, shuffle_seed=3,
    )

    write_html()


def write_html():
    sections = []
    for g in GROUPS:
        cards = []
        for t, f, name in g["items"]:
            cards.append(
                f'<a class="card" href="{escape(f)}" data-caption="{escape(name)}">'
                f'<img loading="lazy" src="{escape(t)}" alt="{escape(name)}"></a>'
            )
        sections.append(
            f'<section class="group" id="g{len(sections)}">'
            f'<h2>{escape(g["title"])}<span class="count">{len(g["items"])} 张</span></h2>'
            f'<p class="intro">{escape(g["intro"])}</p>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OFF 美术画廊 · OFF Art Gallery</title>
<style>
:root {{ --ink:#e8e6e1; --bg:#0d0d0f; --dim:#9a978e; --line:#2a2a30; --accent:#f2f2f2; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--ink); font-family:'Courier New', monospace; line-height:1.6; }}
header {{ padding:64px 20px 40px; text-align:center; border-bottom:1px solid var(--line); }}
header h1 {{ font-size:2.2rem; letter-spacing:.35em; text-transform:uppercase; }}
header .tagline {{ color:var(--dim); margin-top:14px; font-size:.95rem; max-width:640px; margin-left:auto; margin-right:auto; }}
nav {{ display:flex; flex-wrap:wrap; justify-content:center; gap:8px 18px; padding:18px 12px; border-bottom:1px solid var(--line); }}
nav a {{ color:var(--dim); text-decoration:none; font-size:.85rem; letter-spacing:.08em; }}
nav a:hover {{ color:var(--ink); }}
main {{ max-width:1200px; margin:0 auto; padding:20px; }}
.group {{ margin:56px 0; }}
.group h2 {{ font-size:1.25rem; letter-spacing:.2em; border-left:4px solid var(--ink); padding-left:12px; }}
.group .count {{ color:var(--dim); font-size:.8rem; margin-left:10px; letter-spacing:.1em; }}
.group .intro {{ color:var(--dim); font-size:.9rem; margin:12px 0 20px 16px; max-width:760px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(200px,1fr)); gap:10px; }}
.card {{ display:block; background:var(--line); overflow:hidden; aspect-ratio:1/1; }}
.card img {{ width:100%; height:100%; object-fit:cover; display:block; filter:grayscale(.15); transition:transform .25s, filter .25s; }}
.card:hover img {{ transform:scale(1.04); filter:grayscale(0); }}
footer {{ border-top:1px solid var(--line); margin-top:80px; padding:36px 20px 60px; text-align:center; color:var(--dim); font-size:.8rem; line-height:2; }}
footer a {{ color:var(--ink); }}
#lightbox {{ position:fixed; inset:0; background:rgba(0,0,0,.92); display:none; align-items:center; justify-content:center; z-index:99; cursor:zoom-out; }}
#lightbox img {{ max-width:92vw; max-height:88vh; }}
#lightbox .cap {{ position:fixed; bottom:24px; left:0; right:0; text-align:center; color:var(--dim); font-size:.8rem; }}
@media (max-width:600px) {{ header h1 {{ font-size:1.5rem; }} }}
</style>
</head>
<body>
<header>
<h1>OFF</h1>
<p class="tagline">《OFF》(2008) · Mortis Ghost 美术设定画廊<br>
The Batter 净化之旅的设定图、概念草稿、官方美术与周边档案</p>
</header>
<nav>
<a href="#g0">官方宣传</a><a href="#g1">作者概念图</a><a href="#g2">角色</a><a href="#g3">区域</a><a href="#g4">封面标志</a><a href="#g5">粉丝档案</a><a href="#g6">周边收藏</a>
</nav>
<main>
{''.join(sections)}
</main>
<footer>
<p>《OFF》© Mortis Ghost / Unproductive Fun Time · 音乐：Alias Conrad Coldwood · 实体版：Fangamer</p>
<p>本画廊仅供个人研究收藏，图片版权归原作者所有，禁止商用与二次发布。</p>
<p>资料来源：<a href="https://offtherpg.com">offtherpg.com</a> · <a href="https://www.fangamer.com/collections/off">Fangamer</a> · <a href="https://mortisghost.tumblr.com">Mortis Ghost</a> · <a href="https://off.fandom.com">OFF Wiki</a></p>
<p>完整资料包（1272 张图 + 设定文本 + 7 篇访谈）保存在本地 <code>D:/pythoncode/off-art</code></p>
</footer>
<div id="lightbox"><img id="lb-img" alt=""><div class="cap" id="lb-cap"></div></div>
<script>
const lb = document.getElementById('lightbox');
const img = document.getElementById('lb-img');
const cap = document.getElementById('lb-cap');
document.querySelectorAll('.card').forEach(a => {{
  a.addEventListener('click', e => {{
    e.preventDefault();
    img.src = a.href;
    cap.textContent = a.dataset.caption + ' · ' + a.href.split('/').pop();
    lb.style.display = 'flex';
  }});
}});
lb.addEventListener('click', () => lb.style.display = 'none');
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') lb.style.display = 'none'; }});
</script>
</body>
</html>"""
    out = os.path.join(DOCS, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html -> {out}")
    total = sum(len(g["items"]) for g in GROUPS)
    print(f"共 {len(GROUPS)} 组 / {total} 张图片")


if __name__ == "__main__":
    build()
