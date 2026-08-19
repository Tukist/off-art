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
import json
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
.tag { display:inline-block; border:1px solid var(--dim); color:var(--dim);
  font-size:.68rem; padding:1px 8px; letter-spacing:.12em; margin-right:8px; }
.lcard { display:block; background:var(--card); border:1px solid var(--line);
  text-decoration:none; padding:18px 20px; transition:border-color .2s, transform .2s; }
.lcard:hover { border-color:var(--ink); transform:translateY(-2px); }
.lcard h3 { font-size:1rem; letter-spacing:.08em; color:var(--ink); }
.lcard .meta { color:var(--dim); font-size:.78rem; margin-top:8px; display:-webkit-box;
  -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.lcard .arrow { float:right; color:var(--dim); font-size:1.1rem; }
.lcard ul { margin:10px 0 0 18px; color:#8a877e; font-size:.74rem; }
.lcard li { margin:2px 0; display:-webkit-box; -webkit-line-clamp:2;
  -webkit-box-orient:vertical; overflow:hidden; }
header.sub p a { color:var(--dim); text-decoration:none; border-bottom:1px dotted var(--dim); }
header.sub p a:hover { color:var(--ink); }
.article { max-width:880px; margin:0 auto; padding:36px 20px 70px; }
.article h1 { font-size:1.35rem; letter-spacing:.15em; margin:30px 0 8px; }
.article h2 { font-size:1.25rem; letter-spacing:.12em; margin:30px 0 8px; border-left:4px solid var(--ink); padding-left:12px; }
.article h3 { font-size:1.05rem; margin:20px 0 6px; }
.article p { margin:12px 0; color:#d2d0c9; }
.article ul, .article ol { margin:10px 0 10px 26px; color:#d2d0c9; }
.article table { border-collapse:collapse; margin:14px 0; width:100%; font-size:.85rem; }
.article th, .article td { border:1px solid var(--line); padding:6px 12px; text-align:left; }
.article code { background:var(--line); padding:1px 6px; font-size:.85rem; }
.article pre { background:#0a0a0c; border:1px solid var(--line); padding:14px; overflow-x:auto; font-size:.8rem; margin:12px 0; }
.article a { color:var(--ink); text-decoration:underline; text-underline-offset:3px; }
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

/* ===== 侧边栏音乐播放器（OFF 风） ===== */
.player { position:fixed; right:16px; bottom:16vh; z-index:80; }
#player-toggle { width:48px; height:66px; border:1px solid var(--line); background:#0d0d0f;
  color:var(--ink); cursor:pointer; font-size:1.1rem; letter-spacing:.1em;
  transition:background .25s, color .25s, border-color .25s, transform .38s cubic-bezier(.22,1,.36,1); }
#player-toggle:hover { background:var(--ink); color:var(--bg); border-color:var(--ink); }
.player.open #player-toggle { border-color:var(--ink); color:var(--dim); transform:rotate(180deg); }
#player-toggle.playing { animation:eq 1.2s ease-in-out infinite; }
@keyframes eq { 0%,100%{ opacity:1 } 50%{ opacity:.45 } }
#player-panel { position:absolute; right:56px; bottom:0; width:322px; max-width:86vw;
  max-height:min(74vh,620px); display:flex; flex-direction:column; overflow:hidden;
  background:rgba(13,13,15,.96); border:1px solid var(--line); box-shadow:0 0 0 1px rgba(0,0,0,.4);
  opacity:0; transform:translateX(18px); pointer-events:none;
  transition:opacity .38s cubic-bezier(.22,1,.36,1), transform .38s cubic-bezier(.22,1,.36,1); }
.player.open #player-panel { opacity:1; transform:translateX(0); pointer-events:auto; }
.p-head { display:flex; align-items:center; justify-content:space-between; padding:12px 16px;
  border-bottom:1px solid var(--line); }
.p-head .p-logo { font-size:.78rem; letter-spacing:.3em; color:var(--ink); }
.p-head .p-logo i { font-style:normal; color:var(--dim); margin-right:6px; }
#player-close { background:none; border:none; color:var(--dim); font-size:1rem; cursor:pointer;
  padding:2px 8px; transition:color .2s; }
#player-close:hover { color:var(--ink); }
.p-now { display:flex; align-items:center; gap:14px; padding:18px 16px 14px; }
.p-disc { width:52px; height:52px; flex:none; border:1px solid var(--dim); border-radius:50%;
  display:flex; align-items:center; justify-content:center; color:var(--dim); font-size:1.1rem;
  background:repeating-conic-gradient(#111 0 8deg, #1c1c20 8deg 16deg); }
.p-disc.spin { animation:spin 5s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
.p-meta { min-width:0; }
.p-track { font-size:.9rem; color:var(--ink); letter-spacing:.04em; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
.p-artist { font-size:.72rem; color:var(--dim); margin-top:3px; }
.p-controls { display:flex; justify-content:center; gap:22px; padding:6px 0 12px; }
.p-controls button { background:none; border:1px solid transparent; color:var(--ink);
  font-size:1rem; cursor:pointer; width:38px; height:38px; transition:all .2s; }
.p-controls button:hover { border-color:var(--dim); background:var(--ink); color:var(--bg); }
#p-play { font-size:1.05rem; border:1px solid var(--dim); }
.p-progress, .p-vol { padding:0 16px; }
.p-bar { position:relative; height:14px; cursor:pointer; display:flex; align-items:center; }
.p-bar .p-fill { position:absolute; left:0; top:6px; height:2px; background:var(--ink);
  width:0; transition:background .2s; }
.p-bar::before { content:""; position:absolute; left:0; right:0; top:6px; height:2px;
  background:var(--line); }
.p-bar:hover .p-fill { background:#fff; }
.p-bar .p-knob { position:absolute; top:3px; width:8px; height:8px; background:var(--ink);
  transform:translateX(-50%) scale(0); transition:transform .2s; }
.p-bar:hover .p-knob { transform:translateX(-50%) scale(1); }
.p-times { display:flex; justify-content:space-between; color:var(--dim);
  font-size:.68rem; padding:2px 16px 10px; }
.p-vol { display:flex; align-items:center; gap:10px; padding-bottom:12px; }
.p-vol span { color:var(--dim); font-size:.66rem; letter-spacing:.15em; }
.p-vol .p-bar { flex:1; }
.p-list { flex:1; overflow-y:auto; border-top:1px solid var(--line); list-style:none;
  padding:6px 0 10px; scrollbar-width:thin; scrollbar-color:var(--line) transparent; }
.p-list::-webkit-scrollbar { width:6px; }
.p-list::-webkit-scrollbar-thumb { background:var(--line); }
.p-list li { padding:7px 16px; font-size:.76rem; color:var(--dim); cursor:pointer;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  transition:color .2s, background .2s, padding-left .25s; }
.p-list li:hover { color:var(--ink); background:rgba(255,255,255,.04); padding-left:20px; }
.p-list li.playing { color:var(--ink); }
.p-list li.playing::before { content:"▍"; margin-right:6px; animation:eq 1.5s ease-in-out infinite; }
"""

FOOTER = """
<footer>
<p>《OFF》© Mortis Ghost / Unproductive Fun Time · 音乐：Alias Conrad Coldwood · 实体版：Fangamer</p>
<p>本站仅供个人研究收藏，图片与文字版权归原作者所有，禁止商用与二次发布。</p>
<p>资料源：<a href="https://offtherpg.com">offtherpg.com</a> · <a href="https://www.fangamer.com/collections/off">Fangamer</a> ·
<a href="https://mortisghost.tumblr.com">Mortis Ghost</a> · <a href="https://off.fandom.com">OFF Wiki</a></p>
</footer>
"""

PLAYER_HTML = """
<div class="player" id="player">
  <button id="player-toggle" title="OFF 原声播放器">♪</button>
  <div id="player-panel">
    <div class="p-head"><span class="p-logo"><i>◆</i>OFF // OST</span><button id="player-close" aria-label="收起">×</button></div>
    <div class="p-now">
      <div class="p-disc" id="p-disc">♪</div>
      <div class="p-meta"><div class="p-track" id="p-track">选择一首曲目</div><div class="p-artist" id="p-artist">Alias Conrad Coldwood</div></div>
    </div>
    <div class="p-controls">
      <button id="p-prev" title="上一首">⏮</button>
      <button id="p-play" title="播放/暂停">▶</button>
      <button id="p-next" title="下一首">⏭</button>
    </div>
    <div class="p-progress">
      <div class="p-bar" id="p-bar"><div class="p-fill" id="p-fill"></div><div class="p-knob" id="p-knob"></div></div>
      <div class="p-times"><span id="p-cur">0:00</span><span id="p-dur">0:00</span></div>
    </div>
    <div class="p-vol"><span>VOL</span><div class="p-bar" id="v-bar"><div class="p-fill" id="v-fill"></div></div></div>
    <ul class="p-list" id="p-list"></ul>
  </div>
</div>
"""

PLAYER_JS = r"""
(function(){
var TRACKS = __TRACKS__;
var PRE = "__PREFIX__";
if(!TRACKS.length) return;
var audio = new Audio();
var idx = 0;
var list = document.getElementById('p-list');
var el = function(k){ return document.getElementById(k); };
var fill = el('p-fill'), knob = el('p-knob'), vfill = el('v-fill');
function fmt(s){ s = Math.max(0, Math.floor(s||0)); return Math.floor(s/60) + ':' + (s%60<10?'0':'') + (s%60); }
function setFill(p){ fill.style.width = (p*100) + '%'; knob.style.left = (p*100) + '%'; }
function play(i, autostart){
  if(i<0) i = TRACKS.length-1; if(i>=TRACKS.length) i = 0;
  idx = i; var t = TRACKS[i];
  audio.src = PRE + t.file;
  if(autostart !== false) audio.play().catch(function(){});
  el('p-track').textContent = t.title;
  el('p-artist').textContent = t.artist;
  el('p-dur').textContent = fmt(t.dur);
  Array.prototype.forEach.call(list.children, function(li,j){ li.className = (j===idx) ? 'playing' : ''; });
  save();
}
el('p-list').innerHTML = '';
TRACKS.forEach(function(t,i){
  var li = document.createElement('li');
  li.textContent = (i<9?'0':'')+(i+1) + '. ' + t.title;
  li.title = t.title + ' — ' + t.artist;
  li.addEventListener('click', function(){ play(i); });
  el('p-list').appendChild(li);
});
audio.addEventListener('timeupdate', function(){
  var d = audio.duration || TRACKS[idx].dur;
  el('p-cur').textContent = fmt(audio.currentTime);
  if(d) setFill(audio.currentTime/d);
});
audio.addEventListener('ended', function(){ play(idx+1); });
audio.addEventListener('play', function(){
  el('p-play').textContent = '\u275A\u275A';
  el('p-disc').classList.add('spin');
  el('player-toggle').classList.add('playing');
});
audio.addEventListener('pause', function(){
  el('p-play').textContent = '\u25B6';
  el('p-disc').classList.remove('spin');
  el('player-toggle').classList.remove('playing');
});
el('p-play').addEventListener('click', function(){ audio.paused ? audio.play() : audio.pause(); });
el('p-prev').addEventListener('click', function(){ play(idx-1); });
el('p-next').addEventListener('click', function(){ play(idx+1); });
function seekBar(bar, fillEl, cb){
  bar.addEventListener('pointerdown', function(e){
    var set = function(ev){
      var r = bar.getBoundingClientRect();
      var p = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width));
      fillEl.style.width = (p*100) + '%';
      cb(p);
    };
    set(e);
    bar.setPointerCapture(e.pointerId);
    bar.addEventListener('pointermove', set);
    bar.addEventListener('pointerup', function(){ bar.removeEventListener('pointermove', set); });
  });
}
seekBar(el('p-bar'), fill, function(p){ if(audio.duration) audio.currentTime = p*audio.duration; });
seekBar(el('v-bar'), vfill, function(p){ audio.volume = p; localStorage.setItem('off_vol', p); });
var vol = parseFloat(localStorage.getItem('off_vol'));
if(!isNaN(vol) && vol>=0 && vol<=1){ audio.volume = vol; vfill.style.width = (vol*100) + '%'; }
else { audio.volume = 0.7; vfill.style.width = '70%'; }
var player = document.getElementById('player');
function setOpen(o){ player.classList.toggle('open', o); localStorage.setItem('off_open', o?'1':'0'); }
el('player-toggle').addEventListener('click', function(){ setOpen(!player.classList.contains('open')); });
el('player-close').addEventListener('click', function(){ setOpen(false); });
// 点击面板以外区域收起 + ESC 收起
document.addEventListener('click', function(e){
  if(player.classList.contains('open') && !player.contains(e.target)) setOpen(false);
});
document.addEventListener('keydown', function(e){ if(e.key === 'Escape') setOpen(false); });
if(localStorage.getItem('off_open') === '1') player.classList.add('open');
function save(){
  try { localStorage.setItem('off_music', JSON.stringify({idx:idx, time:audio.currentTime||0})); } catch(e){}
}
setInterval(save, 3000);
window.addEventListener('pagehide', save);
var st = null;
try { st = JSON.parse(localStorage.getItem('off_music')); } catch(e){}
if(st && st.idx>=0 && st.idx<TRACKS.length){
  idx = st.idx;
  var t = TRACKS[idx];
  audio.src = PRE + t.file;
  el('p-track').textContent = t.title;
  el('p-artist').textContent = t.artist;
  el('p-dur').textContent = fmt(t.dur);
  Array.prototype.forEach.call(list.children, function(li,j){ li.className = (j===idx) ? 'playing' : ''; });
  audio.addEventListener('loadedmetadata', function(){ audio.currentTime = st.time || 0; });
}
})();
"""


def player_markup(prefix):
    try:
        tracks = json.load(open(os.path.join(BASE, "docs", "music.json"), encoding="utf-8"))
    except Exception:
        tracks = []
    js = PLAYER_JS.replace("__TRACKS__", json.dumps(tracks, ensure_ascii=False)).replace("__PREFIX__", prefix)
    return PLAYER_HTML + "\n<script>" + js + "</script>"

NAV_LINKS = [
    ("官方宣传", "index.html#g0"), ("概念图", "index.html#g1"), ("角色", "index.html#g2"),
    ("区域", "index.html#g3"), ("封面标志", "index.html#g4"), ("粉丝档案", "index.html#g5"),
    ("周边收藏", "index.html#g6"), ("设定文本", "lore.html"), ("访谈", "interviews.html"),
]


def topbar(brand_link="index.html", extra_links=None, prefix=""):
    links = list(NAV_LINKS)
    if extra_links:
        links = extra_links + links
    items = [f'<a class="brand" href="{prefix}{brand_link}">OFF</a>']
    for name, href in links:
        h = href if href.startswith("http") else prefix + href
        items.append(f'<a href="{h}">{name}</a>')
    return f'<div class="topbar"><nav>{"".join(items)}</nav></div>'


def page(hero, main_html, brand_link="index.html", extra_links=None, prefix=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{hero["title"]}</title>
<style>{CSS}</style>
</head>
<body>
{topbar(brand_link, extra_links, prefix)}
{hero["html"]}
<main>
{main_html}
</main>
{FOOTER}
{player_markup(prefix)}
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
        if re.match(r"^#\s", ln):  # 跳过标题行
            continue
        if low.startswith("contents"):
            skip = True
        if skip and low == "references":
            skip = False
        if skip or "spoiler warning" in low or not ln.strip():
            continue
        # 过滤 infobox 噪音短标签（如 Artwork / Battle / Mask 1）
        if len(ln.strip()) < 25 and not re.search(r"[.!?。！？]", ln):
            continue
        cleaned.append(ln)
    text = re.sub(r"\s+", " ", " ".join(cleaned)).strip()
    text = re.sub(r"^#+\s*", "", text)
    return text[:200] + ("…" if len(text) > 200 else "")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build_lore():
    os.makedirs(os.path.join(DOCS, "lore"), exist_ok=True)
    sections = []
    for cat, names in LORE_GROUPS:
        cards = []
        for name in names:
            path = os.path.join(WIKI_DIR, name + ".md")
            if not os.path.exists(path):
                continue
            raw = open(path, encoding="utf-8").read()
            slug = slugify(name)
            body = re.sub(r"^#\s+.+", "", raw, count=1, flags=re.M).strip()
            # 独立详情页
            hero = {"title": f"OFF 设定 · {display_name(name)}",
                    "html": f'<header class="sub"><h1>{escape(display_name(name))}</h1>'
                            f'<p><span class="tag">{escape(cat)}</span>'
                            f'<a href="../lore.html">← 设定文本</a> · '
                            f'<a href="../index.html">画廊</a></p></header>',
                    "script": ""}
            detail = page(hero, f'<div class="article">{md_to_html(body)}</div>',
                          brand_link="../index.html", prefix="../")
            open(os.path.join(DOCS, "lore", slug + ".html"), "w", encoding="utf-8").write(detail)
            # 索引卡片（跳详情页）
            cards.append(f'<a class="lcard" href="lore/{slug}.html"><span class="arrow">→</span>'
                         f'<span class="tag">{escape(cat)}</span>'
                         f'<h3>{escape(display_name(name))}</h3>'
                         f'<div class="meta" title="{escape(lore_excerpt(raw))}">{escape(lore_excerpt(raw))}</div></a>')
        if cards:
            sections.append(f'<section class="group" id="{escape(cat)}">'
                            f'<h2>{escape(cat)}<span class="count">{len(cards)} 篇</span></h2>'
                            f'<div class="cardlist">{"".join(cards)}</div></section>')
    main = "".join(sections)
    hero = {"title": "OFF 设定文本 · Lore",
            "html": f'<header class="sub"><h1>设定文本 / Lore</h1>'
                    f'<p>来自 OFF Wiki（Fandom）的 23 页世界观设定 · 点击条目进入独立页面</p></header>',
            "script": ""}
    extra = [(c, f"lore.html#{c}") for c, _ in LORE_GROUPS]
    return page(hero, main, brand_link="index.html", extra_links=extra)


# ---------------- 访谈页 ----------------

def build_interviews():
    os.makedirs(os.path.join(DOCS, "interviews"), exist_ok=True)
    cards = []
    for path in sorted(os.listdir(INTV_DIR)):
        if not path.endswith(".md") or path.startswith("_"):
            continue
        raw = open(os.path.join(INTV_DIR, path), encoding="utf-8").read()
        title = re.search(r"^# (.+)$", raw, re.M)
        title = title.group(1).strip() if title else display_name(path)
        src = re.search(r"^-\s*来源:\s*(.+)$", raw, re.M)
        src_url = src.group(1).strip() if src else ""
        date = re.search(r"^-\s*日期:\s*(.+)$", raw, re.M)
        date_s = date.group(1).strip() if date else ""
        key = re.search(r"## 中文要点摘要\s*\n(.*?)(?=\n## )", raw, re.S)
        points = re.findall(r"^\s*-\s+(.+)$", key.group(1), re.M) if key else []
        full = re.search(r"## 全文\s*\n(.*)$", raw, re.S)
        body = md_to_html(full.group(1)) if full else "<p>（全文缺失）</p>"
        point_html = "".join(f'<li title="{escape(p)}">{md_inline(escape(p))}</li>' for p in points) or "<li>（无摘要）</li>"
        # Lore 模式：中文要点合并为单段摘要（灰色小字 + 截断 + 悬停全文）
        summary = "。".join(p for p in points).strip() + ("。" if points else "（无摘要）")
        year = date_s[:4] if date_s else ""
        slug = slugify(path[:-3])
        # 独立详情页
        hero = {"title": f"OFF 访谈 · {title}",
                "html": f'<header class="sub"><h1>{escape(title)}</h1>'
                        f'<p>{escape(date_s)} · '
                        f'<a href="{escape(src_url)}" target="_blank" rel="noopener">原始来源 ↗</a> · '
                        f'<a href="../interviews.html">← 访谈</a> · '
                        f'<a href="../index.html">画廊</a></p></header>',
                "script": ""}
        detail = page(hero, f'<div class="article">{body}</div>',
                      brand_link="../index.html", prefix="../")
        open(os.path.join(DOCS, "interviews", slug + ".html"), "w", encoding="utf-8").write(detail)
        # 索引卡片（Lore 模式：tag + 标题 + 单段摘要）
        cards.append(f'<a class="lcard" href="interviews/{slug}.html"><span class="arrow">→</span>'
                     f'<span class="tag">{escape(year) if year else "访谈"}</span>'
                     f'<h3>{escape(title)}</h3>'
                     f'<div class="meta" title="{escape(summary)}">{escape(summary)}</div></a>')
    main = f'<section class="group" id="interviews"><div class="cardlist">{"".join(cards)}</div></section>'
    hero = {"title": "OFF 作者访谈 · Interviews",
            "html": f'<header class="sub"><h1>作者访谈 / Interviews</h1>'
                    f'<p>7 篇访谈 · Mortis Ghost、Toby Fox、Morusque、Quinn K.、Nightmargin 与 15 周年直播整理 · 点击进入独立页面</p></header>',
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
