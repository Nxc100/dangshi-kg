# -*- coding: utf-8 -*-
"""
DR-01 大事记试爬（V3 附录 A）：抓 1 个大事记页，切出「日期 + 事件描述」打印前 N 条。
通过标准：字段与原文一致。

用法（项目根目录）：python -m kg.crawler.test_dsj [--limit 10]

页面结构（DR-06 实测）：年份加粗标题行驱动年份上下文，其下逐条「日期 + 事件描述」，
日期形如「7月23日」「1月」「本年」。编码由 common.detect_encoding 按 meta 判定（本页为 gb2312）。
"""
import argparse
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import fetch, soup  # noqa: E402
from kg.extract.clean import clean_text  # noqa: E402

URL = "http://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html"

# 年份独占一段，如「1921年」（DR-06 实测：div.show_text 下 1177 个 <p>）
YEAR_LINE = re.compile(r"^(1[89]\d{2}|20\d{2})\s*年$")
# 条目开头的日期表述：7月23日 / 5月5日－10日 / 1月 / 本年 / 春
DATE_HEAD = re.compile(
    r"^(\d{1,2}月\d{1,2}日(?:[－—~至-]\d{1,2}(?:月\d{1,2})?日)?"
    r"|\d{1,2}月(?:[－—~至-]\d{1,2}月)?"
    r"|本年(?:\d{1,2}月)?|春|夏|秋|冬)")


def parse(html, limit=10):
    """返回 [(年份, 日期文本, 事件描述)]；年份独占段落驱动上下文，其后各段以日期开头。"""
    dom = soup(html)
    for tag in dom(["script", "style"]):
        tag.decompose()
    body = dom.select_one("div.show_text") or dom
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
            continue  # 正文开头的说明性段落，无年份上下文
        dm = DATE_HEAD.match(line)
        if not dm:
            continue
        desc = line[dm.end():].lstrip("　 ，,、").strip()
        if desc:
            items.append((year, dm.group(1), desc))
            if limit and len(items) >= limit:
                break
    return items


def main():
    parser = argparse.ArgumentParser(description="DR-01 大事记试爬")
    parser.add_argument("--limit", type=int, default=10, help="打印前 N 条，0 表示全部")
    args = parser.parse_args()

    html = fetch(URL, subdir="dr06")
    items = parse(html, limit=args.limit)
    print("来源：%s" % URL)
    print("解析出 %d 条（limit=%s）\n" % (len(items), args.limit or "全部"))
    for year, date, desc in items:
        print("  %s 年 %-12s %s" % (year, date, desc[:60]))
    if not items:
        print("  ！未解析出条目，请检查页面结构是否变动（原始页已留档 data/raw/dr06/）")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
