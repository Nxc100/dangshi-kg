# -*- coding: utf-8 -*-
"""
DR-02 会议专题试爬（V3 附录 A）：抓 1 个会议专题页，解析会议名 / 时间 / 地点为 dict 打印。
通过标准：字段与原文一致。

用法（项目根目录）：python -m kg.crawler.test_meeting [--url <会议专题页>]

DR-06 实测结论：人民网 /GB/64162/64168/index.html 为目录框架页（10KB，无直达子页链接），
共产党员网专题 https://www.12371.cn/special/lcddh/ 列出二十次大会的直达链接（37 条），
故以后者为 DR-02 主入口。会议子页正文含「时间 / 地点 / 出席代表 / 主要内容」等叙述。
"""
import argparse
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import fetch, soup  # noqa: E402
from kg.extract.clean import clean_text, half_width  # noqa: E402

INDEX_URL = "https://www.12371.cn/special/lcddh/"
# 默认试爬「中共一大」专题页（DR-06 实测路径为 ddh1，非 ddh01）；--url 可换任意会议页
DEFAULT_URL = "https://www.12371.cn/special/lcddh/ddh1/"

MEETING_NAME = re.compile(r"(中国共产党第[一二三四五六七八九十百]+次全国代表大会)")
# 全角数字已由 half_width 归一（DR-02 老页面存在「１９２１年」）
TIME_PAT = re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日(?:[－—~至-]\d{1,2}月\d{1,2}日|[－—~至-]\d{1,2}日)?"
                      r"|\d{4}年\d{1,2}月)")
# 地点表述差异大：「在延安召开」「在上海法租界望志路106号(今兴业路76号)开幕」
# 先取「在…举行/召开/开幕」的整段（允许门牌与括注），再从中截出行政区名作为地点实体候选
PLACE_PAT = re.compile(r"(?:在|于)\s*([一-龥][一-龥\d()（）·]{1,28}?)(?:举行|召开|开幕|举办|开会)")
CITY_HEAD = re.compile(r"^([一-龥]{2,6}?)(?:市|省|县|区)?(?=[一-龥]{0,}?(?:租界|路|街|村|镇|号|里|宾馆|会堂|礼堂)|$)")


def list_meetings(html, limit=25):
    """从专题目录页提取各次大会的名称与链接。"""
    dom = soup(html)
    out, seen = [], set()
    for a in dom.find_all("a", href=True):
        text = clean_text(a.get_text(" ", strip=True))
        if not text or len(text) > 40:
            continue
        if re.search(r"第[一二三四五六七八九十]+次全国代表大会|党的[一二三四五六七八九十]+大", text):
            href = a["href"]
            if href.startswith("/"):
                href = "https://www.12371.cn" + href
            if href not in seen:
                seen.add(href)
                out.append({"name": text, "url": href})
        if len(out) >= limit:
            break
    return out


def parse_meeting(html):
    """从会议专题页解析 {会议名, 时间, 地点}；取正文中首个匹配。"""
    dom = soup(html)
    for tag in dom(["script", "style"]):
        tag.decompose()
    title = clean_text(dom.title.get_text()) if dom.title else ""
    text = half_width(clean_text(dom.get_text(" ", strip=True)))

    name = MEETING_NAME.search(title) or MEETING_NAME.search(text)
    time_m = TIME_PAT.search(text)
    place_m = PLACE_PAT.search(text)
    place = full = "未识别"
    if place_m:
        full = place_m.group(1)
        city = CITY_HEAD.match(full)
        place = city.group(1) if city else full
    return {
        "会议名": name.group(1) if name else (title[:30] or "未识别"),
        "时间": time_m.group(1) if time_m else "未识别",
        "地点": place,
        "地点原文": full,
        "正文长度": len(text),
    }


def main():
    parser = argparse.ArgumentParser(description="DR-02 会议专题试爬")
    parser.add_argument("--url", default=DEFAULT_URL, help="会议专题页 URL")
    parser.add_argument("--index", action="store_true", help="改为列出目录页的各次大会链接")
    args = parser.parse_args()

    if args.index:
        items = list_meetings(fetch(INDEX_URL, subdir="dr06"))
        print("目录页：%s\n共 %d 次大会：\n" % (INDEX_URL, len(items)))
        for it in items:
            print("  %-30s %s" % (it["name"][:28], it["url"]))
        return 0 if items else 1

    html = fetch(args.url, subdir="dr06")
    data = parse_meeting(html)
    print("来源：%s\n" % args.url)
    for key, value in data.items():
        print("  %-8s %s" % (key, value))
    unknown = [k for k, v in data.items() if v == "未识别"]
    if unknown:
        print("\n  ！以下字段未识别：%s（原始页已留档 data/raw/dr06/）" % "、".join(unknown))
    return 1 if len(unknown) >= 3 else 0


if __name__ == "__main__":
    sys.exit(main())
