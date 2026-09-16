# -*- coding: utf-8 -*-
"""
DR-06 数据源入口复核（FRS 3.2）：逐一访问 DR-01~DR-05 与 DR-12 的入口，记录
「URL、可达性、编码、页面结构备注」，样页留档 data/raw/，结果回填 data/sources.md。

用法（项目根目录）：python -m kg.crawler.check_sources [--no-archive]

纪律（FRS 3.1 / 规范 7.3）：只访问权威官方公开静态页；常规浏览器 UA；
请求间隔 ≥ 2 秒；原始 HTML 全量留档，解析可离线重跑。

同一数据源登记多个候选入口时逐个尝试，首个可达者记为主入口，其余记为备用。
"""
import argparse
import os
import re
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests  # noqa: E402

from kg.crawler.common import MIN_INTERVAL, TIMEOUT, UA, encoding_for, raw_path  # noqa: E402

_META_CHARSET = re.compile(r'charset\s*=\s*["\']?\s*([\w-]+)', re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def _probe_dsj(text):
    """DR-01 大事记全文：年份标题行驱动 + 逐条「日期 + 事件描述」。"""
    years = sorted(set(re.findall(r"(19[2-9]\d|20[0-2]\d)\s*年", text)))
    entries = re.findall(r"(\d{1,2}\s*月\s*\d{1,2}\s*日)", text)
    span = ("%s—%s" % (years[0], years[-1])) if years else "未识别到年份"
    return "年份标题 %d 个（%s）；「月日」条目 %d 处" % (len(years), span, len(entries))


def _probe_meeting(text):
    """DR-02 历次党代会数据库：各次大会子页链接。"""
    hits = set(re.findall(r"(中国共产党第[一二三四五六七八九十]+次全国代表大会|"
                          r"[一二三四五六七八九十]+大)(?=[^\w]|$)", text))
    links = len(re.findall(r'href="[^"]*(?:64162|lcddh)[^"]*"', text))
    return "大会名称 %d 种；专题链接 %d 条" % (len(hits), links)


def _probe_person(text):
    """DR-03 党史人物：人物专题链接与馆别栏目。"""
    halls = [h for h in ("领袖", "元勋", "将帅", "先辈", "英烈", "人物") if h in text]
    links = len(re.findall(r'href="[^"]*(?:69112|234123)[^"]*"', text))
    return "栏目 %s；人物链接 %d 条" % ("/".join(halls) or "未识别", links)


def _probe_jianshi(text):
    """DR-04《中国共产党简史》分章：第一章至第十章目录。"""
    chapters = sorted(set(re.findall(r"第([一二三四五六七八九十]+)章", text)))
    links = len(re.findall(r'href="[^"]*\.(?:htm|html)"', text))
    return "章节标题 %d 个（%s）；链接 %d 条" % (
        len(chapters), "、".join("第%s章" % c for c in chapters[:3]) + ("…" if len(chapters) > 3 else ""), links)


def _probe_ttd(text):
    """DR-12 党史百年·天天读：栏目首页一次性列出全年日期页链接。"""
    days = set(re.findall(r'href="(/GB/434461/4344\d\d/\d+/index\.html)"', text))
    months = {d.split("/")[3] for d in days}
    return "日期页链接 %d 条，覆盖月栏目 %d 个" % (len(days), len(months))


def _probe_generic(text):
    links = len(re.findall(r'href="[^"]+"', text))
    return "页面链接 %d 条" % links


# 候选入口按优先级排列；首个可达者记为主入口
SOURCES = [
    {"id": "DR-01", "name": "《中国共产党一百年大事记》全文页",
     "supply": "事件实体主来源、时间轴数据、时期划分依据",
     "urls": ["http://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html",
              "https://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html",
              "https://www.qstheory.cn/yaowen/2021-06/28/c_1127603704.htm"],
     "probe": _probe_dsj},
    {"id": "DR-02", "name": "历次党代会数据库",
     "supply": "会议实体主来源",
     "urls": ["http://cpc.people.com.cn/GB/64162/64168/index.html",
              "https://www.12371.cn/special/lcddh/"],
     "probe": _probe_meeting},
    {"id": "DR-03", "name": "党史人物纪念馆 / 党史资料库人物栏",
     "supply": "人物实体主来源",
     "urls": ["http://cpc.people.com.cn/GB/69112/index.html",
              "http://dangshi.people.com.cn/GB/234123/index.html"],
     "probe": _probe_person},
    {"id": "DR-04", "name": "《中国共产党简史》在线分章全文",
     "supply": "F9 兜底语料、属性整理依据、组织沿革依据",
     "urls": ["http://www.idcpc.gov.cn/ztwy/tbtj/jdbnghlc/xxzl/jianshi/",
              "https://www.idcpc.gov.cn/ztwy/tbtj/jdbnghlc/xxzl/jianshi/"],
     "probe": _probe_jianshi},
    {"id": "DR-05", "name": "人民网党史频道「党史大事记」栏目",
     "supply": "文献实体来源、语料补充",
     "urls": ["http://cpc.people.com.cn/GB/64162/64164/index.html"],
     "probe": _probe_generic},
    {"id": "DR-12", "name": "中央党史和文献研究院「党史百年·天天读」",
     "supply": "事件实体主来源（按日编年）、F9 语料主体、人物与文献佐证",
     "urls": ["https://www.dswxyjy.org.cn/GB/434461/index.html"],
     "probe": _probe_ttd},
]


def decode(resp, url):
    """返回 (文本, 实际使用的编码, 声明来源)。人民网系显式 GBK（DR-07）。"""
    header_enc = (resp.encoding or "").lower()
    meta = _META_CHARSET.search(resp.content[:3000].decode("latin-1", "ignore"))
    meta_enc = (meta.group(1).lower() if meta else "")
    chosen = encoding_for(url)  # 域名规则优先：people.com.cn 系为 gbk
    if meta_enc and meta_enc not in ("iso-8859-1",):
        chosen = "gbk" if meta_enc in ("gb2312", "gbk", "gb18030") else meta_enc
    try:
        text = resp.content.decode(chosen, "replace")
    except LookupError:
        chosen, text = "utf-8", resp.content.decode("utf-8", "replace")
    return text, chosen, "meta=%s / header=%s" % (meta_enc or "无", header_enc or "无")


def title_of(text):
    m = _TITLE.search(text)
    return _TAG.sub("", m.group(1)).strip()[:48] if m else "（无 title）"


def try_url(url, archive=True):
    """访问单个 URL，返回诊断字典。"""
    time.sleep(MIN_INTERVAL)  # 请求间隔 ≥ 2 秒
    info = {"url": url, "ok": False}
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        info["note"] = "%s：%s" % (exc.__class__.__name__, str(exc)[:70])
        return info
    info["status"] = resp.status_code
    info["final_url"] = resp.url
    info["bytes"] = len(resp.content)
    if resp.status_code != 200:
        info["note"] = "HTTP %d" % resp.status_code
        return info
    text, enc, declared = decode(resp, url)
    info.update({"ok": True, "text": text, "encoding": enc, "declared": declared,
                 "title": title_of(text)})
    if archive:
        path = raw_path(url, subdir="dr06")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        info["archive"] = os.path.relpath(path, _ROOT).replace("\\", "/")
    return info


def check(source, archive=True):
    """按候选顺序尝试，首个可达者为主入口。"""
    print("\n[%s] %s" % (source["id"], source["name"]))
    primary, backups = None, []
    for url in source["urls"]:
        info = try_url(url, archive=archive and primary is None)
        if info["ok"]:
            info["structure"] = source["probe"](info["text"])
            print("  可达 %-62s %d 字节" % (url, info["bytes"]))
            print("       标题：%s" % info["title"])
            print("       编码：%s（声明 %s）" % (info["encoding"], info["declared"]))
            print("       结构：%s" % info["structure"])
            if info.get("archive"):
                print("       留档：%s" % info["archive"])
            if primary is None:
                primary = info
            else:
                backups.append(info)
        else:
            print("  不可达 %-60s %s" % (url, info.get("note", "")))
            backups.append(info)
    if primary is None:
        print("  ！全部候选入口均不可达")
    return {"source": source, "primary": primary, "backups": backups}


def main():
    parser = argparse.ArgumentParser(description="DR-06 数据源入口复核")
    parser.add_argument("--no-archive", action="store_true", help="只诊断不留档")
    args = parser.parse_args()

    print("=" * 100)
    print("DR-06 数据源入口复核  UA=常规浏览器  间隔 ≥%.0f 秒  留档=%s"
          % (MIN_INTERVAL, "否" if args.no_archive else "data/raw/dr06/"))
    print("=" * 100)
    results = [check(s, archive=not args.no_archive) for s in SOURCES]

    print("\n" + "=" * 100)
    reachable = [r for r in results if r["primary"]]
    print("复核结果：%d/%d 个数据源有可达入口" % (len(reachable), len(results)))
    for r in results:
        p = r["primary"]
        print("  %-7s %-34s %s" % (r["source"]["id"], r["source"]["name"][:32],
                                   "可达（%s）" % p["encoding"] if p else "全部候选不可达"))
    return 0 if len(reachable) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
