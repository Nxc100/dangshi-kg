# -*- coding: utf-8 -*-
"""
数据对功能的支撑度核查（V3 6.4 / FRS 第四章的数据前置条件）。

用法（项目根目录）：venv\\Scripts\\python -m eval.data_capability

verify.py 回答的是「数据量够不够」，本脚本回答的是「这些数据能不能把功能跑起来」：

  一、15 类意图 —— 逐条统计**有多少实体能让该意图查出非空结果**（可答实体数），
      并给出占该意图所涉实体类型总数的比例。比例为 0 的意图等于该功能没有数据可用。
  二、F7 测验 6 个题型 —— 每个题型在 checked=1 核心池里能出多少道题；
      任一题型可出题数为 0，则 F7 的题型覆盖不完整。
  三、F5 百科 / F6 时间轴 / F8 每日推荐 / F9 兜底 —— 各自的数据前置条件。

每项都对照 THRESHOLD 给出达标结论；不修改任何数据。
退出码：0 = 全部功能都有数据支撑，否则 1。
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from qa.intent_rules import INTENT_ZH  # noqa: E402

# 每类意图的「可答实体」计数口径：(涉及的实体类型, 判定该实体可答的 Cypher 片段)
# 片段里的 n 即候选实体，WHERE 条件成立即认为该意图对它能给出非空答案。
INTENT_PROBE = {
    "I1": (("Meeting", "n.time_text IS NOT NULL"), ("Event", "n.time_text IS NOT NULL"),
           ("Organization", "n.found_time_text IS NOT NULL"),
           ("Document", "n.pub_time_text IS NOT NULL")),
    "I2": (("Meeting", "(n)-[:HELD_IN]->(:Location)"), ("Event", "(n)-[:OCCURRED_IN]->(:Location)")),
    "I3": (("Meeting", "n.content IS NOT NULL"), ("Event", "n.content IS NOT NULL")),
    "I4": (("Meeting", "n.meaning IS NOT NULL"), ("Event", "n.meaning IS NOT NULL")),
    "I5": (("Event", "(:Person)-[:LED]->(n) OR (:Organization)-[:LED]->(n)"),),
    "I6": (("Meeting", "(:Person)-[:PARTICIPATED_IN]->(n)"),),
    "I7": (("Document", "(:Person)-[:AUTHORED]->(n)"),),
    "I8": (("Person", "(n)-[:AUTHORED]->(:Document)"),),
    "I9": (("Person", "(n)-[:LED]->(:Event)"),),
    "I10": (("Period", "(:Event)-[:BELONGS_TO]->(n) OR (:Meeting)-[:BELONGS_TO]->(n)"),),
    "I11": (("Organization", "(n)-[:REORGANIZED_TO]-(:Organization)"),),
    "I12": (("Person", "(n)-[:HELD_POSITION]->(:Organization)"),),
    "I13": tuple((label, "n.name IS NOT NULL") for label in O.LABELS),
    "I14": (("Meeting", "(:Person)-[:PARTICIPATED_IN]->(n)"),),
    "I15": (("Document", "(:Person)-[:AUTHORED]->(n)"),),
}

# 各意图可答实体数的下限。定在「够撑起该功能的演示与测验」的量级，不追求全覆盖：
# 单跳属性类意图要求百位数，关系类与两跳类要求两位数（关系抽取本就只取有触发词的）。
THRESHOLD = {"I1": 500, "I2": 100, "I3": 500, "I4": 20, "I5": 20, "I6": 10, "I7": 30,
             "I8": 10, "I9": 10, "I10": 7, "I11": 2, "I12": 5, "I13": 1000,
             "I14": 10, "I15": 30}
QUIZ_MIN = 5          # 每个题型至少能出的题数
DAILY_MIN = 30        # 每日推荐池下限（F8 按日轮换，池子太小会很快重复）
CORPUS_MIN = 2000     # F9 语料段落下限（V3 3.7）


def _fmt(ok):
    return "达标" if ok else "**不足**"


def count_answerable(run_read, probes):
    """按探针统计可答实体数与该类型实体总数。"""
    answerable = total = 0
    for label, condition in probes:
        rows = run_read("MATCH (n:%s) RETURN count(n) AS total, "
                        "count(CASE WHEN %s THEN 1 END) AS hit" % (label, condition))
        total += int(rows[0]["total"])
        answerable += int(rows[0]["hit"])
    return answerable, total


def check_intents(run_read):
    """15 类意图的可答实体数。"""
    print("=== 一、15 类意图的数据支撑 ===")
    print("  %-5s %-16s %10s %10s %8s %s" % ("意图", "名称", "可答实体", "涉及实体", "下限", "结论"))
    weak = []
    for intent in sorted(INTENT_PROBE, key=lambda k: int(k[1:])):
        answerable, total = count_answerable(run_read, INTENT_PROBE[intent])
        floor = THRESHOLD[intent]
        ok = answerable >= floor
        if not ok:
            weak.append((intent, answerable, floor))
        print("  %-5s %-16s %10d %10d %8d %s"
              % (intent, INTENT_ZH[intent], answerable, total, floor, _fmt(ok)))
    return weak


def check_quiz(run_read):
    """F7 六个题型在核心池里各能出多少题。"""
    from backend.services import quiz_service

    print("=== 二、F7 测验题型覆盖（只从 checked=1 核心池取数）===")
    weak = []
    for key, tpl in quiz_service.TEMPLATES.items():
        rows = run_read(tpl["cypher"])
        count = len(rows)
        ok = count >= QUIZ_MIN
        if not ok:
            weak.append((key, count, QUIZ_MIN))
        print("  %-4s %-22s 可出题 %5d 道（下限 %d）%s"
              % (key, tpl.get("zh") or tpl.get("stem", "")[:20], count, QUIZ_MIN, _fmt(ok)))
    return weak


def check_features(run_read):
    """F5 百科 / F6 时间轴 / F8 推荐 / F9 兜底的数据前置条件。"""
    from qa import fallback

    print("=== 三、其余功能的数据前置条件 ===")
    weak = []

    total = int(run_read("MATCH (n) RETURN count(n) AS c")[0]["c"])
    with_intro = int(run_read(
        "MATCH (n) WHERE n.intro IS NOT NULL AND n.intro <> '' RETURN count(n) AS c")[0]["c"])
    linked = int(run_read("MATCH (n) WHERE (n)--() RETURN count(n) AS c")[0]["c"])
    print("  F5 百科  有简介 %d/%d = %.1f%%；有关联边（子图非空）%d/%d = %.1f%%"
          % (with_intro, total, with_intro * 100.0 / total,
             linked, total, linked * 100.0 / total))

    print("  F6 时间轴 七个时期的事件分布：")
    for period in O.PERIODS:
        c = int(run_read("MATCH (e)-[:BELONGS_TO]->(:Period {name:$n}) RETURN count(e) AS c",
                         n=period["name"])[0]["c"])
        if c == 0:
            weak.append(("F6 时期「%s」" % period["name"], 0, 1))
        print("    %-26s %5d 条" % (period["name"], c))

    pool = int(run_read("MATCH (n) WHERE n.checked = 1 AND n.intro IS NOT NULL "
                        "AND n.intro <> '' RETURN count(n) AS c")[0]["c"])
    ok = pool >= DAILY_MIN
    if not ok:
        weak.append(("F8 推荐池", pool, DAILY_MIN))
    print("  F8 推荐  核心池中带简介的实体 %d 个（下限 %d）%s" % (pool, DAILY_MIN, _fmt(ok)))

    fallback.build()
    size = fallback.size()
    ok = size >= CORPUS_MIN
    if not ok:
        weak.append(("F9 语料", size, CORPUS_MIN))
    print("  F9 兜底  语料 %d 段（下限 %d）%s" % (size, CORPUS_MIN, _fmt(ok)))
    return weak


def main():
    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_status, run_read

    app = create_app(load_resources=False)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            return 1
        weak = check_intents(run_read)
        weak += check_quiz(run_read)
        weak += check_features(run_read)

    print("=== 结论 ===")
    if not weak:
        print("  15 类意图、6 个题型与 F5/F6/F8/F9 均有足量数据支撑。")
        return 0
    print("  以下 %d 项数据不足，需补数据或调整抽取规则：" % len(weak))
    for name, got, floor in weak:
        print("    %-24s 实测 %d，下限 %d" % (name, got, floor))
    return 1


if __name__ == "__main__":
    sys.exit(main())
