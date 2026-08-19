# -*- coding: utf-8 -*-
"""
Tumblr 老版 API 抓取共用工具
兼容两种响应格式：
  A: var tumblr_api_read = {JSON};
  B: tumblr_api_read([{JSON}]);   (JSONP 数组)
所有请求走本地代理 127.0.0.1:7897，礼貌限速。
"""
import csv
import json
import os
import random
import re
import time

import requests

PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
IMG_SNIFF = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]


def _sniff_webp(data):
    return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _sniff_avif(data):
    # ISO BMFF: 前 12 字节内出现 "ftypavif" / "ftypavis"
    return b"ftypavif" in data[:16] or b"ftypavis" in data[:16]


def make_session():
    s = requests.Session()
    s.proxies.update(PROXY)
    s.headers.update(HEADERS)
    return s


def parse_tumblr_response(text):
    """解析 Tumblr 老版 API 响应，返回 JSON 字典。"""
    text = text.strip()
    # 去掉 "var tumblr_api_read = " 前缀
    if text.startswith("var tumblr_api_read"):
        text = text[len("var tumblr_api_read"):].lstrip()
        if text.startswith("="):
            text = text[1:].lstrip()
    # 兼容 JSONP 数组包裹 "tumblr_api_read([...])"
    if text.startswith("tumblr_api_read("):
        text = text[len("tumblr_api_read("):]
        if text.endswith(")"):
            text = text[:-1]
    text = text.rstrip()
    while text.endswith(";"):
        text = text[:-1].rstrip()
    return json.loads(text)


def fetch_json(session, url, max_retries=5):
    """带礼貌退避的 GET，返回 JSON 字典；失败返回 None。"""
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code in (429, 403):
                wait = 10 * (attempt + 1)
                print(f"  [!] HTTP {r.status_code} @ {url} — 退避 {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return parse_tumblr_response(r.text)
        except (requests.RequestException, ValueError) as e:
            wait = 3 * (attempt + 1)
            print(f"  [!] 请求失败 ({e}) — {wait}s 后重试")
            time.sleep(wait)
    return None


def polite_sleep():
    """每请求间隔 0.8~1.2 秒。"""
    time.sleep(random.uniform(0.8, 1.2))


def post_photo_urls(post):
    """从帖子对象中提取最大尺寸的图片 URL 列表（1280 优先）。"""
    def best(p):
        best_size, best_url = -1, None
        for k, v in p.items():
            if k.startswith("photo-url-") and v:
                m = re.search(r"(\d+)\s*$", k)
                size = int(m.group(1)) if m else 0
                if size > best_size:
                    best_size, best_url = size, v
        return best_url

    urls = []
    for p in post.get("photos") or []:
        u = best(p)
        if u:
            urls.append(u)
    # 某些旧帖子把图片 URL 直接放在帖子顶层
    if not urls:
        u = best(post)
        if u:
            urls.append(u)
    return urls


def extract_body_images(post):
    """从 regular-body HTML 中提取图片 URL（srcset 选最大宽度，回退 src）。
    这两个博客的图片都嵌在正文里，而非 photos 数组。"""
    body = post.get("regular-body") or ""
    urls = []
    for m in re.finditer(r"<img[^>]+>", body):
        tag = m.group(0)
        best, best_w = None, -1
        ss = re.search(r'srcset="([^"]+)"', tag)
        if ss:
            for part in ss.group(1).split(","):
                part = part.strip()
                bits = part.rsplit(" ", 1)
                u, w = bits[0], 0
                if len(bits) == 2 and bits[1].endswith("w"):
                    try:
                        w = int(bits[1][:-1])
                    except ValueError:
                        w = 0
                if w > best_w:
                    best_w, best = w, u
        if best is None:
            sm = re.search(r'src="([^"]+)"', tag)
            if sm:
                best = sm.group(1)
        if best:
            urls.append(best)
    return urls


def collect_image_urls(post):
    """合并 photos 数组 + 正文 img 的最大尺寸 URL，去重保序。"""
    urls = post_photo_urls(post) + extract_body_images(post)
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def strip_html(text):
    """去除 HTML 标签并反转义实体。"""
    text = re.sub(r"<[^>]+>", "", text or "")
    return html_unescape(text)


def html_unescape(text):
    import html as _html
    return _html.unescape(text)


def sniff_image(data):
    """按文件头判断图片格式，返回 (ext, ok)。"""
    if not data:
        return None, False
    for magic, ext in IMG_SNIFF:
        if data.startswith(magic):
            return ext, True
    if _sniff_webp(data):
        return "webp", True
    if _sniff_avif(data):
        return "avif", True
    return None, False


def download_image(session, url, dest, retries=2):
    """下载图片并校验文件头。成功返回 ext（png/jpg/gif），失败抛异常。"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            data = r.content
            ext, ok = sniff_image(data)
            if not ok:
                raise ValueError("文件头校验失败或 0 字节")
            with open(dest, "wb") as f:
                f.write(data)
            return ext
        except Exception as e:
            last_err = e
            if attempt < retries:
                print(f"  [!] 下载失败 {url} ({e}) — 重试 {attempt + 1}/{retries}")
                time.sleep(2 * (attempt + 1))
    raise last_err


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_summary(path, src_url, total_posts, downloaded, formats, extra_notes):
    """写 _summary.md。formats: dict[ext] = 数量。"""
    fmt_lines = "、".join(f"{k}: {v} 张" for k, v in sorted(formats.items())) or "无"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {os.path.basename(os.path.dirname(path))} 图片抓取汇总\n\n")
        f.write(f"- 来源: {src_url}\n")
        f.write(f"- 抓取帖子数: {total_posts}\n")
        f.write(f"- 下载图片数: {downloaded}\n")
        f.write(f"- 图片格式分布: {fmt_lines}\n")
        f.write("- 注意事项:\n")
        for note in extra_notes:
            f.write(f"  - {note}\n")
