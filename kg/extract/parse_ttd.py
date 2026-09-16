# -*- coding: utf-8 -*-
"""
DR-12「党史百年·天天读」解析（V3 3.2 Step C + 3.3 清洗与时间标准化）。

读取 data/raw/ttd/ 的 366 个日页留档，解析三个板块的编年条目，
产出 data/clean/ttd_raw.csv，字段与大事记 events_raw.csv 对齐，便于下游统一处理。

页面结构（实地核查 data/raw/ttd/）：
  · 「重要论述」 div.discuss-con > .discuss-scroll-con —— 依次为「YYYY年M月D日」标记与正文块；
  · 「党史回眸」 div.event-con   > .event-scroll-con   —— 依次为「YYYY年」标记与「M月D日 正文」块；
  · 「历史瞬间」 div.swiper-focus .box                 —— 整句图注，自带完整日期。
三者正文均承载于**裸 `<div>`**，故按容器的直接子节点顺序成对读取，而非按 `<p>` 取。

时间三字段与时期归属复用唯一实现（timeparse / period_assign），不在此另写一份。

用法（项目根目录）：python -m kg.extract.parse_ttd
"""
import argparse
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import soup, write_csv  # noqa: E402
from kg.crawler.ttd_crawler import SUBDIR  # noqa: E402
from kg.extract import period_assign, timeparse  # noqa: E402
from kg.extract.clean import clean_text  # noqa: E402

RAW_DIR = os.path.join(_ROOT, "data", "raw", SUBDIR)
OUT_CSV = os.path.join(_ROOT, "data", "clean", "ttd_raw.csv")
FIELDS = ["年份", "日期原文", "条目正文", "板块", "来源URL",
          "time_sort", "time_precision", "所属时期"]

# 板块选择器 → 板块名。前两者按「标记 + 正文」成对读取，第三者为整句图注
PAIRED_SECTIONS = (("div.discuss-con .discuss-scroll-con", "重要论述"),
                   ("div.event-con .event-scroll-con", "党史回眸"))
CAPTION_SECTION = ("div.swiper-focus .box", "历史瞬间")

YEAR = r"(?:1[89]\d{2}|20\d{2})"
YEAR_ONLY = re.compile(r"^(%s)\s*年$" % YEAR)
FULL_MARK = re.compile(r"^(%s)\s*年\s*(\d{1,2}月\d{1,2}日)\s*$" % YEAR)
DATE_HEAD = re.compile(r"^(\d{1,2}月\d{1,2}日(?:[－—~至-]\d{1,2}(?:月\d{1,2})?日)?|\d{1,2}月)\s*")
CAPTION = re.compile(r"^(%s)\s*年\s*(\d{1,2}月\d{1,2}日)\s*[，,]\s*(.+)$" % YEAR)
MIN_DESC_LEN = 12  # 短于此的块视为排版残留，不作条目


def _chunks(container):
    """按容器的直接子节点顺序取文本块——正文整体落在一个子 div 内，不可再向下拆。"""
    out = []
    for child in container.children:
        text = clean_text(child.get_text(" ", strip=True)
                          if getattr(child, "get_text", None) else str(child))
        if text:
            out.append(text)
    return out


def _emit(year, date_text, desc, section, url):
    """把一条已定位到年月日的表述转成条目行。"""
    time_sort, precision = timeparse.parse("%s年%s" % (year, date_text))
    if time_sort is None:
        time_sort, precision = "%s9999" % year, "year"
    return {"年份": year, "日期原文": date_text, "条目正文": desc, "板块": section,
            "来源URL": url, "time_sort": time_sort, "time_precision": precision,
            "所属时期": period_assign.assign(time_sort) or ""}


def parse_paired(container, section, url):
    """
    「重要论述」「党史回眸」两板块：标记块与正文块交替出现。

    两者标记形态不同（前者「YYYY年M月D日」、后者仅「YYYY年」而日期在正文首），
    故统一维护 year / date 上下文，正文块自带日期时以自带者为准。
    """
    items, year, date_text = [], None, None
    for text in _chunks(container):
        full = FULL_MARK.match(text)
        if full:
            year, date_text = full.group(1), full.group(2)
            continue
        only = YEAR_ONLY.match(text)
        if only:
            year, date_text = only.group(1), None
            continue
        if year is None:
            continue
        head = DATE_HEAD.match(text)
        body = text[head.end():].lstrip("　 ，,、").strip() if head else text
        current = head.group(1) if head else date_text
        if not current or len(body) < MIN_DESC_LEN:
            continue
        items.append(_emit(year, current, body, section, url))
    return items


def parse_captions(dom, url):
    """「历史瞬间」图注：整句自带完整日期，逐句成条。"""
    selector, section = CAPTION_SECTION
    items = []
    for node in dom.select(selector):
        m = CAPTION.match(clean_text(node.get_text(" ", strip=True)))
        if m and len(m.group(3)) >= MIN_DESC_LEN:
            items.append(_emit(m.group(1), m.group(2), m.group(3), section, url))
    return items


def parse_page(html, url):
    """解析单个日页，返回三个板块的全部条目。"""
    dom = soup(html)
    for tag in dom(["script", "style"]):
        tag.decompose()
    items = []
    for selector, section in PAIRED_SECTIONS:
        container = dom.select_one(selector)
        if container is not None:
            items.extend(parse_paired(container, section, url))
    items.extend(parse_captions(dom, url))
    return items


def load_archived():
    """读取留档日页；文件名与 URL 的对应由 ttd_crawler.list_days 还原。"""
    from kg.crawler.common import raw_path
    from kg.crawler.ttd_crawler import list_days

    pages = []
    for item in list_days():
        path = raw_path(item["url"], SUBDIR)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                pages.append((item["url"], f.read()))
    return pages


def summarize(items):
    from collections import Counter

    years = sorted({int(i["年份"]) for i in items})
    print("  条目总数 %d，覆盖 %d—%d 年" % (len(items), years[0], years[-1]))
    print("  板块分布：%s" % dict(Counter(i["板块"] for i in items)))
    print("  时间精度：%s" % dict(Counter(i["time_precision"] for i in items)))
    periods = Counter(i["所属时期"] or "（未归属）" for i in items)
    for name, count in sorted(periods.items(), key=lambda kv: -kv[1]):
        print("    %-24s %5d" % (name, count))


def main():
    parser = argparse.ArgumentParser(description="DR-12 天天读日页解析")
    parser.add_argument("--limit", type=int, default=0, help="只解析前 N 条（0 为全部）")
    args = parser.parse_args()

    pages = load_archived()
    if not pages:
        print("未找到留档日页，请先执行：python -m kg.crawler.ttd_crawler")
        return 1

    seen, items = set(), []
    for url, html in pages:
        for item in parse_page(html, url):
            # 同一史实会同时出现在「重要论述」与「历史瞬间」，按年月日 + 正文去重
            key = (item["年份"], item["日期原文"], item["条目正文"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    if args.limit:
        items = items[:args.limit]
    if not items:
        print("未解析出条目，请检查页面结构是否变动（留档在 data/raw/%s/）" % SUBDIR)
        return 1

    write_csv(OUT_CSV, items, FIELDS)
    print("\nDR-12 解析结果（留档 %d 页）" % len(pages))
    summarize(items)
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
