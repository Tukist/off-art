# -*- coding: utf-8 -*-
"""
从 off.fandom.com 抓取核心设定页面，转存为 Markdown（纯文本正文）。

背景：该 wiki 未启用 TextExtracts 扩展（prop=extracts 不可用），
因此改用 action=parse&prop=text 拿到渲染后的 HTML，再用自写的
HTMLParser 提取纯文本（跳过 script/style，块级标签转段落）。

- 每页存为 wiki/<PageName>.md，开头为 "# <PageName>"；
- 抓不到的页面记录到 wiki/_failed_pages.txt；
- 最后生成 wiki/_index.md（文件名 + 一句话内容说明，取自首段）。
"""
import html
import os
import re
import sys
import time
from html.parser import HTMLParser

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = "D:/pythoncode/off-art"
WIKI_DIR = os.path.join(BASE_DIR, "wiki")
os.makedirs(WIKI_DIR, exist_ok=True)

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
API = "https://off.fandom.com/api.php"
INTERVAL = 0.7

PAGES = [
    "OFF", "The_Batter", "The_Judge", "Zacharie", "The_Player",
    "Dedan", "Japhet", "Vader_Eloha", "Almighty", "Sugarcube",
    "Elsen", "Spectre", "Zones", "Zone_1", "Zone_2", "Zone_3",
    "The_Room", "Unproductive_Fun_Time",
]

# 视为"块级"的标签：遇到它们就换行/分段
BLOCK_TAGS = {"p", "div", "table", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
              "br", "aside", "figure", "blockquote", "ul", "ol", "section", "footer",
              "dl", "dt", "dd", "tbody", "thead", "hr"}
SKIP_TAGS = {"script", "style", "noscript"}
# 不想显示的标签内容：导航/编辑链接等
DROPPED_TAGS = {"sup", "span.mw-editsection"}


class TextExtractor(HTMLParser):
    """把 HTML 转成段落化纯文本。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.block_stack = []
        self.in_drop = 0
        self._last_was_block = True  # 开头不产生空行

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
        # 规范化空白：每行去首尾空格，压缩多余空行
        lines = [ln.strip() for ln in raw.split("\n")]
        out = []
        blank = 0
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
    """抓取单页渲染文本，返回 (ok, text 或错误信息)。"""
    params = {
        "action": "parse",
        "prop": "text",
        "page": title,
        "redirects": True,
        "format": "json",
    }
    resp = requests.get(API, params=params, proxies=PROXY, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        return False, data["error"].get("info", str(data["error"]))
    parse = data.get("parse")
    if not parse or "text" not in parse:
        return False, "no parse result"
    if parse.get("missing"):
        return False, "missing"
    extractor = TextExtractor()
    extractor.feed(parse["text"]["*"])
    return True, extractor.text()


def summarize(text):
    """从首段提取一句话内容说明（去掉引用标记，截断到 200 字）。"""
    para = re.sub(r"\[\d+\]", "", text.strip())
    para = re.sub(r"\s+", " ", para)
    if not para:
        return "(无正文)"
    end = min(len(para), 200)
    cut = para.rfind(".", 0, end)
    cut_zh = para.rfind("。", 0, end)
    cut = max(cut, cut_zh)
    if cut > 30:
        para = para[: cut + 1]
    else:
        para = para[:end] + ("…" if len(para) > end else "")
    return para


def main():
    print(f"[1/3] 抓取 {len(PAGES)} 个设定页面 ...")
    results = {}   # page_name -> (ok, text_or_error)
    for i, page in enumerate(PAGES, 1):
        ok, text = fetch_page_text(page)
        results[page] = (ok, text)
        status = f"OK {len(text)} 字符" if ok else f"FAIL: {text[:80]}"
        print(f"  ({i}/{len(PAGES)}) {page}: {status}")
        time.sleep(INTERVAL)

    print("[2/3] 写入 Markdown ...")
    index_rows = []
    failed = []
    for page, (ok, text) in results.items():
        if not ok or not text.strip():
            failed.append((page, text if not ok else "empty"))
            continue
        path = os.path.join(WIKI_DIR, page + ".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {page}\n\n{text}\n")
        index_rows.append((page, summarize(text)))

    with open(os.path.join(WIKI_DIR, "_failed_pages.txt"), "w", encoding="utf-8") as f:
        for name, reason in failed:
            f.write(f"{name}\t{reason}\n")

    print("[3/3] 生成 _index.md ...")
    with open(os.path.join(WIKI_DIR, "_index.md"), "w", encoding="utf-8") as f:
        f.write("# OFF Wiki 设定页面索引\n\n")
        f.write(f"> 来源: off.fandom.com（action=parse 渲染文本，共 {len(index_rows)} 页）\n\n")
        for name, summary in index_rows:
            f.write(f"- [{name}.md]({name}.md) — {summary}\n")
        if failed:
            f.write("\n## 抓取失败页面\n\n")
            f.write("\n".join(f"- {n}（{r}）" for n, r in failed) + "\n")

    print(f"保存页面: {len(index_rows)}，失败: {len(failed)}")
    if failed:
        print("失败明细:")
        for n, r in failed:
            print(f"  {n}: {r}")


if __name__ == "__main__":
    main()
