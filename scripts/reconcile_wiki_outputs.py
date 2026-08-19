# -*- coding: utf-8 -*-
"""
协调脚本：整理两个并发代理产生的 wiki 产出。

1. 重建 wiki/_index.md：扫描 wiki/*.md（排除 _index.md），覆盖全部已存页面，
   每页一行（文件名 + 首段一句话说明）；缺失页面（Almighty、Unproductive_Fun_Time）
   单独列在末尾。
2. 重建 art/wiki/_source_list.csv：扫描 art/wiki/ 磁盘文件（排除 _ 前缀元数据），
   结合 scripts/wiki_allfiles_list.json（全站 504 条 API 清单）补上 URL，
   输出列：本地文件名 | 原始URL | wiki文件名。
"""
import csv
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = "D:/pythoncode/off-art"
WIKI_DIR = os.path.join(BASE, "wiki")
ART_DIR = os.path.join(BASE, "art", "wiki")
RAW_LIST = os.path.join(BASE, "scripts", "wiki_allfiles_list.json")
SRC_CSV = os.path.join(ART_DIR, "_source_list.csv")
IDX = os.path.join(WIKI_DIR, "_index.md")

MISSING_NOTE = {
    "Almighty": "wiki 上无该页面（概念散见于其他页面，如 OFF 世界观部分）",
    "Unproductive_Fun_Time": "该名称是 OFF 开发团队名（Mortis Ghost + Alias Conrad Coldwood），wiki 无此页面",
}

# 磁盘上不作为"图片来源"统计的元数据文件
META = {"_source_list.csv", "_failed.csv", "_image_list.csv", "_image_list.json"}


def load_api_list():
    """返回 {wiki原始文件名: {url, name, size}}，含全部 504 条。"""
    with open(RAW_LIST, encoding="utf-8") as f:
        return {e["name"]: e for e in json.load(f)}


def sanitize(name):
    stem, ext = os.path.splitext(name)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    safe = safe.strip("._")
    if not safe:
        safe = "image"
    return safe[:100] + ext


def summarize(text):
    para = re.sub(r"\[\d+\]", "", text.strip())
    para = re.sub(r"\s+", " ", para)
    if not para:
        return "(无正文)"
    end = min(len(para), 160)
    cut = max(para.rfind(".", 0, end), para.rfind("。", 0, end))
    if cut > 25:
        para = para[: cut + 1]
    else:
        para = para[:end] + ("…" if len(para) > end else "")
    return para


def rebuild_index():
    files = sorted(f for f in os.listdir(WIKI_DIR)
                   if f.endswith(".md") and f not in ("_index.md",))
    rows = []
    for fn in files:
        with open(os.path.join(WIKI_DIR, fn), encoding="utf-8") as f:
            text = f.read()
        body = re.sub(r"^#\s+.*\n+", "", text, count=1)
        rows.append((fn, summarize(body)))
    with open(IDX, "w", encoding="utf-8") as f:
        f.write("# OFF Wiki 设定页面索引\n\n")
        f.write(f"> 来源: https://off.fandom.com/wiki/ （经代理抓取，action=parse 渲染文本）\n")
        f.write(f"> 共 {len(rows)} 页。生成时间: 2026-08-19（协调脚本 rebuild）\n\n")
        f.write("| 文件 | 内容概要 |\n")
        f.write("|------|----------|\n")
        for fn, s in rows:
            f.write(f"| [{fn}]({fn}) | {s} |\n")
        f.write("\n## wiki 上不存在的页面\n\n")
        for name, why in MISSING_NOTE.items():
            f.write(f"- **{name}**：{why}\n")
    return len(rows)


def rebuild_source_csv():
    api = load_api_list()
    files = sorted(f for f in os.listdir(ART_DIR)
                   if os.path.isfile(os.path.join(ART_DIR, f)) and f not in META)
    rows = []
    no_url = 0
    for fn in files:
        info = api.get(fn)
        if info is None:
            info = api.get(fn.replace("__", "_"))  # 兜底：双下划线变体
        if info is None:
            # 反向：找 sanitize 后等于该名的条目
            info = next((e for e in api.values() if sanitize(e["name"]) == fn), None)
        if info:
            rows.append((fn, info["url"], info["name"]))
        else:
            rows.append((fn, "N/A(不在API清单)", fn))
            no_url += 1
    with open(SRC_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["local_filename", "url", "wiki_filename"])
        w.writerows(rows)
    return len(rows), no_url


if __name__ == "__main__":
    n_idx = rebuild_index()
    print(f"重建 _index.md：{n_idx} 页")
    n_csv, no_url = rebuild_source_csv()
    print(f"重建 _source_list.csv：{n_csv} 行（无URL的 {no_url} 行）")
