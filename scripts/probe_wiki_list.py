# -*- coding: utf-8 -*-
"""探测 off.fandom.com 全站文件清单：统计总数、按扩展名分类"""
import requests, json, time, collections

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
API = "https://off.fandom.com/api.php"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tif", ".tiff", ".avif", ".apng"}

def get_list(params):
    params.update({"action": "query", "list": "allimages", "ailimit": 500,
                   "aiprop": "url|size|comment", "format": "json"})
    return requests.get(API, params=params, proxies=PROXY, headers=UA, timeout=30).json()

def main():
    entries = []
    params = {}
    page = 0
    while True:
        page += 1
        data = get_list(params)
        items = data.get("query", {}).get("allimages", [])
        entries.extend(items)
        cont = data.get("continue")
        if not cont or "aicontinue" not in cont:
            break
        params["aicontinue"] = cont["aicontinue"]
        time.sleep(0.5)
        if page % 5 == 0:
            print(f"  ... page {page}, total {len(entries)}")
    print(f"总条目数: {len(entries)}")
    ext_counter = collections.Counter()
    for e in entries:
        name = e["name"].lower()
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else "(none)"
        ext_counter[ext] += 1
    for ext, cnt in ext_counter.most_common(20):
        print(f"  {ext}: {cnt}")
    img = [e for e in entries if "." + e["name"].rsplit(".", 1)[-1].lower() in IMG_EXTS]
    print(f"纯图片数: {len(img)}")
    with open("/d/pythoncode/off-art/scripts/wiki_allfiles_list.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)
    print("清单已保存到 scripts/wiki_allfiles_list.json")

if __name__ == "__main__":
    main()
