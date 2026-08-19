# -*- coding: utf-8 -*-
"""
OFF 原声转码 + 曲目清单生成
- 扫描 D:/CloudMusic/off/*.mp3（Alias Conrad Coldwood 原声）
- ffmpeg 转码为 128kbps MP3 到 docs/music/（保持音质与体积平衡）
- mutagen 读取时长，输出 docs/music.json 供播放器嵌入
用法：python scripts/build_music.py
"""
import os
import re
import json
import subprocess

import imageio_ffmpeg
from mutagen.mp3 import MP3

SRC_DIR = "D:/CloudMusic/off"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "docs", "music")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BITRATE = "128k"


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith(".mp3"))
    print(f"发现 {len(files)} 首 MP3")

    tracks = []
    for i, fname in enumerate(files, 1):
        src = os.path.join(SRC_DIR, fname)
        title = re.sub(r"^Alias Conrad Coldwood\s*-\s*", "", fname).replace(".mp3", "").strip()
        slug = f"{i:02d}-{slugify(title)}.mp3"
        dst = os.path.join(OUT_DIR, slug)
        if not os.path.exists(dst):
            subprocess.run([FFMPEG, "-y", "-i", src,
                            "-codec:a", "libmp3lame", "-b:a", BITRATE,
                            "-map_metadata", "-1", "-id3v2_version", "3",
                            dst],
                           capture_output=True)
        dur = round(MP3(dst).info.length)
        size_mb = os.path.getsize(dst) / 1048576
        tracks.append({"file": "music/" + slug, "title": title,
                       "artist": "Alias Conrad Coldwood", "dur": dur})
        print(f"  [{i:02d}] {title}  {dur}s  {size_mb:.1f}MB")

    with open(os.path.join(BASE, "docs", "music.json"), "w", encoding="utf-8") as f:
        json.dump(tracks, f, ensure_ascii=False, indent=1)
    total = sum(os.path.getsize(os.path.join(OUT_DIR, t["file"].split("/")[-1])) for t in tracks)
    print(f"\n完成：{len(tracks)} 首，总大小 {total/1048576:.0f}MB，清单 docs/music.json")


if __name__ == "__main__":
    main()
