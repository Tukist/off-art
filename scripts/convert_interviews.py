#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 _raw/ 目录下抓取的 OFF 访谈 HTML 转成 Markdown，写入 ../interviews/。

支持的来源（各有不同的正文容器结构）：
  - gamatomic_off.html          : <section class="article__paragraph"> 内 Q/A div
  - offtherpg_<slug>.html       : <div id="interview"> 内 h2(问题) + p(回答)
  - tumblr_15th.html            : <div class="post"> 内 .title + .copy
  - tumblr_classic.html         : <div class="post loading"> 内 blockquote

只用 Python 标准库 (html.parser)。
输出：每个访谈一个 md 文件，头部元数据 + 中文摘要占位 + ## 全文。
"""

import html as html_mod
import os
import re
import sys
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "_raw")
OUT = os.path.join(BASE, "..", "interviews")


# ---------------------------------------------------------------- 配平提取
_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)\b[^>]*>")
_VOID = {"br", "img", "hr", "meta", "link", "input", "source", "area", "base",
         "col", "embed", "param", "track", "wbr"}


def extract_balanced(html, start):
    """html[start:] 必须以 '<tag...>' 开头；返回 (内部html, 结束偏移)。

    内部 html 不含外层开始/结束标签；支持嵌套同名标签与自闭合标签。
    """
    m = re.match(r"<\s*([a-zA-Z0-9]+)\b[^>]*>", html[start:])
    if not m:
        raise ValueError("不是标签开头: %r" % html[start:start + 60])
    tag = m.group(1)
    end = start + m.end()
    depth = 1
    while depth > 0:
        m2 = _TAG_RE.search(html, end)
        if not m2:
            break
        if m2.group(2).lower() in _VOID:
            end = m2.end()
            continue
        if m2.group(1) == "/":
            depth -= 1
        else:
            depth += 1
        end = m2.end()
    inner_start = start + m.end()
    close_start = end - (m2.end() - m2.start()) if m2 else len(html)
    close_after = m2.end() if m2 else len(html)
    return html[inner_start:close_start], close_after


# ---------------------------------------------------------------- 块级转换
class BlockConverter(HTMLParser):
    """把 HTML 片段转成 Markdown 文本（保留 h/p/ul/li/blockquote 结构）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []          # (kind, text)；kind: h2/h3/h4/p/li/quote/raw
        self.cur = []             # 当前块已累积的 inline 文本
        self.cur_kind = "p"
        self.ul_depth = 0
        self.in_li = False
        self.quote_depth = 0
        self.link_stack = []      # 未闭合的链接 href
        self.skip = 0             # script/style 深度

    # ---- inline 辅助 ----
    def _flush(self):
        text = "".join(self.cur).strip()
        self.cur = []
        if not text:
            return
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\*\*[\s\n]+\*\*", "", text)   # 清理空粗体产生的孤立 **
        text = re.sub(r"\n{3,}", "\n\n", text)
        if self.in_li:
            indent = "  " * self.ul_depth
            text = indent + "- " + text.replace("\n", "\n" + indent + "  ")
            self.blocks.append(("li", text))
        elif self.quote_depth:
            text = "\n".join("> " + ln for ln in text.split("\n"))
            self.blocks.append(("quote", text))
        else:
            self.blocks.append((self.cur_kind, text))

    def handle_starttag(self, tag, attrs):
        if self.skip:
            return
        tag = tag.lower()
        if tag in ("script", "style"):
            self.skip += 1
            return
        a = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.cur_kind = "h" + tag[1]
        elif tag == "p":
            self._flush()
            self.cur_kind = "p"
        elif tag == "blockquote":
            self._flush()
            self.quote_depth += 1
        elif tag in ("ul", "ol"):
            self._flush()
            self.ul_depth += 1
        elif tag == "li":
            self._flush()
            self.in_li = True
            self.cur_kind = "li"
        elif tag == "br":
            self.cur.append("\n")
        elif tag in ("b", "strong"):
            self.cur.append("**")
        elif tag in ("i", "em"):
            self.cur.append("*")
        elif tag == "a":
            self.cur.append("[")
            self.link_stack.append(a.get("href", ""))
        elif tag == "img":
            alt = a.get("alt", "")
            src = a.get("src", "")
            if src:
                self.cur.append("![%s](%s)" % (alt, src))
        # 其余 div/span/section/font/small/center 等无语义，忽略

    def handle_endtag(self, tag):
        if self.skip:
            if tag.lower() in ("script", "style"):
                self.skip -= 1
            return
        tag = tag.lower()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.cur_kind = "p"
        elif tag == "p":
            self._flush()
        elif tag == "blockquote":
            self._flush()
            self.quote_depth = max(0, self.quote_depth - 1)
        elif tag in ("ul", "ol"):
            self._flush()
            self.ul_depth = max(0, self.ul_depth - 1)
        elif tag == "li":
            self._flush()
            self.in_li = False
            self.cur_kind = "p"
        elif tag in ("b", "strong"):
            self.cur.append("**")
        elif tag in ("i", "em"):
            self.cur.append("*")
        elif tag == "a":
            href = self.link_stack.pop() if self.link_stack else ""
            self.cur.append("](%s)" % href)

    def handle_data(self, data):
        if self.skip:
            return
        self.cur.append(data.replace("\r", ""))

    def render(self):
        """把块序列渲染成 Markdown 文本。"""
        self._flush()          # 兜底：收尾未触发的剩余 inline 内容
        out = []
        prev_kind = None
        for kind, text in self.blocks:
            if kind == "h2":
                text = "## " + text
            elif kind == "h3":
                text = "### " + text
            elif kind == "h4":
                text = "#### " + text
            elif kind == "li":
                text = text
            if out:
                if kind == "li" and prev_kind == "li":
                    out.append(text)
                else:
                    out.append("")
                    out.append(text)
            else:
                out.append(text)
            prev_kind = kind
        return "\n".join(out).strip()


def to_md(html_fragment):
    c = BlockConverter()
    c.feed(html_fragment)
    c.close()
    return c.render()


# ---------------------------------------------------------------- 各来源正文提取
def gamatomic_body(html):
    """GamAtomic：<article> 内 h2/h3 引言 + interview-question/answer div。"""
    start = html.find("<article")
    art, _ = extract_balanced(html, start)

    # 副标题 h2 与导读 summary（summary 在 <section class="article__summary">）
    h2 = re.search(r"<h2>(.*?)</h2>", art, re.S)
    summary = re.search(r'<section class="article__summary">(.*?)</section>', art, re.S)
    parts = []
    if h2:
        parts.append("### " + to_md(h2.group(1)))
    if summary:
        parts.append(to_md(summary.group(1)))

    # 每个 section.article__paragraph
    sec_pat = re.compile(r'<section class="article__paragraph">(.*?)</section>', re.S)
    for sec in sec_pat.findall(art):
        block = []
        h3 = re.search(r"<h3>(.*?)</h3>", sec, re.S)
        if h3:
            block.append("### " + to_md(h3.group(1)))
        # publication__text 内的 Q/A div 与插图
        text_start = sec.find('<div class="publication__text">')
        if text_start >= 0:
            pubtext, _ = extract_balanced(sec, text_start)
            # 按顺序扫描：interview-question / interview-answer / 其他(插图)
            pos = 0
            for m in re.finditer(
                r'<div class="interview-(question|answer)">', pubtext):
                if m.start() > pos:
                    frag = pubtext[pos:m.start()]
                    extra = to_md(frag)
                    if extra:
                        block.append(extra)
                inner, close_after = extract_balanced(pubtext, m.start())
                kind = m.group(1)
                # 说话人加粗（answer 内 <span class="interview-speaker">X</span>）
                inner2 = re.sub(
                    r'<span class="interview-speaker">(.*?)</span>',
                    r"<b>\1:</b> ", inner, flags=re.S)
                txt = to_md(inner2)
                if kind == "question":
                    block.append("**Q:** " + txt)
                else:
                    block.append("**A:** " + txt)
                pos = close_after
            if pos < len(pubtext):
                extra = to_md(pubtext[pos:])
                if extra:
                    block.append(extra)
        if block:
            parts.append("\n\n".join(block))
    return "\n\n".join(parts)


def offtherpg_body(html):
    """offtherpg：<div id="interview"> 内 h2(问题) + p(回答)。"""
    start = html.find('<div id="interview"')
    if start < 0:
        start = html.find('id="interview"')
        if start < 0:
            raise ValueError("找不到 #interview 容器")
        start = html.rfind("<div", 0, start)
    inner, _ = extract_balanced(html, start)
    return to_md(inner)


def tumblr_15th_body(html):
    """fronomeeps 15 周年：.post 内 .title + .copy。"""
    title = re.search(r'<div class="title">(.*?)</div>', html, re.S)
    start = html.find('<div class="copy">')
    if start < 0:
        raise ValueError("找不到 .copy 容器")
    copy, _ = extract_balanced(html, start)
    body = to_md(copy)
    if title:
        body = "### " + to_md(title.group(1)) + "\n\n" + body
    return body


def tumblr_classic_body(html):
    """经典访谈：.post.loading 内的 h3 + blockquote。"""
    start = html.find('<div class="post loading">')
    if start < 0:
        raise ValueError("找不到 .post.loading 容器")
    post, _ = extract_balanced(html, start)
    h3 = re.search(r"<h3>(.*?)</h3>", post, re.S)
    bq_start = post.find("<blockquote>")
    parts = []
    if h3:
        parts.append("### " + to_md(h3.group(1)))
    if bq_start >= 0:
        inner, _ = extract_balanced(post, bq_start)
        parts.append(to_md(inner))
    else:
        # 无 blockquote 时取 Posted on 之前的全部
        cut = post.find("Posted on")
        parts.append(to_md(post[:cut] if cut > 0 else post))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- 元数据
JOBS = [
    dict(
        raw="gamatomic_off.html", out="gamatomic_2025_off_interview.md",
        title="Interview with Mortis Ghost — OFF (GamAtomic, 2025 Remaster)",
        url="https://www.gamatomic.com/interviews/13448/off",
        date="2025-08-18",
        extractor=gamatomic_body,
    ),
    dict(
        raw="offtherpg_nightmargin.html", out="offtherpg_nightmargin_interview.md",
        title="Nightmargin talks about the soundtrack and RPGmaker (OFF)",
        url="https://offtherpg.com/interviews/nightmargin/",
        date="2025-04-03",
        extractor=offtherpg_body,
    ),
    dict(
        raw="offtherpg_quinn-k.html", out="offtherpg_quinn_k_interview.md",
        title="Quinn K. talks localization and game dev! (OFF)",
        url="https://offtherpg.com/interviews/quinn-k/",
        date="2025-02-27",
        extractor=offtherpg_body,
    ),
    dict(
        raw="offtherpg_morusque.html", out="offtherpg_morusque_interview.md",
        title="Morusque, how did you discover OFF?",
        url="https://offtherpg.com/interviews/morusque/",
        date="2025-02-06",
        extractor=offtherpg_body,
    ),
    dict(
        raw="offtherpg_tobyfox.html", out="offtherpg_tobyfox_interview.md",
        title="Toby Fox, how has OFF influenced you?",
        url="https://offtherpg.com/interviews/tobyfox/",
        date="2025-01-23",
        extractor=offtherpg_body,
    ),
    dict(
        raw="tumblr_15th.html", out="off_15th_anniversary_stream_notes.md",
        title="Abriged text of OFF's 15th anniversary stream! (fan transcript)",
        url="https://fronomeeps.tumblr.com/post/722598150455640064/abriged-text-of-offs-15th-anniversary-stream",
        date="2023-07-12",
        extractor=tumblr_15th_body,
    ),
    dict(
        raw="tumblr_classic.html", out="mortis_ghost_coldwood_text_interview.md",
        title="Text For Interview of Mortis Ghost and Alias Conrad Coldwood",
        url="https://brainplaguerewind.tumblr.com/post/150232549905/text-for-interview-of-mortis-ghost-and-alias",
        date="2016-09-10",
        extractor=tumblr_classic_body,
    ),
]

HEADER = """# {title}
- 来源: {url}
- 日期: {date}
- 语言: English

## 中文要点摘要
{summary}

## 全文
{body}
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for job in JOBS:
        raw_path = os.path.join(RAW, job["raw"])
        if not os.path.exists(raw_path):
            print("!! 缺失原始文件: %s" % job["raw"], file=sys.stderr)
            continue
        with open(raw_path, encoding="utf-8", errors="replace") as f:
            html = f.read()
        body = job["extractor"](html)
        md = HEADER.format(
            title=job["title"], url=job["url"], date=job["date"],
            summary="- (待补)", body=body)
        out_path = os.path.join(OUT, job["out"])
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        size = os.path.getsize(out_path)
        total += size
        print("%-42s %8d bytes  (%d chars)" % (job["out"], size, len(md)))
    print("total bytes: %d" % total)


if __name__ == "__main__":
    main()
