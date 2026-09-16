# -*- coding: utf-8 -*-
"""
DR-03 党史人物采集（V3 3.2 Step C）。

入口以 data/sources.md 的 DR-06 复核结论为准：人民网党史频道·党史资料库人物栏
（纪念馆首页 /GB/69112/index.html 已 403，但其下的人物专页 /GB/69112/<id>/ 仍可访问）。

职责：从人物栏枚举人物专页链接，逐页抓取留档到 data/raw/person/。
解析与属性整理交由 kg/extract/extract_triples.py 与 Excel 人工整理环节。

用法（项目根目录）：
    python -m kg.crawler.person_crawler --list   # 只列人物链接
    python -m kg.crawler.person_crawler          # 抓取并留档
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

SUBDIR = "person"
INDEX_URL = "http://dangshi.people.com.cn/GB/234123/index.html"
# 人物专页形如 http://cpc.people.com.cn/GB/69112/70190/index.html
PERSON_URL = re.compile(r"/GB/69112/\d+/")
# 中文姓名：2–4 字，排除栏目名
NAME_OK = re.compile(r"^[一-龥·]{2,6}$")
NOT_NAME = {"纪念馆", "人物", "领袖", "元勋", "将帅", "先辈", "英烈", "更多", "首页", "毛主席纪念堂"}


def list_persons(force=False):
    """从人物栏解析人物专页链接，返回 [{name, url}]。"""
    dom = soup(fetch(INDEX_URL, subdir=SUBDIR, force=force))
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        name = clean_text(a.get_text(" ", strip=True))
        url = urljoin(INDEX_URL, a["href"])
        if not PERSON_URL.search(url) or url in seen:
            continue
        if not NAME_OK.match(name) or name in NOT_NAME:
            continue
        seen.add(url)
        out.append({"name": name, "url": url})
    return out


# 人物专题下的正文子栏目：index.html 本身只是目录页，生平正文在这些子栏目里
BIO_SECTIONS = ("生平简介", "大事年表", "生平年谱", "人物生平")


def list_bio_pages(index_url, html):
    """从人物专题目录页解析生平类子栏目链接。"""
    dom = soup(html)
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        if title not in BIO_SECTIONS:
            continue
        url = urljoin(index_url, a["href"])
        if url in seen:
            continue
        seen.add(url)
        out.append({"section": title, "url": url})
    return out


def crawl(force=False, limit=0, with_bio=True):
    """
    逐个人物抓取留档。先抓专题目录页，再下钻其「生平简介 / 大事年表」子栏目，
    因为目录页本身不含正文（DR-06 实测：<p> 数为 0）。
    """
    persons = list_persons(force=force)
    if limit:
        persons = persons[:limit]
    done = []
    for p in persons:
        try:
            html = fetch(p["url"], subdir=SUBDIR, force=force)
        except Exception as exc:  # noqa: BLE001 —— 单页失败不中断整批
            print("  抓取失败 %-8s %s" % (p["name"], exc.__class__.__name__))
            continue
        bios = list_bio_pages(p["url"], html) if with_bio else []
        got = 0
        for bio in bios:
            try:
                sub = fetch(bio["url"], subdir=SUBDIR, force=force)
            except Exception as exc:  # noqa: BLE001
                print("    子页失败 %-8s %s" % (bio["section"], exc.__class__.__name__))
                continue
            got += len(sub)
        done.append(dict(p, path=raw_path(p["url"], SUBDIR), chars=len(html), bio_chars=got))
        print("  已留档 %-8s 目录 %6d 字符 + 生平子页 %d 个 / %7d 字符"
              % (p["name"], len(html), len(bios), got))
    return done


def main():
    parser = argparse.ArgumentParser(description="DR-03 党史人物采集")
    parser.add_argument("--list", action="store_true", help="只列出人物链接")
    parser.add_argument("--limit", type=int, default=0, help="只抓前 N 个（0 为全部）")
    parser.add_argument("--force", action="store_true", help="忽略已有留档，强制重抓")
    args = parser.parse_args()

    if args.list:
        persons = list_persons(force=args.force)
        print("人物栏：%s\n可枚举人物 %d 位：\n" % (INDEX_URL, len(persons)))
        for p in persons:
            print("  %-8s %s" % (p["name"], p["url"]))
        return 0 if persons else 1

    print("DR-03 人物页采集（间隔 ≥2 秒，留档 data/raw/%s/）\n" % SUBDIR)
    done = crawl(force=args.force, limit=args.limit)
    print("\n共留档 %d 位人物" % len(done))
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
