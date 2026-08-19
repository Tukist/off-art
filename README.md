# OFF 美术设定资料包

《OFF》(Mortis Ghost / Unproductive Fun Time, 2008) 的美术设定资料与作者访谈整理。

> **收集日期**：2026-08（本地时区）
> **目的**：个人学习研究与收藏
> **注意**：本包所有内容版权归原作者 Mortis Ghost、作曲家 Alias Conrad Coldwood、发行方 Fangamer 及相关版权方所有，仅供个人参考，**禁止商用与二次发布**。见文末「版权声明」。

---

## 总览

| 类别 | 数量 | 位置 |
|------|------|------|
| 官方美术与宣传图 | 25 张（截图/Logo/背景） | `art/official/` |
| 作者博客概念图 | 35 张 | `art/official/` |
| Wiki 美术图（角色/场景/图标） | 425 张 | `art/wiki/` |
| 粉丝整理艺术档案 | 752 张 | `art/fan/` |
| 官方周边与收藏版内容物 | 31 张 | `art/merch/` |
| 设定文本页 | 23 页 | `wiki/` |
| 作者访谈全文 | 7 篇 | `interviews/` |

## 目录结构

```
off-art/
├── README.md                # 本文件
├── art/
│   ├── official/            # 官方宣传图 + 作者博客概念图（含 _mortis_posts.md 帖文记录）
│   ├── wiki/                # OFF Wiki (Fandom) 美术图，全站图片
│   ├── fan/                 # 粉丝整理的官方艺术档案（Tumblr: off-art-archive）
│   └── merch/               # 官方周边 + OFF 收藏版内容物图
├── wiki/                    # 设定文本（Batter、The Judge、四区域、Sugar、Mortis Ghost 等 23 页）
├── interviews/              # 作者/合作者访谈全文（7 篇 + 索引 _index.md）
└── scripts/                 # 全部抓取脚本（可重跑/续抓）
```

---

## 内容详述

### art/official/ — 官方美术
- **offtherpg.com**：8 张官方截图（1920×1080）、官方 Logo、网页背景美术（含 Batter 氛围图）、预告片封面
- **作者博客 mortisghost.tumblr.com**：16 帖 OFF 相关概念图（2013–2026），帖文英文原文见 `_mortis_posts.md`
- 清单：`_source_list.csv`

### art/wiki/ — OFF Wiki 美术图
- 全站图片 425 张：角色立绘、场景、图标、封面、2025 重制版素材等
- 来源：https://off.fandom.com（Fandom CDN，已用 `&format=original` 还原原始格式）
- 清单：`_source_list.csv`（文件名 | 原始URL | wiki文件名）

### art/fan/ — 粉丝整理的艺术档案
- 来源：https://off-art-archive.tumblr.com（粉丝汇总 Mortis Ghost 的概念图、笔记本扫描、怪物设计等）
- 帖子文字记录：`_notes.csv`；图片清单：`_source_list.csv`

### art/merch/ — 官方周边与收藏版
- **OFF 收藏版（Bad Human Edition）**内容物高清图：摇头公仔、前传漫画《OF》、收藏盒、星座/塔罗卡、说明书、纪念卡
- **周边**：Batter/Dedan/Judge 毛绒、帽子、球衣、T 恤、海报、桌垫、胸针
- 来源：Fangamer 官网

### wiki/ — 设定文本
23 页 Markdown，含：`OFF`（游戏总览）、`The_Batter`、`The_Judge`、`Zacharie`、`The_Player`、`Dedan`、`Japhet`、`Vader_Eloha`、`Sugar`、`Spectres`、`Elsen`、`Zones`、`Zone_0/1/2/3`、`The_Room`、`Enoch`、`The_Queen`、`Purified_Zones`、`Add-Ons`、`The_Nothingness`、`Mortis_Ghost`
索引见 `wiki/_index.md`

### interviews/ — 访谈全文
| 文件 | 内容 |
|------|------|
| `gamatomic_2025_off_interview.md` | **GamAtomic 2025 专访**（重制版发售，最全面） |
| `offtherpg_tobyfox_interview.md` | Toby Fox 谈 OFF 对他的影响 |
| `offtherpg_morusque_interview.md` | 新配乐作者 Morusque 的 OFF 缘起 |
| `offtherpg_quinn_k_interview.md` | 英文版译者 Quinn K. 谈本地化 |
| `offtherpg_nightmargin_interview.md` | OneShot 作者 Nightmargin 谈配乐与 RPG Maker |
| `off_15th_anniversary_stream_notes.md` | 15 周年直播文字整理（4 小时 VOD 全稿） |
| `mortis_ghost_coldwood_text_interview.md` | Mortis Ghost 与作曲家 Coldwood 经典双人访谈（2016） |

---

## 来源链接

| 来源 | URL |
|------|-----|
| OFF 官方站 | https://offtherpg.com |
| OFF 官方周边 | https://www.fangamer.com/collections/off |
| 作者博客（Tumblr） | https://mortisghost.tumblr.com |
| 粉丝艺术档案（Tumblr） | https://off-art-archive.tumblr.com |
| OFF Wiki (Fandom) | https://off.fandom.com |
| OFF 百科词条（维基） | https://en.wikipedia.org/wiki/Off_(video_game) |

## 版权声明

本资料包中所有图片、文字、标识的版权归其原始权利人所有：

- 游戏与美术：《OFF》© Mortis Ghost / Unproductive Fun Time
- 配乐：Alias Conrad Coldwood；2025 重制版新配乐含 Toby Fox、Morusque 等
- 实体版与周边：© Fangamer
- Wiki 文本：CC BY-SA（Fandom）；访谈文字版权归原作者/发布站点

本包仅用于个人学习、研究与收藏，**不得用于商业用途或公开传播**。如权利人要求删除，请告知。

## 重抓脚本

`scripts/` 下脚本均幂等（已下载自动跳过），可重新执行：

```bash
# 续抓 fan 档案（改 MAX_IMAGES 可加大上限）
python scripts/fetch_tumblr_fan_art.py

# 重新抓作者博客概念图
python scripts/fetch_tumblr_official_art.py

# 重新下载 wiki 图片（先 fetch_wiki_image_list.py 刷新清单）
python scripts/fetch_wiki_image_list.py
python scripts/download_wiki_images.py

# 重新抓取访谈（原始 HTML 在 scripts/_raw/ 可追溯）
python scripts/convert_interviews.py

# 周边图（需要先保存两个 Fangamer 页面 HTML）
python scripts/download_fangamer_merch.py <集合页.html> <收藏版页.html>
```

网络说明：Tumblr 与 Fandom 需走本地代理 `127.0.0.1:7897`（脚本内已配置）；offtherpg/Fangamer 可直连。
