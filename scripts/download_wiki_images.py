# -*- coding: utf-8 -*-
"""
下载 OFF Wiki (off.fandom.com) 的图片到 art/wiki/。
用法: python download_wiki_images.py
输入: ../art/wiki/_image_list.csv  (由 fetch_wiki_image_list.py 生成)
输出: ../art/wiki/<原文件名>         下载的图片
      ../art/wiki/_source_list.csv  文件名|原始URL|wiki文件名
      ../art/wiki/_failed.csv       下载失败记录
"""
import csv
import os
import re
import sys
import time
import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "wiki")

# Windows 非法文件名字符替换为下划线
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
EXT_FROM_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
}


def sanitize_name(name):
    """清洗文件名：去 Windows 非法字符、去首尾空白。"""
    name = _INVALID.sub("_", name).strip()
    name = re.sub(r"_{2,}", "_", name)
    return name[:200]


def download_one(session, url, path, name):
    """下载单张图片，返回 (状态, 信息)。状态: ok / skipped / failed"""
    for attempt in range(3):  # 首次 + 重试 2 次
        try:
            r = session.get(url, timeout=30)
            if r.status_code in (429, 403):
                wait = 5 * (attempt + 1)
                print(f"    HTTP {r.status_code} on {name}, sleep {wait}s ...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return "failed", f"HTTP {r.status_code}"
            ctype = (r.headers.get("Content-Type") or "").lower()
            if not ctype.startswith("image/"):
                return "skipped", f"not an image (Content-Type={ctype})"
            if not os.path.splitext(path)[1]:
                path += EXT_FROM_MIME.get(ctype, ".img")
            with open(path, "wb") as f:
                f.write(r.content)
            return "ok", ctype
        except requests.RequestException as e:
            if attempt == 2:
                return "failed", str(e)[:120]
            time.sleep(2 * (attempt + 1))
    return "failed", "unreachable"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    csv_in = os.path.join(OUT_DIR, "_image_list.csv")
    if not os.path.exists(csv_in):
        print(f"缺少清单: {csv_in}，请先运行 fetch_wiki_image_list.py")
        sys.exit(1)

    rows = list(csv.reader(open(csv_in, encoding="utf-8-sig")))
    items = [(r[0], r[1]) for r in rows[1:] if len(r) >= 2 and r[0] and r[1]]
    print(f"待下载条目: {len(items)}")

    session = requests.Session()
    session.proxies = PROXY
    session.headers.update(HEADERS)

    src_out = os.path.join(OUT_DIR, "_source_list.csv")
    fail_out = os.path.join(OUT_DIR, "_failed.csv")
    src_f = open(src_out, "w", encoding="utf-8-sig", newline="")
    fail_f = open(fail_out, "w", encoding="utf-8-sig", newline="")
    sw = csv.writer(src_f)
    fw = csv.writer(fail_f)
    sw.writerow(["filename", "url", "wiki_filename"])
    fw.writerow(["wiki_filename", "url", "error"])

    ok = skipped = failed = existed = 0
    for i, (wiki_name, url) in enumerate(items, 1):
        fname = sanitize_name(wiki_name)
        path = os.path.join(OUT_DIR, fname)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            existed += 1
            sw.writerow([fname, url, wiki_name])
            continue
        status, info = download_one(session, url, path, wiki_name)
        if status == "ok":
            ok += 1
            sw.writerow([os.path.basename(path), url, wiki_name])
        elif status == "skipped":
            skipped += 1
            print(f"  [{i}/{len(items)}] 跳过(非图片): {wiki_name}")
        else:
            failed += 1
            fw.writerow([wiki_name, url, info])
            print(f"  [{i}/{len(items)}] 失败: {wiki_name} -> {info}")
        if i % 25 == 0:
            print(f"  进度: {i}/{len(items)} (ok={ok}, existed={existed}, skip={skipped}, fail={failed})")
        time.sleep(0.7)  # 礼貌间隔

    src_f.close()
    fail_f.close()
    print(f"\n完成: 新下载={ok}, 已存在跳过={existed}, 非图片跳过={skipped}, 失败={failed}")
    print(f"来源清单: {src_out}")
    print(f"失败清单: {fail_out}")


if __name__ == "__main__":
    main()
