# -*- coding: utf-8 -*-
"""
扫描 ../wiki/ 下所有设定页 md，重新生成 _index.md（含一句话内容概要）。
用法: python generate_wiki_index.py
"""
import os
import re

WIKI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wiki")

# 页面开头常见的样板段落，摘要时跳过
BOILERPLATE = ("spoiler warning", "this article is a stub", "contents", "this article contains important details")


def summarize(text):
    """从正文第一个有意义的段落提取一句话概要（≤200 字）。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text)]
    for p in paras:
        if not p:
            continue
        low = p.lower()
        if any(low.startswith(b) for b in BOILERPLATE):
            continue
        if len(p) < 30:
            continue
        one = re.sub(r"\s+", " ", p).strip()
        one = re.sub(r"\[\d+\]", "", one)
        end = min(len(one), 200)
        cut = max(one.rfind(".", 0, end), one.rfind("。", 0, end))
        if cut > 40:
            one = one[: cut + 1]
        elif len(one) > end:
            one = one[:end] + "…"
        return one
    # 兜底：取第一个非空行
    for p in paras:
        if p:
            return re.sub(r"\s+", " ", p)[:120]
    return "(无正文)"


def main():
    files = sorted(f for f in os.listdir(WIKI_DIR) if f.endswith(".md") and not f.startswith("_"))
    rows = []
    for fname in files:
        with open(os.path.join(WIKI_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        m = re.match(r"^#\s+(.+)$", content, re.M)
        title = m.group(1).strip() if m else fname[:-3]
        rows.append((fname, title, summarize(content)))

    out = ["# OFF Wiki 设定页面索引", "",
           f"> 来源: https://off.fandom.com/wiki/ (经代理抓取, action=parse 渲染文本, 共 {len(rows)} 页)", "",
           "| 文件 | 页面 | 内容概要 |", "|------|------|----------|"]
    for fname, title, summ in rows:
        summ_esc = summ.replace("|", "\\|")
        out.append(f"| [{fname}]({fname}) | {title} | {summ_esc} |")
    out += ["", "## 抓取失败页面（wiki 上不存在）", "",
            "- Almighty（wiki 无此页面）", "- Unproductive_Fun_Time（wiki 无此页面）", ""]

    path = os.path.join(WIKI_DIR, "_index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"已生成: {path}（{len(rows)} 页）")


if __name__ == "__main__":
    main()
