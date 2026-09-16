# -*- coding: utf-8 -*-
"""
DR-01《中国共产党一百年大事记》采集（V3 3.2 Step B）。

职责只有抓取与留档：把全文页原样存入 data/raw/dsj/，解析交由
kg/extract/parse_events.py，保证解析可离线重跑而不必二次抓取（FRS 3.1 采集纪律）。

入口 URL 以 data/sources.md 的 DR-06 复核结论为准；备用镜像在主入口不可达时启用。

用法（项目根目录）：
    python -m kg.crawler.dsj_crawler          # 已留档则直接复用
    python -m kg.crawler.dsj_crawler --force  # 强制重抓
"""
import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import fetch, raw_path  # noqa: E402

SUBDIR = "dsj"
# DR-06 实测：主入口为人民网全文页（GBK）；求是网为同一新华社受权发布全文（UTF-8）
URLS = [
    "http://cpc.people.com.cn/n1/2021/0628/c64387-32142446.html",
    "https://www.qstheory.cn/yaowen/2021-06/28/c_1127603704.htm",
]


def crawl(force=False):
    """依次尝试候选入口，返回 [(url, 留档路径, 字节数)]；首个成功即返回。"""
    results, errors = [], []
    for url in URLS:
        try:
            html = fetch(url, subdir=SUBDIR, force=force)
        except Exception as exc:  # noqa: BLE001 —— 逐个候选尝试，全失败才报错
            errors.append("%s：%s" % (url, exc.__class__.__name__))
            continue
        results.append((url, raw_path(url, SUBDIR), len(html)))
        break
    if not results:
        raise RuntimeError("全部候选入口均不可达：%s" % "；".join(errors))
    return results


def main():
    parser = argparse.ArgumentParser(description="DR-01 大事记全文采集")
    parser.add_argument("--force", action="store_true", help="忽略已有留档，强制重新抓取")
    args = parser.parse_args()

    for url, path, size in crawl(force=args.force):
        print("已留档 %s" % os.path.relpath(path, _ROOT).replace("\\", "/"))
        print("  来源 %s" % url)
        print("  正文 %d 字符" % size)
    print("\n下一步：python -m kg.extract.parse_events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
