# -*- coding: utf-8 -*-
"""
DR-10 F9 兜底语料库构建（V3 3.2 Step D / 规范 7.3）。

来源与优先级（重复段落保留先者）：
  1)《中国共产党简史》分章正文（DR-04，data/raw/jianshi/）—— 主体语料，章节出处清晰；
  2) 党史人物专页生平（DR-03，data/raw/person/）；
  3) 历次党代会专页（DR-02，data/raw/meeting/）；
  4) 大事记编年条目（DR-01，data/clean/events_raw.csv）—— 补足全程史实覆盖，
     章节标注为「一百年大事记·YYYY 年」。

切分规则：按自然段切分，滤除 < 30 字的段落（V3 3.2 Step D）；去重后写入
data/corpus/paragraphs.csv，字段 text / chapter / source，以 utf-8-sig 落盘。

语料不提供在线编辑，更新走本脚本重建 + 重启服务（规范 7.3）。

用法（项目根目录）：python -m kg.extract.build_corpus [--min-len 30]
"""
import argparse
import csv
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import soup, write_csv  # noqa: E402
from kg.crawler.jianshi_crawler import SUBDIR as JIANSHI_DIR  # noqa: E402
from kg.extract.clean import clean_text  # noqa: E402

OUT_CSV = os.path.join(_ROOT, "data", "corpus", "paragraphs.csv")
EVENTS_CSV = os.path.join(_ROOT, "data", "clean", "events_raw.csv")
RAW_DIR = os.path.join(_ROOT, "data", "raw", JIANSHI_DIR)
FIELDS = ["text", "chapter", "source"]

MIN_LEN = 30
CHAPTER_TITLE = re.compile(r"(第[一二三四五六七八九十]+章[^\r\n]{0,40})")
# 页面导航与版权尾注等非正文文本
NOISE = re.compile(r"(上一篇|下一篇|打印|关闭|责任编辑|来源：|分享到|字体：|扫一扫|版权所有)")


# 章节标题后常跟「时间:2021-03-19」「来源：xxx」等页面元信息，须剔除后再作为出处展示
CHAPTER_TAIL = re.compile(r"\s*(时间|来源|作者|发布日期|字号)\s*[:：].*$")


def _chapter_of(dom, fallback):
    """取章节标题作为语料出处；标题在 h1/h2/title 中择一，并剥离尾部页面元信息。"""
    for sel in ("h1", "h2", ".title", "title"):
        node = dom.select_one(sel)
        if not node:
            continue
        m = CHAPTER_TITLE.search(clean_text(node.get_text(" ", strip=True)))
        if m:
            return CHAPTER_TAIL.sub("", m.group(1)).strip()
    return fallback


def from_jianshi(min_len):
    """从留档的分章页提取正文段落。"""
    if not os.path.isdir(RAW_DIR):
        return []
    rows = []
    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".html"):
            continue
        path = os.path.join(RAW_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            dom = soup(f.read())
        for tag in dom(["script", "style"]):
            tag.decompose()
        chapter = _chapter_of(dom, "《中国共产党简史》")
        if not CHAPTER_TITLE.search(chapter):
            continue  # 目录页等非正文页
        for p in dom.find_all("p"):
            text = clean_text(p.get_text(" ", strip=True))
            if len(text) < min_len or NOISE.search(text):
                continue
            rows.append({"text": text, "chapter": chapter,
                         "source": "《中国共产党简史》· 中共中央对外联络部党史学习平台"})
    return rows


def from_pages(subdir, chapter_prefix, source_label, min_len, max_per_page=0):
    """
    从留档目录提取正文段落的通用实现（人物专页 DR-03 / 党代会专页 DR-02）。

    这两类页面的正文散落在多个 <p> 中且混有导航文本，故按噪声正则过滤后再收集；
    chapter 用「前缀 · 页面标题」标注，保证每段可溯源到具体页面。
    """
    raw_dir = os.path.join(_ROOT, "data", "raw", subdir)
    if not os.path.isdir(raw_dir):
        return []
    rows = []
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".html"):
            continue
        with open(os.path.join(raw_dir, filename), "r", encoding="utf-8") as f:
            dom = soup(f.read())
        for tag in dom(["script", "style"]):
            tag.decompose()
        title = clean_text(dom.title.get_text()) if dom.title else ""
        title = re.split(r"[-_|]{1,2}", title)[0].strip()[:24] or subdir
        picked = 0
        for p in dom.find_all("p"):
            text = clean_text(p.get_text(" ", strip=True))
            if len(text) < min_len or NOISE.search(text):
                continue
            rows.append({"text": text,
                         "chapter": "%s·%s" % (chapter_prefix, title),
                         "source": source_label})
            picked += 1
            if max_per_page and picked >= max_per_page:
                break
    return rows


def from_events(min_len):
    """把大事记条目作为补充语料，章节标注到年份。"""
    if not os.path.exists(EVENTS_CSV):
        return []
    rows = []
    with open(EVENTS_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for item in csv.DictReader(f):
            body = (item.get("条目正文") or "").strip()
            if not body:
                continue
            date = (item.get("日期原文") or "").strip()
            year = (item.get("年份") or "").strip()
            # 先拼出入库文本再判长度：条目正文虽短，补上「YYYY年X月X日，」后多数已达阈值，
            # 且带时间的表述对 TF-IDF 检索更有用（否则会漏掉李大钊就义等短条目）
            text = "%s年%s，%s" % (year, date, body) if date and date[0].isdigit() else body
            if len(text) < min_len:
                continue
            rows.append({
                "text": text,
                "chapter": "《中国共产党一百年大事记》· %s年" % year,
                "source": item.get("来源URL") or "",
            })
    return rows


def dedup(rows):
    """按正文去重，保留首次出现（简史正文优先于大事记补充）。"""
    seen, out = set(), []
    for row in rows:
        key = row["text"]
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description="DR-10 F9 兜底语料库构建")
    parser.add_argument("--min-len", type=int, default=MIN_LEN, help="段落最短字数，默认 30")
    args = parser.parse_args()

    jianshi = from_jianshi(args.min_len)
    persons = from_pages("person", "党史人物", "人民网·党史人物纪念馆", args.min_len)
    meetings = from_pages("meeting", "历次党代会", "共产党员网·历次党代会专题",
                          args.min_len)
    events = from_events(args.min_len)
    # 顺序即优先级：同一段重复出现时保留先者（简史正文 > 人物 > 党代会 > 大事记）
    rows = dedup(jianshi + persons + meetings + events)
    if not rows:
        print("未产出任何段落，请先执行 kg.crawler.jianshi_crawler 与 kg.extract.parse_events")
        return 1

    write_csv(OUT_CSV, rows, FIELDS)
    lengths = [len(r["text"]) for r in rows]
    print("\nDR-10 语料构建结果")
    print("  《简史》分章正文  %5d 段" % len(jianshi))
    print("  党史人物专页      %5d 段" % len(persons))
    print("  历次党代会专页    %5d 段" % len(meetings))
    print("  大事记条目补充    %5d 段" % len(events))
    print("  去重后合计        %5d 段（验收线 ≥ 2000，%s）"
          % (len(rows), "达标" if len(rows) >= 2000 else "未达标"))
    print("  段落长度 最短 %d / 最长 %d / 平均 %d 字"
          % (min(lengths), max(lengths), sum(lengths) // len(lengths)))
    chapters = {r["chapter"] for r in rows}
    print("  出处标注 %d 种，全部段落含出处：%s"
          % (len(chapters), all(r["chapter"] and r["source"] for r in rows)))
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    print("提示：语料在服务启动时构建 TF-IDF 矩阵，重建后需重启后端生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
