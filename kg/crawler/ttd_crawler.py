# -*- coding: utf-8 -*-
"""
DR-12「党史百年·天天读」采集（中共中央党史和文献研究院官网，2026-09-16 新增数据源）。

新增理由：DR-01~DR-05 按其实际容量已取尽，仍不足以支撑 V3 3.7 的实体与语料验收线
（人物正文栏目下线、党代会专题页仅存摘要）。本栏目按 366 天组织，每天含「重要论述 /
党史回眸 / 历史瞬间」等板块，均为带确切日期的史实表述，正文详实、出处权威。

站点结构（实地核查）：
  · 栏目首页 /GB/434461/index.html 静态列出全部 366 个日期页链接，
    形如 /GB/434461/<月栏目 434462~434473>/<日页>/index.html；
  · 日期页正文承载于**裸 `<div>`**（外层为 mCSB 滚动插件容器）而非 `<p>`，
    静态 requests 可完整取得，无需浏览器渲染。

用法（项目根目录）：
    python -m kg.crawler.ttd_crawler --list      # 只列出日期页清单，不抓正文
    python -m kg.crawler.ttd_crawler             # 抓取并留档到 data/raw/ttd/
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

SUBDIR = "ttd"
INDEX_URL = "https://www.dswxyjy.org.cn/GB/434461/index.html"
# 日期页：/GB/434461/<月栏目>/<日页>/index.html；月栏目 434462（1 月）~434473（12 月）
DAY_HREF = re.compile(r"^/GB/434461/(4344[6-7]\d)/(\d+)/index\.html$")
MONTH_BASE = 434462           # 434462 = 1 月，按月递增至 434473 = 12 月
EXPECT_DAYS = 366             # 栏目按闰年编排，1 月 31 天 … 2 月 29 天


def list_days(force=False):
    """
    从栏目首页解析全部日期页。

    首页一次性静态列出 12 个月栏目下的全部日期链接，故无需逐月翻页；
    月份由月栏目 ID 相对 MONTH_BASE 的偏移推出，日期取链接文本（「1日」）。
    """
    dom = soup(fetch(INDEX_URL, subdir=SUBDIR, force=force))
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        m = DAY_HREF.match(a["href"])
        if not m:
            continue
        url = urljoin(INDEX_URL, a["href"])
        if url in seen:
            continue
        seen.add(url)
        month = int(m.group(1)) - MONTH_BASE + 1
        day = clean_text(a.get_text(" ", strip=True)).rstrip("日")
        if not (1 <= month <= 12) or not day.isdigit():
            continue
        out.append({"month": month, "day": int(day),
                    "title": "%d月%s日" % (month, day), "url": url})
    out.sort(key=lambda d: (d["month"], d["day"]))
    return out


def crawl(days, force=False):
    """逐页抓取并留档，返回 (成功数, 失败清单)。间隔由 common.fetch 统一控制（≥2 秒）。"""
    ok, failed = 0, []
    for index, item in enumerate(days, 1):
        try:
            fetch(item["url"], subdir=SUBDIR, force=force)
            ok += 1
        except Exception as exc:  # noqa: BLE001 —— 单页失败不中断整轮采集
            failed.append((item["title"], exc.__class__.__name__))
        if index % 30 == 0:
            print("  已抓取 %d/%d" % (index, len(days)))
    return ok, failed


def main():
    parser = argparse.ArgumentParser(description="DR-12 党史百年·天天读采集")
    parser.add_argument("--list", action="store_true", help="只列出日期页清单")
    parser.add_argument("--force", action="store_true", help="忽略已有留档，强制重抓")
    args = parser.parse_args()

    print("DR-12 天天读采集（间隔 ≥2 秒，留档 data/raw/%s/）" % SUBDIR)
    days = list_days(force=args.force)
    print("栏目首页解析出 %d 个日期页（应为 %d）\n" % (len(days), EXPECT_DAYS))
    if args.list:
        for item in days[:15]:
            print("  %-8s %s" % (item["title"], item["url"]))
        print("  ……")
        return 0 if days else 1

    ok, failed = crawl(days, force=args.force)
    total = sum(os.path.getsize(raw_path(d["url"], SUBDIR))
                for d in days if os.path.exists(raw_path(d["url"], SUBDIR)))
    print("\n留档成功 %d/%d 页，合计 %.1f MB" % (ok, len(days), total / 1024 / 1024))
    if failed:
        print("失败 %d 页：%s" % (len(failed), failed[:10]))
    print("下一步：python -m kg.extract.build_corpus（天天读正文并入 F9 语料）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
