# -*- coding: utf-8 -*-
"""
修补 4 个特殊条目（3 个流媒体海报 + Wiki 背景图）：
1. 用 format=original 下载原始字节（它们的 CSV url 在重下脚本启动时为空，未参与批量重下）
2. 修正扩展名（.webp -> .jpg/.png）
3. 更新 _source_list.csv 中的文件名与 url
用法: python patch_wiki_special_entries.py
"""
import csv
import os
import time
import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "wiki")

# 磁盘旧名(webp) -> (最终文件名, 原始 URL)
SPECIALS = {
    "OFF_10th_Year_Anniversary_Livestream.webp": (
        "OFF_10th_Year_Anniversary_Livestream.jpg",
        "https://static.wikia.nocookie.net/offgame/images/e/e5/OFF_10th_Year_Anniversary_Livestream/revision/latest?cb=20241224203219",
    ),
    "OFF_for_Nintendo_Switch_and_Steam_Announcement_Trailer.webp": (
        "OFF_for_Nintendo_Switch_and_Steam_Announcement_Trailer.jpg",
        "https://static.wikia.nocookie.net/offgame/images/6/6d/OFF_for_Nintendo_Switch_and_Steam_Announcement_Trailer/revision/latest?cb=20241224065714",
    ),
    "Off_15th_anniversary_stream.webp": (
        "Off_15th_anniversary_stream.jpg",
        "https://static.wikia.nocookie.net/offgame/images/8/8a/Off_15th_anniversary_stream/revision/latest?cb=20241224203238",
    ),
    "Wiki-background.webp": (
        "Wiki-background.png",
        "https://static.wikia.nocookie.net/offgame/images/5/50/Wiki-background/revision/latest?cb=20121222233208",
    ),
}


def is_webp(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"RIFF"
    except OSError:
        return False


def main():
    session = requests.Session()
    session.proxies = PROXY
    session.headers.update(HEADERS)
    for old, (new, url) in SPECIALS.items():
        newp = os.path.join(OUT_DIR, new)
        oldp = os.path.join(OUT_DIR, old)
        uo = url + "&format=original"
        ok = False
        for attempt in range(3):
            try:
                r = session.get(uo, timeout=30)
                if r.status_code in (429, 403):
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code == 200 and (r.headers.get("Content-Type") or "").startswith("image/"):
                    with open(newp, "wb") as f:
                        f.write(r.content)
                    ok = True
                    break
                print(f"  {new}: HTTP {r.status_code}")
                break
            except requests.RequestException as e:
                if attempt == 2:
                    print(f"  {new}: 失败 {e}")
                else:
                    time.sleep(2 * (attempt + 1))
        if ok:
            if os.path.exists(oldp) and os.path.abspath(oldp) != os.path.abspath(newp):
                os.remove(oldp)
            print(f"  OK {new} ({os.path.getsize(newp)} bytes, webp={is_webp(newp)})")
        time.sleep(0.6)

    # 更新 CSV 文件名/url
    csvp = os.path.join(OUT_DIR, "_source_list.csv")
    rows = list(csv.reader(open(csvp, encoding="utf-8-sig")))
    name_to_url = {new: url for old, (new, url) in SPECIALS.items()}
    changed = 0
    for r in rows[1:]:
        if len(r) >= 1 and r[0] in name_to_url:
            r[0] = r[0]  # 保持
        if len(r) >= 2 and r[0] in name_to_url and not r[1]:
            r[1] = name_to_url[r[0]]
            changed += 1
    # 旧 webp 名行 -> 新名
    for old, (new, url) in SPECIALS.items():
        for r in rows[1:]:
            if len(r) >= 1 and r[0] == old:
                r[0] = new
                if len(r) >= 2:
                    r[1] = url
                changed += 1
    with open(csvp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r[:3])
    print(f"CSV 更新行数: {changed}")


if __name__ == "__main__":
    main()
