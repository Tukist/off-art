# -*- coding: utf-8 -*-
"""
将 art/wiki/ 下所有图片重下为 CDN 原始格式（URL 追加 &format=original）。
原因: Fandom CDN 对任何 UA 都返回 WebP 转码，导致 .jpg/.png 文件中是 WebP 字节；
      format=original 可拿到上传的原始文件。仅重下文件头仍是 RIFF(WebP) 的文件。
用法: python redownload_wiki_images_original.py
输出: ../art/wiki/<同文件名> ；../art/wiki/_redownload_failed.csv
"""
import csv
import os
import time
import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art", "wiki")

# 磁盘上带错误扩展名的文件 -> 应改为的真实扩展名（format=original 后的实际格式）
RENAME = {
    "OFF_10th_Year_Anniversary_Livestream.webp": "OFF_10th_Year_Anniversary_Livestream.jpg",
    "OFF_for_Nintendo_Switch_and_Steam_Announcement_Trailer.webp": "OFF_for_Nintendo_Switch_and_Steam_Announcement_Trailer.jpg",
    "Off_15th_anniversary_stream.webp": "Off_15th_anniversary_stream.jpg",
    "Wiki-background.webp": "Wiki-background.png",
}


def is_webp(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"RIFF"
    except OSError:
        return False


def main():
    csv_in = os.path.join(OUT_DIR, "_source_list.csv")
    rows = list(csv.reader(open(csv_in, encoding="utf-8-sig")))
    items = [(r[0], r[1]) for r in rows[1:] if len(r) >= 2 and r[0] and r[1]]
    print(f"清单条目: {len(items)}")

    session = requests.Session()
    session.proxies = PROXY
    session.headers.update(HEADERS)
    fail_f = open(os.path.join(OUT_DIR, "_redownload_failed.csv"), "w", encoding="utf-8-sig", newline="")
    fw = csv.writer(fail_f)
    fw.writerow(["filename", "url", "error"])

    ok = skipped = failed = still_webp = 0
    for i, (fname, url) in enumerate(items, 1):
        path = os.path.join(OUT_DIR, fname)
        if not os.path.exists(path) or not is_webp(path):
            skipped += 1  # 已是原始格式或文件缺失(缺失交给日志)
            continue
        uo = url + ("&" if "?" in url else "?") + "format=original"
        status = "ok"
        for attempt in range(3):
            try:
                r = session.get(uo, timeout=30)
                if r.status_code in (429, 403):
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    status = f"HTTP {r.status_code}"
                    break
                if not (r.headers.get("Content-Type") or "").startswith("image/"):
                    status = "not image"
                    break
                with open(path, "wb") as f:
                    f.write(r.content)
                if is_webp(path):
                    still_webp += 1  # 该文件在 wiki 上就是 webp，保留
                break
            except requests.RequestException as e:
                if attempt == 2:
                    status = str(e)[:120]
                else:
                    time.sleep(2 * (attempt + 1))
        if status == "ok":
            ok += 1
        else:
            failed += 1
            fw.writerow([fname, uo, status])
            print(f"  失败: {fname} -> {status}")
        if i % 50 == 0:
            print(f"  进度: {i}/{len(items)} (ok={ok}, skip={skipped}, fail={failed}, still_webp={still_webp})")
        time.sleep(0.6)

    fail_f.close()

    # 修正 4 个错误扩展名文件名
    for old, new in RENAME.items():
        oldp, newp = os.path.join(OUT_DIR, old), os.path.join(OUT_DIR, new)
        if os.path.exists(oldp) and not os.path.exists(newp):
            os.rename(oldp, newp)
            print(f"改名: {old} -> {new}")

    print(f"\n完成: 重下={ok}, 已原始跳过={skipped}, 失败={failed}, 仍为webp={still_webp}")
    print(f"失败清单: {os.path.join(OUT_DIR, '_redownload_failed.csv')}")


if __name__ == "__main__":
    main()
