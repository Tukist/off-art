# -*- coding: utf-8 -*-
"""
抓取 off-art-archive.tumblr.com（Unofficial OFF Art Archive，粉丝整理的官方美术档案）
遍历全部帖子，下载每帖最大尺寸图片到 art/fan/，
输出 _notes.csv / _source_list.csv / _download_failures.csv / _summary.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tumblr_utils import (  # noqa: E402
    make_session, fetch_json, polite_sleep, collect_image_urls,
    download_image, write_csv, write_summary, strip_html,
)

BLOG = "https://off-art-archive.tumblr.com"
OUT = r"D:/pythoncode/off-art/art/fan"
MAX_IMAGES = 900


def main():
    os.makedirs(OUT, exist_ok=True)
    session = make_session()

    notes = []          # post_id | post_url | image_count | post_text
    source_rows = []    # 文件名 | 原始图片URL | 帖子URL
    failures = []       # 文件名 | 原始图片URL | 帖子URL | 错误
    downloaded = 0
    start = 0
    total_posts = 0
    hit_limit = False

    while True:
        url = f"{BLOG}/api/read/json?num=50&start={start}"
        print(f"[页] start={start} url={url}")
        data = fetch_json(session, url)
        if data is None:
            print("  [!] 页面抓取失败，终止分页")
            break
        posts = data.get("posts") or []
        if not posts:
            print("  无更多帖子，分页结束")
            break
        total_posts = data.get("posts-total", total_posts)

        for post in posts:
            if downloaded >= MAX_IMAGES:
                hit_limit = True
                break
            post_id = post.get("id")
            post_url = (post.get("url-with-slug") or post.get("url")
                        or f"{BLOG}/post/{post_id}")
            text = (post.get("regular-body") or post.get("photo-caption")
                    or post.get("quote-text") or "")
            text_plain = strip_html(text).strip()
            photos = collect_image_urls(post)

            saved = 0
            for n, img_url in enumerate(photos, 1):
                if downloaded >= MAX_IMAGES:
                    hit_limit = True
                    break
                fname = f"post_{post_id}_{n:02d}"
                # 幂等续跑：文件已存在则跳过下载，只补记录
                existing = [f for f in os.listdir(OUT)
                            if f.startswith(fname + ".") and not f.endswith(".tmp")]
                if existing:
                    source_rows.append([existing[0], img_url, post_url])
                    saved += 1
                    downloaded += 1
                    continue
                tmp = os.path.join(OUT, fname + ".tmp")
                ext = None
                try:
                    ext = download_image(session, img_url, tmp)
                    final = os.path.join(OUT, f"{fname}.{ext}")
                    os.replace(tmp, final)
                    source_rows.append([os.path.basename(final), img_url, post_url])
                    saved += 1
                    downloaded += 1
                    print(f"  [OK] {os.path.basename(final)}")
                except Exception as e:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                    failures.append([f"{fname}.{ext}" if ext else fname,
                                     img_url, post_url, str(e)])
                    print(f"  [X] {fname} 失败: {e}")
                polite_sleep()

            notes.append([str(post_id), post_url, saved, text_plain[:200]])
            total_posts += 1

        if hit_limit or downloaded >= MAX_IMAGES:
            print(f"  达到上限 {MAX_IMAGES} 张，停止")
            break
        start += 50
        polite_sleep()

    # ---- 输出 CSV ----
    write_csv(os.path.join(OUT, "_notes.csv"),
              ["post_id", "post_url", "image_count", "post_text"],
              notes)
    write_csv(os.path.join(OUT, "_source_list.csv"),
              ["文件名", "原始图片URL", "帖子URL"],
              source_rows)
    write_csv(os.path.join(OUT, "_download_failures.csv"),
              ["文件名", "原始图片URL", "帖子URL", "错误"],
              failures)

    # ---- 格式分布 ----
    formats = {}
    for row in source_rows:
        ext = os.path.splitext(row[0])[1].lstrip(".").lower()
        formats[ext] = formats.get(ext, 0) + 1

    extra = [
        f"API 报告帖子总数: {total_posts if total_posts else '未知'}（实际遍历 {len(notes)} 帖）",
        f"下载失败 {len(failures)} 张，见 _download_failures.csv",
        f"文件名格式 post_<帖子id>_<序号>，扩展名按实际文件头判断",
        "失败重试策略: 每张图最多重试 2 次，仍失败记入 CSV",
    ]
    if hit_limit:
        extra.append(f"⚠ 达到 {MAX_IMAGES} 张上限，未抓完，后续可调大 MAX_IMAGES 续抓")
    write_summary(os.path.join(OUT, "_summary.md"), BLOG, len(notes),
                  downloaded, formats, extra)

    print("=" * 50)
    print(f"完成: 遍历 {len(notes)} 帖, 下载 {downloaded} 张, 失败 {len(failures)} 张")
    print(f"CSV: {os.path.join(OUT, '_notes.csv')} / {os.path.join(OUT, '_source_list.csv')}")
    if failures:
        print("失败明细:")
        for frow in failures:
            print("  ", frow)


if __name__ == "__main__":
    main()
