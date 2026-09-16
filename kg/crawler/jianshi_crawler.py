# -*- coding: utf-8 -*-
"""
DR-04《中国共产党简史》在线分章全文采集（V3 3.2 Step D）。

先抓章节目录页，解析出各章子页链接，再逐章抓取留档到 data/raw/jianshi/。
解析与切分交由 kg/extract/build_corpus.py。

入口以 data/sources.md 的 DR-06 复核结论为准：中联部党史学习平台，UTF-8，
目录页含第一章至第十章共 10 个章节标题。

纪律：请求间隔 ≥ 2 秒（由 common.fetch 统一保证），原始 HTML 全量留档，
断点续爬（已留档的子页直接复用，不二次抓取）。

用法（项目根目录）：
    python -m kg.crawler.jianshi_crawler           # 抓目录 + 全部章节
    python -m kg.crawler.jianshi_crawler --list    # 只列章节链接不抓正文
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

SUBDIR = "jianshi"
INDEX_URL = "http://www.idcpc.gov.cn/ztwy/tbtj/jdbnghlc/xxzl/jianshi/"
CHAPTER_TEXT = re.compile(r"第[一二三四五六七八九十]+章")


def list_chapters(force=False):
    """从目录页解析各章链接，返回 [{title, url}]（按出现顺序去重）。"""
    html = fetch(INDEX_URL, subdir=SUBDIR, force=force)
    dom = soup(html)
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        if not title or not CHAPTER_TEXT.search(title):
            continue
        url = urljoin(INDEX_URL, a["href"])
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": title, "url": url})
    return out


def crawl(force=False):
    """逐章抓取并留档，返回 [{title, url, path, chars}]。"""
    chapters = list_chapters(force=force)
    done = []
    for ch in chapters:
        try:
            html = fetch(ch["url"], subdir=SUBDIR, force=force)
        except Exception as exc:  # noqa: BLE001 —— 单章失败不中断整批
            print("  抓取失败 %s：%s" % (ch["title"], exc.__class__.__name__))
            continue
        done.append(dict(ch, path=raw_path(ch["url"], SUBDIR), chars=len(html)))
        print("  已留档 %-14s %7d 字符" % (ch["title"][:12], len(html)))
    return done


def main():
    parser = argparse.ArgumentParser(description="DR-04《中国共产党简史》分章采集")
    parser.add_argument("--list", action="store_true", help="只列出章节链接")
    parser.add_argument("--force", action="store_true", help="忽略已有留档，强制重抓")
    args = parser.parse_args()

    if args.list:
        chapters = list_chapters(force=args.force)
        print("目录页：%s\n共 %d 章：\n" % (INDEX_URL, len(chapters)))
        for ch in chapters:
            print("  %-16s %s" % (ch["title"][:14], ch["url"]))
        return 0 if chapters else 1

    print("DR-04 分章采集（间隔 ≥2 秒，留档 data/raw/%s/）\n" % SUBDIR)
    done = crawl(force=args.force)
    print("\n共留档 %d 章" % len(done))
    print("下一步：python -m kg.extract.build_corpus")
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
