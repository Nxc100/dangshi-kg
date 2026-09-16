# -*- coding: utf-8 -*-
"""
核心实体池交叉复核（V3 3.6「校验方式 + 交叉复核」环节的机械化实现）。

用法（项目根目录）：venv\\Scripts\\python -m eval.core_check [--list 40]

复核对象：data/excel/ 六张实体表中 checked=1 的全部行（即核心池）。
复核方法——**逐条回到留档原文找证据**，而不是相信表里写了什么。结论分三档：

  通过    主名或别名在留档语料中确有出现，且没有与原文冲突的属性；
  待补源  主名与别名均未见于留档语料。不算错，但按「每条知识可溯源」不得进核心池，
          应在 db/seed_data/core_pool.py 的 UNSOURCED 中登记，或补充数据源后再入池；
  不一致  属性与原文**直接冲突**，属必须清零的错误（V3 3.6：交叉复核错误数为 0）：
            · 人物生卒年与原文「（1893—1976）」式表述不符；
            · source 不是可溯源链接。

另设一档只报不拦的提示「无时间佐证」：事件 / 会议声明的年份，未在任何提到该实体的
原文中出现。它不等于写错——权威编年条目常把年份写在段落之外（如党代会专题页只写
「10月16日在人民大会堂开幕」），故不作为拦截条件，只提示该条的时间尚缺同段佐证。

退出码：0 = 无不一致且核心池内无待补源项；否则 1。本脚本不修改任何数据。
"""
import argparse
import csv
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from qa.dictionary import split_alias  # noqa: E402

EXCEL_DIR = os.path.join(_ROOT, "data", "excel")
CORPUS_CSV = os.path.join(_ROOT, "data", "corpus", "paragraphs.csv")
ENTRY_CSVS = (os.path.join(_ROOT, "data", "clean", "events_raw.csv"),
              os.path.join(_ROOT, "data", "clean", "ttd_raw.csv"))
SHEET_OF = {"Person": "person.xlsx", "Organization": "organization.xlsx",
            "Event": "event.xlsx", "Meeting": "meeting.xlsx",
            "Location": "location.xlsx", "Document": "document.xlsx"}
YEAR = re.compile(r"(1[89]\d{2}|20\d{2})")
LIFE_SPAN = re.compile(r"[（(](1[89]\d{2})\s*[—\-－~～]\s*(1[89]\d{2}|20\d{2})[)）]")
URL = re.compile(r"^https?://")

UNSOURCED, INCONSISTENT, NO_TIME = "待补源", "不一致", "无时间佐证"
UNSOURCED_PY = os.path.join(_ROOT, "db", "seed_data", "core_unsourced.py")
UNSOURCED_DOC = [
    "# -*- coding: utf-8 -*-",
    '"""',
    "留档语料未覆盖的实体名单（由 eval/core_check.py --emit 生成，勿手改）。",
    "",
    "这些实体本身是党史常识，但其主名与别名在当前留档语料（data/corpus 与 data/clean）中",
    "一次也没出现。按数据红线「每条知识可溯源」，它们**不计入核心池**：",
    "db/merge_sources.py 合并时把这些行的 checked 置 0，实体本身仍然入库可查。",
    "补充能覆盖它们的数据源后重跑复核，名单会自动收缩。",
    '"""',
    "",
    "UNSOURCED = [",
]


def emit_unsourced(findings):
    """把「待补源」名单写成模块，供 db/merge_sources.py 在合并时降级。"""
    names = sorted({name for tier, _, name, _ in findings if tier == UNSOURCED})
    lines = list(UNSOURCED_DOC)
    lines.extend('    "%s",' % name for name in names)
    lines.append("]")
    with open(UNSOURCED_PY, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return len(names)


def load_evidence():
    """
    返回全部留档段落（F9 语料 + 两份编年条目，条目前缀带年月日），
    用于判定「该实体是否被原文提到」与「声明的年份是否有同段佐证」。
    """
    texts = []
    if os.path.exists(CORPUS_CSV):
        with open(CORPUS_CSV, "r", encoding="utf-8-sig", newline="") as f:
            texts.extend(row["text"] for row in csv.DictReader(f))
    for path in ENTRY_CSVS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                texts.append("%s年%s %s" % (row["年份"], row["日期原文"], row["条目正文"]))
    return texts


class Evidence(object):
    """留档证据。按关键词线性扫描——核心池只有数百条，无需建倒排索引。"""

    def __init__(self, texts):
        self.texts = texts

    def mentions(self, keys):
        return [t for t in self.texts if any(k and k in t for k in keys)]


def current_unsourced():
    """当前已登记的待补源名单（本轮生成前的旧名单）。"""
    try:
        from db.seed_data.core_unsourced import UNSOURCED as names
    except ImportError:
        return frozenset()
    return frozenset(names)


def load_checked_rows(include_demoted=False):
    """
    读 data/excel 六表，返回核心池的行（附标签）。

    默认只取 checked=1。`include_demoted` 为真时额外纳入已被降级的那些行——
    生成降级名单必须在「候选核心池」上求值，否则会与上一轮的降级结果互相抵消：
    上一轮降级后它们 checked=0，本轮就查不到，名单被清空，下一轮又被提回来。
    """
    import pandas as pd

    demoted = current_unsourced() if include_demoted else frozenset()
    rows = []
    for label, filename in SHEET_OF.items():
        path = os.path.join(EXCEL_DIR, filename)
        if not os.path.exists(path):
            continue
        frame = pd.read_excel(path).fillna("")
        for record in frame.to_dict("records"):
            if int(record.get("checked") or 0) == 1 or str(record.get("name")) in demoted:
                record["_label"] = label
                rows.append(record)
    return rows


def check_row(row, evidence):
    """复核一行，返回 (档位, 问题描述列表)；档位为 None 表示通过。"""
    label, name = row["_label"], str(row["name"]).strip()
    keys = [name] + split_alias(row.get("alias"))

    if not URL.match(str(row.get("source") or "").strip()):
        return INCONSISTENT, ["source 不是可溯源链接"]

    hits = evidence.mentions(keys)
    if not hits:
        return UNSOURCED, ["主名与别名均未见于留档语料"]

    if label == "Person":
        issues = _check_life(row, hits)
        return (INCONSISTENT, issues) if issues else (None, [])
    if label in ("Event", "Meeting"):
        issues = _check_time(row, hits)
        return (NO_TIME, issues) if issues else (None, [])
    return None, []


def _check_time(row, hits):
    """声明年份是否在提到该实体的原文中出现过（只提示，不拦截）。"""
    declared = YEAR.search(str(row.get("time_text") or ""))
    if not declared:
        return ["time_text 中无法识别年份：%s" % row.get("time_text")]
    if not any(declared.group(1) in text for text in hits):
        return ["年份 %s 未在提到该实体的原文中出现" % declared.group(1)]
    return []


def _check_life(row, hits):
    """人物：若填了生卒年，检查原文中的「（生—卒）」表述是否与之冲突。"""
    born, died = str(row.get("birth_year") or ""), str(row.get("death_year") or "")
    if not born:
        return []
    born = born.split(".")[0]
    for text in hits:
        for match in LIFE_SPAN.finditer(text):
            if match.group(1) != born:
                return ["生年 %s 与原文表述 %s 不一致" % (born, match.group(0))]
            if died and match.group(2) != died.split(".")[0]:
                return ["卒年 %s 与原文表述 %s 不一致" % (died, match.group(0))]
    return []


def check_uniqueness(rows):
    """主名跨标签唯一、别名不指向多个主名。"""
    issues, owner, alias_owner = [], {}, {}
    for row in rows:
        name = str(row["name"]).strip()
        if name in owner and owner[name] != row["_label"]:
            issues.append("主名跨标签重复：%s（%s / %s）" % (name, owner[name], row["_label"]))
        owner[name] = row["_label"]
        for alias in split_alias(row.get("alias")):
            if alias in alias_owner and alias_owner[alias] != name:
                issues.append("别名一对多：%s → %s / %s" % (alias, alias_owner[alias], name))
            alias_owner[alias] = name
    return issues


def report(rows, findings, by_label, list_limit):
    print("  %-14s %6s %6s %6s %8s %8s"
          % ("类型", "核心池", "待补源", "不一致", "无时间佐证", "通过率"))
    for label in O.LABELS:
        if label not in by_label:
            continue
        total, unsourced, bad, no_time = by_label[label]
        print("  %-14s %6d %6d %6d %8d %7.1f%%"
              % (O.zh(label), total, unsourced, bad, no_time,
                 (total - unsourced - bad - no_time) * 100.0 / total))
    total = len(rows)
    n_unsourced = sum(1 for f in findings if f[0] == UNSOURCED)
    n_bad = sum(1 for f in findings if f[0] == INCONSISTENT)
    print("  %-14s %6d %6d %6d %8d %7.1f%%"
          % ("合计", total, n_unsourced, n_bad, len(findings) - n_unsourced - n_bad,
             (total - len(findings)) * 100.0 / total))
    for tier in (INCONSISTENT, UNSOURCED, NO_TIME):
        items = [f for f in findings if f[0] == tier]
        if not items:
            continue
        print("\n%s（%d 条，前 %d 条）：" % (tier, len(items), min(list_limit, len(items))))
        for _, label, name, issues in items[:list_limit]:
            print("  [%s] %-28s %s" % (O.zh(label), name[:26], "；".join(issues)))
    return n_unsourced, n_bad


def main():
    parser = argparse.ArgumentParser(description="V3 3.6 核心实体池交叉复核")
    parser.add_argument("--list", type=int, default=25, help="每档最多列出多少条")
    parser.add_argument("--emit", action="store_true",
                        help="把待补源名单写入 db/seed_data/core_unsourced.py")
    args = parser.parse_args()

    rows = load_checked_rows(include_demoted=args.emit)
    if not rows:
        print("未读到任何 checked=1 的实体，请先执行：python -m db.build_seed")
        return 1
    texts = load_evidence()
    if not texts:
        print("未读到留档语料，请先执行：python -m kg.extract.build_corpus")
        return 1

    evidence = Evidence(texts)
    findings, by_label = [], {}
    for row in rows:
        stat = by_label.setdefault(row["_label"], [0, 0, 0, 0])
        stat[0] += 1
        tier, issues = check_row(row, evidence)
        if tier:
            stat[{UNSOURCED: 1, INCONSISTENT: 2, NO_TIME: 3}[tier]] += 1
            findings.append((tier, row["_label"], str(row["name"]), issues))

    print("V3 3.6 核心实体池交叉复核（证据来源：%d 段留档原文）\n" % len(texts))
    n_unsourced, n_bad = report(rows, findings, by_label, args.list)
    if args.emit:
        print("\n已写出待补源名单 %d 条：%s"
              % (emit_unsourced(findings),
                 os.path.relpath(UNSOURCED_PY, _ROOT).replace("\\", "/")))
    extra = check_uniqueness(rows)
    print("\n唯一性复核：%s" % ("通过（主名跨标签唯一、别名无一对多）" if not extra else extra[:5]))
    print("结论：不一致 %d 条（要求 0），核心池内待补源 %d 条（要求 0）"
          % (n_bad, n_unsourced))
    return 1 if (n_bad or n_unsourced or extra) else 0


if __name__ == "__main__":
    sys.exit(main())
