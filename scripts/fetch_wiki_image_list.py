# -*- coding: utf-8 -*-
"""
抓取 OFF Wiki (off.fandom.com) 全站图片清单（含 URL），保存为 JSON + CSV。
用法: python fetch_wiki_image_list.py
输出: ../art/wiki/_image_list.json  (原始清单)
      ../art/wiki/_image_list.csv   (文件名|原始URL|wiki文件名)
"""
import json
import time
import csv
import os
import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
API = "https://off.fandom.com/api.php"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "wiki")

# 需要过滤掉的非图片扩展名（Fandom 的 allimages 会包含音频/视频/文档）
SKIP_EXTS = {".ogg", ".oga", ".ogv", ".mp3", ".wav", ".webm", ".mp4", ".gif", ".svg", ".pdf", ".flac", ".m4a", ".aac", ".wma"}


def fetch_all_images():
    all_imgs = []
    aicontinue = None
    page = 0
    while True:
        params = {
            "action": "query",
            "list": "allimages",
            "ailimit": "500",
            "aiprop": "url|size|comment",
            "format": "json",
        }
        if aicontinue:
            params["aicontinue"] = aicontinue
        for attempt in range(4):
            try:
                r = requests.get(API, params=params, proxies=PROXY, headers=HEADERS, timeout=30)
                if r.status_code == 429 or r.status_code == 403:
                    wait = 5 * (attempt + 1)
                    print(f"  HTTP {r.status_code}, sleep {wait}s ...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == 3:
                    raise
                print(f"  请求失败: {e}, 重试 {attempt + 1}/4")
                time.sleep(2 * (attempt + 1))
        d = r.json()
        imgs = d.get("query", {}).get("allimages", [])
        all_imgs.extend(imgs)
        page += 1
        print(f"页 {page}: 获取 {len(imgs)} 条, 累计 {len(all_imgs)}")
        cont = d.get("continue")
        if cont and "aicontinue" in cont:
            aicontinue = cont["aicontinue"]
        else:
            break
        time.sleep(0.7)
    return all_imgs


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("开始抓取全站图片清单 ...")
    all_imgs = fetch_all_images()
    print(f"总条目: {len(all_imgs)}")

    # 保存原始 JSON
    json_path = os.path.join(OUT_DIR, "_image_list.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_imgs, f, ensure_ascii=False, indent=1)
    print(f"原始清单已存: {json_path}")

    # 生成 CSV（只保留图片，过滤音频等）
    csv_path = os.path.join(OUT_DIR, "_image_list.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "url", "size", "width", "height", "mime"])
        kept = 0
        for im in all_imgs:
            name = im.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext in SKIP_EXTS:
                continue
            mime = im.get("mime", "")
            if mime and not mime.startswith("image/"):
                continue
            w.writerow([name, im.get("url", ""), im.get("size", 0), im.get("width", 0), im.get("height", 0), mime])
            kept += 1
        print(f"图片条目(过滤后): {kept}")
    print(f"CSV 清单已存: {csv_path}")


if __name__ == "__main__":
    main()
