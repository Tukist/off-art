# -*- coding: utf-8 -*-
"""
下载 Fangamer 官网的 OFF 周边/收藏版内容物图片到 art/merch/
来源：
  - https://www.fangamer.com/collections/off           （周边集合页）
  - https://www.fangamer.com/products/off-collectors-edition-game-nintendo-switch （收藏版详情页）
"""
import os
import re
import sys
import time
import csv

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "art", "merch")
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Referer": "https://www.fangamer.com/"}

# 排除的噪音图
EXCLUDE = re.compile(r"(logo|flag-|footer|header|payment|icon|shadow|blog-post-thumbnail|subscribe|favicon)", re.I)

# 高分辨率替换规则：_360x360.png -> 去掉尺寸后缀拿原图
def upscale(url: str) -> list:
    """返回尝试的候选 URL 列表（优先高清）"""
    cands = []
    if "_360x360.png" in url:
        cands.append(url.replace("_360x360.png", ".png"))
    if "?crop=center&height=600" in url:
        # 900px 版本已经是高清，直接用
        cands.append(url)
    cands.append(url)
    return cands

def main():
    html_files = sys.argv[1:]
    urls = set()
    for hf in html_files:
        with open(hf, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        for m in re.finditer(r'src="(//?cdn\.shopify\.com[^"]+?\.(?:png|jpe?g|webp))[^"]*"', html):
            u = m.group(1)
            if u.startswith("//"):
                u = "https:" + u
            # 去掉查询参数拿到基础 URL，过滤低清缩略图
            if "width=300" in m.group(0):
                continue
            if EXCLUDE.search(u):
                continue
            urls.add(u)

    print(f"共 {len(urls)} 个候选图片 URL")
    rows = []
    ok = fail = 0
    for i, u in enumerate(sorted(urls)):
        fname = u.split("/")[-1].split("?")[0]
        fname = re.sub(r"_360x360", "", fname)
        fname = "merch_" + fname
        dest = os.path.join(OUT, fname)
        saved = False
        for cand in upscale(u):
            try:
                r = requests.get(cand, headers=HEADERS, timeout=30)
                if r.status_code == 200 and len(r.content) > 500:
                    with open(dest, "wb") as f:
                        f.write(r.content)
                    rows.append((fname, cand, u))
                    ok += 1
                    saved = True
                    break
            except Exception as e:
                pass
        if not saved:
            fail += 1
            print(f"  [FAIL] {u}")
        time.sleep(0.6)

    with open(os.path.join(OUT, "_source_list.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["文件名", "下载URL", "页面原始URL"])
        w.writerows(rows)
    print(f"完成：成功 {ok}，失败 {fail}，清单 {os.path.join(OUT, '_source_list.csv')}")

if __name__ == "__main__":
    main()
