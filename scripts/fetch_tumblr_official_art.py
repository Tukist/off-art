# -*- coding: utf-8 -*-
"""
抓取 mortisghost.tumblr.com（作者 Mortis Ghost 博客 "The Jurnal"）中与 OFF 相关的帖子
- 筛选: tag 含 "off"（不区分大小写）或 正文/标题提到 OFF/Batter/Zacharie/Judge/Elsen
- 下载命中帖图片到 art/official/，文件名 mortis_post_<post_id>_<n>.<ext>
- 命中帖正文存 _mortis_posts.md，另输出 _source_list.csv / _download_failures.csv / _summary.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tumblr_utils import (  # noqa: E402
    make_session, fetch_json, polite_sleep, collect_image_urls, strip_html,
    download_image, write_csv, write_summary,
)

BLOG = "https://mortisghost.tumblr.com"
OUT = r"D:/pythoncode/off-art/art/official"
MAX_MATCHED_POSTS = 150

# OFF 相关关键词（正文/标题，忽略大小写，单词边界）
KW_RE = re.compile(
    r"\boff\b|\bbatter\b|\bzacharie\b|\bjudge\b|\belsen\b",
    re.IGNORECASE,
)


def is_off_post(post):
    """判断帖子是否与 OFF 相关。"""
    # 规则 1: tag 含 off（不区分大小写）；用 \boff\b 避免 coffee/staff 等误判，
    # 同时兼容 "off-game" 这类带连字符的 tag
    for t in post.get("tags") or []:
        tl = t.lower()
        if re.search(r"\boff\b", tl) or tl.startswith("off-") or tl.startswith("off_"):
            return True
    # 规则 2: 标题或正文提到关键词
    title = post.get("title") or ""
    body = strip_html(post.get("regular-body") or "").strip()
    if KW_RE.search(title + "\n" + body):
        return True
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    session = make_session()

    source_rows = []   # 文件名 | 原始图片URL | 帖子URL
    failures = []      # 文件名 | 原始图片URL | 帖子URL | 错误
    md_blocks = []     # 命中帖正文（英文原文）
    downloaded = 0
    matched = 0
    start = 0
    total_posts = 0

    while matched < MAX_MATCHED_POSTS:
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
            if matched >= MAX_MATCHED_POSTS:
                break
            if not is_off_post(post):
                continue
            matched += 1
            post_id = post.get("id")
            post_url = (post.get("url-with-slug") or post.get("url")
                        or f"{BLOG}/post/{post_id}")
            date = post.get("date-gmt") or post.get("date") or "未知日期"
            body = strip_html(post.get("regular-body") or "").strip()
            title = (post.get("title") or "").strip()

            # 正文存档（英文原文）
            block = [f"## {date} — {post_url}", ""]
            if title:
                block.append(f"**{title}**")
                block.append("")
            block.append(body if body else "（无正文）")
            block.append("")
            block.append("---")
            block.append("")
            md_blocks.append("\n".join(block))

            # 下载图片
            photos = collect_image_urls(post)
            saved = 0
            for n, img_url in enumerate(photos, 1):
                fname = f"mortis_post_{post_id}_{n:02d}"
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
            print(f"  [帖] matched={matched} id={post_id} 图片={saved}/{len(photos)}")

        if matched >= MAX_MATCHED_POSTS:
            print(f"  命中上限 {MAX_MATCHED_POSTS} 帖，停止")
            break
        start += 50
        polite_sleep()

    # ---- 输出 ----
    md_path = os.path.join(OUT, "_mortis_posts.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Mortis Ghost 博客 OFF 相关帖子正文存档\n\n")
        f.write(f"> 来源: {BLOG} ｜ 命中 {matched} 帖（上限 {MAX_MATCHED_POSTS}）\n\n")
        f.write("\n".join(md_blocks))

    write_csv(os.path.join(OUT, "_source_list.csv"),
              ["文件名", "原始图片URL", "帖子URL"], source_rows)
    write_csv(os.path.join(OUT, "_download_failures.csv"),
              ["文件名", "原始图片URL", "帖子URL", "错误"], failures)

    formats = {}
    for row in source_rows:
        ext = os.path.splitext(row[0])[1].lstrip(".").lower()
        formats[ext] = formats.get(ext, 0) + 1

    extra = [
        f"API 报告帖子总数: {total_posts}，命中 OFF 相关帖 {matched} 个",
        f"下载失败 {len(failures)} 张，见 _download_failures.csv",
        "筛选规则: tag 含 off（\boff\b，兼容 off- 前缀）或 正文/标题含 "
        "OFF/Batter/Zacharie/Judge/Elsen 关键词",
        f"命中帖正文（英文原文）已存 {os.path.basename(md_path)}",
    ]
    if matched >= MAX_MATCHED_POSTS:
        extra.append(f"⚠ 达到 {MAX_MATCHED_POSTS} 帖上限，未抓完")
    write_summary(os.path.join(OUT, "_summary.md"), BLOG, matched,
                  downloaded, formats, extra)

    print("=" * 50)
    print(f"完成: 命中 {matched} 帖, 下载 {downloaded} 张, 失败 {len(failures)} 张")
    print(f"正文: {md_path}")
    print(f"CSV: {os.path.join(OUT, '_source_list.csv')}")
    if failures:
        print("失败明细:")
        for frow in failures:
            print("  ", frow)


if __name__ == "__main__":
    main()
