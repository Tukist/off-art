# -*- coding: utf-8 -*-
"""
补抓缺失页面并重建 _index.md。
- 补抓: Spectres (替代 Spectre), Sugar (替代 Sugarcube)
- Almighty / Unproductive_Fun_Time 在 wiki 上不存在 -> 记录缺失
- 重新生成 ../wiki/_index.md
用法: python patch_wiki_pages.py
"""
import os
import re
import time
import requests
from bs4 import BeautifulSoup

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
API = "https://off.fandom.com/api.php"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_DIR = os.path.join(ROOT, "wiki")

NEW_PAGES = ["Spectres", "Sugar"]
MISSING = ["Almighty", "Unproductive_Fun_Time"]  # 确认不存在的页面


def get_page_html(title):
    params = {
        "action": "parse", "prop": "text", "format": "json",
        "page": title, "redirects": "1",
    }
    for attempt in range(4):
        try:
            r = requests.get(API, params=params, proxies=PROXY, headers=HEADERS, timeout=30)
            if r.status_code in (429, 403):
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    d = r.json()
    if "parse" not in d:
        return None, None
    p = d["parse"]
    title_used = p.get("redirects", [{}])[0].get("to", title) if p.get("redirects") else title
    return p["text"]["*"], title_used


def clean_inline(el):
    for img in el.find_all(["img", "audio", "video"]):
        img.decompose()
    for sup in el.find_all("sup"):
        sup.decompose()
    return el.get_text(" ", strip=True)


def html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, .navbox, .mw-editsection, .reference, .noprint, .toc, sup.reference"):
        tag.decompose()
    out = []
    for box in soup.select("aside.portable-infobox"):
        lines = []
        for item in box.find_all(["h2", "h3", "div"], recursive=True):
            cls = " ".join(item.get("class", []))
            if "pi-title" in cls or "pi-header" in cls:
                t = item.get_text(" ", strip=True)
                if t:
                    lines.append(f"= {t} =")
            elif "pi-data" in cls:
                label = item.select_one(".pi-data-label")
                value = item.select_one(".pi-data-value")
                if label and value:
                    l = label.get_text(" ", strip=True)
                    v = value.get_text(" ", strip=True)
                    if l and v:
                        lines.append(f"* {l}: {v}")
        if lines:
            out.append("```info")
            out.extend(lines)
            out.append("```")
        box.decompose()

    main_el = soup.select_one(".mw-parser-output") or soup.body or soup
    for child in main_el.children:
        if not hasattr(child, "name") or child.name is None:
            continue
        name = child.name
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            txt = child.get_text(" ", strip=True)
            if txt:
                out.append(f"{'#' * (int(name[1]) + 1)} {txt}")
        elif name == "p":
            txt = clean_inline(child)
            if txt:
                out.append(txt)
                out.append("")
        elif name in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                txt = clean_inline(li)
                if txt:
                    out.append(f"- {txt}")
            out.append("")
        elif name == "table":
            rows = []
            for tr in child.find_all("tr"):
                cells = [clean_inline(c) if clean_inline(c) else " " for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append("| " + " | ".join(cells) + " |")
            if rows:
                out.append("\n".join(rows[:2]) + "\n" + "\n".join(rows[2:]))
        elif name == "blockquote":
            for p in child.find_all("p", recursive=False):
                txt = clean_inline(p)
                if txt:
                    out.append(f"> {txt}")
            out.append("")
        elif name == "div":
            txt = clean_inline(child)
            if txt:
                out.append(txt)
                out.append("")
    md = "\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def summarize(md_path):
    try:
        with open(md_path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return ""
    text = re.sub(r"```info.*?```", "", text, flags=re.S)
    # 跳过剧透警告、消歧义提示等噪音段落
    noise_prefixes = ("spoiler warning", "this article is a stub", "for the location")
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para or para.startswith("#") or para.startswith("```"):
            continue
        flat = re.sub(r"[#*>`|\[\]{}]", "", para)
        flat = re.sub(r"\s+", " ", flat).strip()
        if flat.lower().startswith(noise_prefixes):
            continue
        if flat:
            return flat[:120]
    return ""


def main():
    os.makedirs(WIKI_DIR, exist_ok=True)
    added = []
    for title in NEW_PAGES:
        print(f"补抓: {title}")
        html, title_used = get_page_html(title)
        if html is None:
            print(f"  !! {title} 仍不存在")
            continue
        md = html_to_markdown(html)
        out_title = title_used or title
        fname = f"{title}.md"
        with open(os.path.join(WIKI_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"# {out_title}\n\n{md}\n")
        added.append((fname, out_title))
        print(f"  已保存 {fname} ({len(md)} 字符)")
        time.sleep(0.6)

    # 重建 _index.md
    index_path = os.path.join(WIKI_DIR, "_index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# OFF Wiki 设定页面索引\n\n")
        f.write("> 来源: https://off.fandom.com/wiki/ (经代理抓取, action=parse 渲染文本)\n\n")
        f.write("| 文件 | 页面 | 内容概要 |\n")
        f.write("|------|------|----------|\n")
        for fn in sorted(os.listdir(WIKI_DIR)):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            title = fn[:-3]
            page = title.replace("_", " ")
            summary = summarize(os.path.join(WIKI_DIR, fn))
            f.write(f"| [{fn}]({fn}) | {page} | {summary} |\n")
        if MISSING:
            f.write("\n## 抓取失败页面（wiki 上不存在）\n\n")
            for t in MISSING:
                f.write(f"- {t}（The page you specified doesn't exist.）\n")
    print(f"索引已重建: {index_path}")

    # 更新 _failed_pages.txt
    with open(os.path.join(WIKI_DIR, "_failed_pages.txt"), "w", encoding="utf-8") as f:
        for t in MISSING:
            f.write(f"{t}\tThe page you specified doesn't exist.\n")
    print("缺失记录已更新")


if __name__ == "__main__":
    main()
