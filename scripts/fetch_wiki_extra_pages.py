# -*- coding: utf-8 -*-
"""
补抓 OFF Wiki 缺失/补充设定页面（action=parse 渲染文本 → Markdown）。
用法: python fetch_wiki_extra_pages.py
输出: ../wiki/<页面名>.md ；更新 ../wiki/_failed_pages.txt（真实缺失记录）
"""
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
API = "https://off.fandom.com/api.php"
WIKI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wiki")
INTERVAL = 0.7

# 补充页面（填补任务清单缺口 + 追加核心设定页）
EXTRA_PAGES = [
    "Sugar",              # 任务里 Sugarcube 的对应页面
    "Spectres",           # 任务里 Spectre 的对应页面（复数）
    "The_Queen",          # Vader_Eloha 重定向的目标（正典反派页）
    "Enoch", "Alpha", "Omega", "Epsilon",   # 守护者/Addition 角色
    "Purified_Zones", "Zone_0", "Zone_4",   # 额外区域设定
    "The_Puppeteer", "The_Nothingness",     # 重要剧情设定
    "Mortis_Ghost",       # 作者页（美术资料相关）
    "World_Map",
]

BLOCK_TAGS = {"p", "div", "table", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
              "br", "aside", "figure", "blockquote", "ul", "ol", "section", "footer",
              "dl", "dt", "dd", "tbody", "thead", "hr"}
SKIP_TAGS = {"script", "style", "noscript"}


class TextExtractor(HTMLParser):
    """HTML → 段落化纯文本。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.block_stack = []
        self.in_drop = 0
        self._last_was_block = True

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        classes = dict(attrs).get("class", "")
        if tag == "span" and "mw-editsection" in classes:
            self.in_drop += 1
            return
        if tag in BLOCK_TAGS:
            if not self._last_was_block:
                self.parts.append("\n")
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.parts.append("\n")
            self.block_stack.append(tag)
            self._last_was_block = True

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag == "span" and self.in_drop:
            self.in_drop -= 1
            return
        if tag in BLOCK_TAGS:
            if not self._last_was_block:
                self.parts.append("\n")
            self._last_was_block = True
            if self.block_stack:
                self.block_stack.pop()

    def handle_data(self, data):
        if self.skip_depth or self.in_drop:
            return
        data = data.replace("\u00a0", " ")
        if not data.strip():
            return
        if self._last_was_block:
            data = data.lstrip()
        self.parts.append(data)
        self._last_was_block = False

    def text(self):
        raw = "".join(self.parts)
        lines = [ln.strip() for ln in raw.split("\n")]
        out, blank = [], 0
        for ln in lines:
            if ln:
                out.append(ln)
                blank = 0
            else:
                blank += 1
                if blank <= 1:
                    out.append("")
        return "\n".join(out).strip()


def fetch_page_text(title):
    """抓取单页渲染文本，返回 (ok, text 或错误信息, 实际页面标题)。"""
    params = {"action": "parse", "prop": "text", "page": title, "redirects": True, "format": "json"}
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
                return False, str(e)[:120], title
            time.sleep(2 * (attempt + 1))
    data = r.json()
    if "error" in data:
        return False, data["error"].get("info", str(data["error"])), title
    parse = data.get("parse")
    if not parse or "text" not in parse:
        return False, "no parse result", title
    if parse.get("missing"):
        return False, "missing", title
    actual = parse.get("title", title)
    ex = TextExtractor()
    ex.feed(parse["text"]["*"])
    return True, ex.text(), actual


def main():
    os.makedirs(WIKI_DIR, exist_ok=True)
    saved, failed = [], []
    for i, page in enumerate(EXTRA_PAGES, 1):
        ok, text, actual = fetch_page_text(page)
        if not ok or not text.strip():
            failed.append((page, text if not ok else "empty"))
            print(f"  ({i}/{len(EXTRA_PAGES)}) {page}: FAIL {str(text)[:60]}")
            time.sleep(INTERVAL)
            continue
        # 目标文件名用实际页面标题（空格换下划线）
        fname = actual.replace(" ", "_").replace("/", "_") + ".md"
        if fname.startswith("Category_") or actual.startswith("Category:"):
            failed.append((page, "redirects to category, skipped"))
            print(f"  ({i}/{len(EXTRA_PAGES)}) {page}: SKIP (category)")
            time.sleep(INTERVAL)
            continue
        with open(os.path.join(WIKI_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"# {actual}\n\n{text}\n")
        saved.append((page, fname))
        print(f"  ({i}/{len(EXTRA_PAGES)}) {page}: OK -> {fname} ({len(text)} 字)")
        time.sleep(INTERVAL)

    # 更新失败记录（合并全站确认不存在的页面）
    confirmed_missing = [
        ("Almighty", "wiki 无此页面"),
        ("Unproductive_Fun_Time", "wiki 无此页面"),
    ] + [(p, r) for p, r in failed]
    with open(os.path.join(WIKI_DIR, "_failed_pages.txt"), "w", encoding="utf-8") as f:
        for name, reason in confirmed_missing:
            f.write(f"{name}\t{reason}\n")
    print(f"\n完成: 新保存 {len(saved)} 页, 失败/缺失 {len(confirmed_missing)} 项")
    for p, r in confirmed_missing:
        print(f"  - {p}: {r}")


if __name__ == "__main__":
    main()
