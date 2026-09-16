# -*- coding: utf-8 -*-
"""
DR-02 历次党代会采集（V3 3.2 Step C）。

入口以 data/sources.md 的 DR-06 复核结论为准：共产党员网「历次党代会」专题，
目录页列出一大至二十大的直达链接（路径为 ddh1 而非 ddh01；十八大以后另用独立专题域）。

职责：枚举各次大会专题页并逐页抓取留档到 data/raw/meeting/。
字段解析见 kg/crawler/test_meeting.py 的试爬验证；正式属性整理走 Excel 人工环节。

用法（项目根目录）：
    python -m kg.crawler.meeting_crawler --list   # 只列大会链接
    python -m kg.crawler.meeting_crawler          # 抓取并留档
"""
import argparse
import os
import re
import sys
from urllib.parse import urljoin

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import fetch, raw_path, soup  # noqa: E402
from kg.extract.clean import clean_text  # noqa: E402

SUBDIR = "meeting"
INDEX_URL = "https://www.12371.cn/special/lcddh/"
MEETING_TEXT = re.compile(r"第[一二三四五六七八九十]+次全国代表大会|党的[一二三四五六七八九十]+大")


def list_meetings(force=False):
    """从专题目录页枚举各次大会，返回 [{name, url}]（保持页面顺序，二十大在前）。"""
    dom = soup(fetch(INDEX_URL, subdir=SUBDIR, force=force))
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        name = clean_text(a.get_text(" ", strip=True))
        if not name or len(name) > 40 or not MEETING_TEXT.search(name):
            continue
        url = urljoin(INDEX_URL, a["href"])
        if url in seen:
            continue
        seen.add(url)
        out.append({"name": name, "url": url})
    return out


def crawl(force=False):
    """逐个大会专题页抓取留档。"""
    done = []
    for m in list_meetings(force=force):
        try:
            html = fetch(m["url"], subdir=SUBDIR, force=force)
        except Exception as exc:  # noqa: BLE001 —— 单页失败不中断整批
            print("  抓取失败 %-24s %s" % (m["name"][:22], exc.__class__.__name__))
            continue
        done.append(dict(m, path=raw_path(m["url"], SUBDIR), chars=len(html)))
        print("  已留档 %-24s %7d 字符" % (m["name"][:22], len(html)))
    return done


def main():
    parser = argparse.ArgumentParser(description="DR-02 历次党代会采集")
    parser.add_argument("--list", action="store_true", help="只列出大会链接")
    parser.add_argument("--force", action="store_true", help="忽略已有留档，强制重抓")
    args = parser.parse_args()

    if args.list:
        items = list_meetings(force=args.force)
        print("目录页：%s\n共 %d 次大会：\n" % (INDEX_URL, len(items)))
        for m in items:
            print("  %-26s %s" % (m["name"][:24], m["url"]))
        return 0 if items else 1

    print("DR-02 党代会采集（间隔 ≥2 秒，留档 data/raw/%s/）\n" % SUBDIR)
    done = crawl(force=args.force)
    print("\n共留档 %d 次大会" % len(done))
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
