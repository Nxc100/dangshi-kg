# -*- coding: utf-8 -*-
"""
DR-13 自动实体构建（V3 3.4 第 1 步「规则自动抽取」的实体侧产物）。

输入：DR-01 大事记条目 data/clean/events_raw.csv 与 DR-12 天天读条目 data/clean/ttd_raw.csv
      —— 两者均为「确切日期 + 权威表述」的编年条目，字段已对齐。
产出：data/clean/entities_auto.csv，由 db/build_seed.py 并入 Excel 与种子数据同门校验。

名称策略（本模块的正确性基础）——**整句成名，绝不在句中截取片段**：
  · 事件名 = 条目首句去掉日期前缀后的**完整表述**，长度越界即整条弃用，不做截断；
    这与《中国共产党一百年大事记》的条目标题写法一致，读起来即是一条史实。
  · 组织 / 地点 = 分词结果中以机构后缀、政区后缀收尾的完整词（见 lexicon）。
  · 文献 = 书名号内的完整跨度。
  · 人物 **不自动产出**（理由见 lexicon 模块注释），由 db/seed_data 人工登记。

简介（intro）约定：自动池实体的 intro 一律取其**首次出现的原文句，逐字引用**，
并在 source 记下该条目的来源 URL；不生成任何原文之外的表述。checked 一律为 0，
待 V3 3.6 人工校验时改写为正式简介并置 1。

用法（项目根目录）：python -m kg.extract.build_entities [--sample 20]
"""
import argparse
import csv
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import write_csv  # noqa: E402
from kg.extract import lexicon  # noqa: E402

SOURCES = (os.path.join(_ROOT, "data", "clean", "events_raw.csv"),
           os.path.join(_ROOT, "data", "clean", "ttd_raw.csv"))
OUT_CSV = os.path.join(_ROOT, "data", "clean", "entities_auto.csv")
FIELDS = ["label", "name", "alias", "time_text", "content", "intro",
          "org_type", "doc_type", "found_time_text", "pub_time_text",
          "modern_name", "source", "checked"]

NAME_MIN, NAME_MAX = 8, 50
CONTENT_MAX = 900
MIN_MENTIONS = 2  # 组织 / 地点须在至少两条独立条目中出现
SENTENCE_END = re.compile(r"[。！？；]")
# 条目正文常残留日期前缀（「-翌年3月　」「8月　」「1990年1月18日 」），逐段剥离到正文为止
LEAD_TOKEN = re.compile(
    r"^(?:[-—－~至]|[\s　,，、]"
    r"|(?:1[89]|20)\d{2}年|\d{1,2}月|\d{1,2}日"
    r"|翌年|本年|同年|次年|上半年|下半年|年初|年底|年末|春|夏|秋|冬"
    r"|午夜|凌晨|清晨|上午|中午|下午|傍晚|晚间|夜间|前夕"
    r"|上旬|中旬|下旬|月初|月底|月末|初|底)")
# 以状语连词开头说明主句在后，整句成名会得到残缺表述，弃用
# 以状语连词或指代词开头说明主句 / 先行词在别处，整句成名会得到无主语的残缺表述
LEAD_BAD = re.compile(
    r"^(经|据|根据|为了|为|由于|随着|按照|鉴于|其中|同日|当日|是日"
    r"|这|该|其|此|上述|另|又|并|但|而|他|她|它|他们|她们|它们|双方|大家|与会)")
# 以连词、助词收尾说明句子被引号或括号打断
TAIL_BAD = re.compile(r"(的|和|与|及|、|，|等|是|在|把|被|对|向|从|到|以)$")
DOC_SPAN = re.compile(r"《([^《》]{2,60})》")
# 组织 / 地点分词取自 jieba 词性标注，再过 lexicon 的后缀闸门
ORG_TAGS, PLACE_TAGS = ("nt", "nz", "n", "j"), ("ns", "nz")


def load_entries():
    """读入两个编年条目源，统一为 (年份, 日期原文, 正文, 时间原文, 来源URL)。"""
    entries = []
    for path in SOURCES:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                year, date = row["年份"].strip(), row["日期原文"].strip()
                time_text = "%s年%s" % (year, date) if date and date[0].isdigit() else "%s年" % year
                entries.append((year, date, row["条目正文"].strip(), time_text, row["来源URL"]))
    return entries


def strip_lead(text):
    """反复剥去开头的日期与时段标记，直到剩下正文本身。"""
    while True:
        m = LEAD_TOKEN.match(text)
        if not m or m.end() == 0:
            return text
        text = text[m.end():]


def event_name(body):
    """取首句为事件名；越界或残缺一律返回 None（宁可少收，不做截断）。"""
    head = strip_lead(body)
    name = SENTENCE_END.split(head)[0].strip().rstrip("，,、")
    if "：" in name or ":" in name:
        return None  # 冒号后是引语，整句成名会把引语头截进来
    if not (NAME_MIN <= len(name) <= NAME_MAX):
        return None
    if LEAD_BAD.match(name) or TAIL_BAD.search(name):
        return None
    if name.count("《") != name.count("》") or name.count("(") != name.count(")"):
        return None
    return name


def collect_events(entries, store):
    """条目 → Event。同名条目保留最早一条，后续正文追加到 content。"""
    named = 0
    for _, _, body, time_text, url in entries:
        name = event_name(body)
        if not name:
            continue
        named += 1
        row = store.setdefault(name, {
            "label": "Event", "name": name, "time_text": time_text,
            "content": body[:CONTENT_MAX], "intro": body[:CONTENT_MAX], "source": url})
        if row["label"] == "Event" and body[:CONTENT_MAX] not in row["content"]:
            row["content"] = (row["content"] + " " + body)[:CONTENT_MAX]
    return named


def collect_documents(entries, store):
    """书名号跨度 → Document，首次出现句作 intro。"""
    for _, _, body, time_text, url in entries:
        for name in (n.strip() for n in DOC_SPAN.findall(body)):
            if not lexicon.is_document(name) or name in store:
                continue
            store[name] = {"label": "Document", "name": name,
                           "doc_type": lexicon.doc_type_of(name),
                           "pub_time_text": time_text,
                           "intro": SENTENCE_END.split(body)[0][:CONTENT_MAX], "source": url}


def collect_named(entries, store):
    """
    分词结果中过后缀闸门的组织与地点。

    另加**出现次数 ≥ MIN_MENTIONS** 的闸门：只出现一次的多为分词偶发切分，
    在多条独立条目中反复出现才说明它是一个稳定专名。
    """
    import jieba.posseg as pseg

    hits = {}
    for _, _, body, _, url in entries:
        first = SENTENCE_END.split(body)[0][:CONTENT_MAX]
        for word, flag in pseg.cut(body):
            if word in store:
                continue
            if flag in ORG_TAGS and lexicon.is_org(word):
                label = "Organization"
            elif flag in PLACE_TAGS and lexicon.is_place(word):
                label = "Location"
            else:
                continue
            slot = hits.setdefault(word, [label, 0, first, url])
            slot[1] += 1
    for word, (label, count, first, url) in hits.items():
        if count < MIN_MENTIONS:
            continue
        if label == "Organization":
            store[word] = {"label": label, "name": word, "org_type": org_type_of(word),
                           "intro": first, "source": url}
        else:
            store[word] = {"label": label, "name": word, "source": url}


ORG_TYPE_RULES = (
    (re.compile(r"(军|师|旅|纵队|支队|大队|中队|方面军|兵团|军区|军团|司令部|政治部)$"), "军队"),
    (re.compile(r"(总工会|联合会|工会|妇联|共青团|青年团|学联|商会|协会|盟)$"), "群团"),
    (re.compile(r"(共产党|国民党|民主党|致公党|民盟|民革|民进|农工党|九三学社)$"), "政党"),
)
ORG_TYPE_DEFAULT = "机构"


def org_type_of(name):
    """按后缀判定组织类型（ontology Organization.org_type 枚举）。"""
    for pattern, value in ORG_TYPE_RULES:
        if pattern.search(name):
            return value
    return ORG_TYPE_DEFAULT


def build(entries):
    """按「事件 → 文献 → 组织/地点」顺序构建，先登记者占用该主名（跨标签唯一）。"""
    store = {}
    named = collect_events(entries, store)
    collect_documents(entries, store)
    collect_named(entries, store)
    return store, named


def main():
    parser = argparse.ArgumentParser(description="DR-13 自动实体构建")
    parser.add_argument("--sample", type=int, default=0, help="打印每类前 N 条样本")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        print("未找到编年条目，请先执行 kg.extract.parse_events 与 kg.extract.parse_ttd")
        return 1

    store, named = build(entries)
    rows = sorted(store.values(), key=lambda r: (r["label"], r["name"]))
    for row in rows:
        row.setdefault("checked", 0)
    write_csv(OUT_CSV, rows, FIELDS)

    from collections import Counter
    counter = Counter(r["label"] for r in rows)
    print("\nDR-13 自动实体构建")
    print("  输入条目 %d，其中可整句成名 %d（%.1f%%）" % (len(entries), named, named * 100.0 / len(entries)))
    for label in ("Event", "Organization", "Location", "Document"):
        print("  %-14s %5d" % (label, counter.get(label, 0)))
    print("  合计 %d 个自动实体（checked=0，待 3.6 校验）" % len(rows))
    if args.sample:
        for label in ("Event", "Organization", "Location", "Document"):
            picks = [r["name"] for r in rows if r["label"] == label][:args.sample]
            print("\n  %s 样本：" % label)
            for name in picks:
                print("    %s" % name)
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
