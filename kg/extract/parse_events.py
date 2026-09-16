# -*- coding: utf-8 -*-
"""
DR-08 大事记全量解析（V3 3.2 Step B + 3.3 清洗与时间标准化）。

读取 data/raw/dsj/ 的留档页，解析编年条目并产出 data/clean/events_raw.csv。
字段：年份、日期原文、条目正文、来源URL、time_sort、time_precision、所属时期。

页面结构（DR-06 实测）：正文在 div.show_text，年份独占一段（如「1921年」）驱动上下文，
其后各段以日期开头（7月23日 / 5月5日－10日 / 1月 / 本年 / 春）。

时间三字段与时期归属复用唯一实现（timeparse / period_assign），不在此另写一份。
CSV 以 utf-8-sig 落盘，Excel 直接打开无乱码（规范 7.2）。

用法（项目根目录）：python -m kg.extract.parse_events [--limit N]
"""
import argparse
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import soup, write_csv  # noqa: E402
from kg.crawler.dsj_crawler import SUBDIR, URLS  # noqa: E402
from kg.extract import period_assign, timeparse  # noqa: E402
from kg.extract.clean import clean_text  # noqa: E402

OUT_CSV = os.path.join(_ROOT, "data", "clean", "events_raw.csv")
FIELDS = ["年份", "日期原文", "条目正文", "来源URL", "time_sort", "time_precision", "所属时期"]

YEAR_LINE = re.compile(r"^(1[89]\d{2}|20\d{2})\s*年$")
DATE_HEAD = re.compile(
    r"^(\d{1,2}月\d{1,2}日(?:[－—~至-]\d{1,2}(?:月\d{1,2})?日)?"
    r"|\d{1,2}月(?:[－—~至-]\d{1,2}月)?"
    r"|本年(?:\d{1,2}月)?|春|夏|秋|冬)")
MIN_DESC_LEN = 8  # 过短的残段不作为条目


def parse_page(html, url):
    """解析单个留档页，返回条目列表。"""
    dom = soup(html)
    for tag in dom(["script", "style"]):
        tag.decompose()
    body = dom.select_one("div.show_text") or dom.select_one("div.text") or dom
    year, items = None, []
    for p in body.find_all("p"):
        line = clean_text(p.get_text(" ", strip=True))
        if not line:
            continue
        ym = YEAR_LINE.match(line)
        if ym:
            year = ym.group(1)
            continue
        if year is None:
            continue
        dm = DATE_HEAD.match(line)
        if not dm:
            continue
        desc = line[dm.end():].lstrip("　 ，,、").strip()
        if len(desc) < MIN_DESC_LEN:
            continue
        date_text = dm.group(1)
        # 「本年」「春」等无月日表述，按仅到年处理
        time_sort, precision = timeparse.parse("%s年%s" % (year, date_text)
                                               if date_text[0].isdigit() else "%s年" % year)
        if time_sort is None:
            time_sort, precision = "%s9999" % year, "year"
        items.append({
            "年份": year,
            "日期原文": date_text,
            "条目正文": desc,
            "来源URL": url,
            "time_sort": time_sort,
            "time_precision": precision,
            "所属时期": period_assign.assign(time_sort) or "",
        })
    return items


def load_archived():
    """读取已留档的大事记页；未留档时提示先跑采集脚本。"""
    from kg.crawler.common import raw_path

    pages = []
    for url in URLS:
        path = raw_path(url, SUBDIR)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                pages.append((url, f.read()))
            break  # 主入口已留档即可，镜像仅作备用
    return pages


def summarize(items):
    from collections import Counter

    years = sorted({int(i["年份"]) for i in items})
    print("  条目总数 %d，覆盖 %d—%d 年" % (len(items), years[0], years[-1]) if years else "  无条目")
    prec = Counter(i["time_precision"] for i in items)
    print("  时间精度：%s" % dict(prec))
    periods = Counter(i["所属时期"] or "（未归属）" for i in items)
    for name, count in sorted(periods.items(), key=lambda kv: -kv[1]):
        print("    %-24s %4d" % (name, count))


def main():
    parser = argparse.ArgumentParser(description="DR-08 大事记全量解析")
    parser.add_argument("--limit", type=int, default=0, help="只解析前 N 条（0 为全部）")
    args = parser.parse_args()

    pages = load_archived()
    if not pages:
        print("未找到留档页，请先执行：python -m kg.crawler.dsj_crawler")
        return 1

    items = []
    for url, html in pages:
        items.extend(parse_page(html, url))
    if args.limit:
        items = items[:args.limit]
    if not items:
        print("未解析出条目，请检查页面结构是否变动（留档在 data/raw/%s/）" % SUBDIR)
        return 1

    write_csv(OUT_CSV, items, FIELDS)
    print("\nDR-08 解析结果")
    summarize(items)
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
