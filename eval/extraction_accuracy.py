# -*- coding: utf-8 -*-
"""
自动抽取准确率抽样评估（V3 3.4 第 3 步，论文「数据处理」章素材）。

用法（项目根目录）：
    venv\\Scripts\\python -m eval.extraction_accuracy --sample    # 生成抽样单
    venv\\Scripts\\python -m eval.extraction_accuracy            # 按已判定的抽样单出报告

抽样口径（V3 3.4：随机抽 200 条人工判对错）：
  · 总体 = DR-13 自动实体（data/clean/entities_auto.csv）
           + DR-14 自动关系（data/clean/relations_auto.csv）；
  · 按两类在总体中的占比分配 200 个名额，组内用固定随机种子无放回抽样，
    换机器、换时间重跑得到同一份抽样单，评估结果可复现；
  · 抽样单落 data/clean/extraction_sample.csv，含「抽取结果 + 原文依据」两列，
    人工只需在「判定」列填 对 / 错，并可在「说明」列写明错因。

判定口径（写清楚才有可比性）：
  实体「对」—— 名称是原文中一个边界完整的表述，类型判定正确；
              名称被截断、跨越了句子成分、或类型张冠李戴均记「错」。
  关系「对」—— 原文确实表达了该三元组，且头尾实体对应正确；
              触发词命中但语义不成立（如把定语误当谓语）记「错」。

本脚本不修改抽取产物，只统计。
"""
import argparse
import csv
import os
import random
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from kg.crawler.common import write_csv  # noqa: E402

ENTITY_CSV = os.path.join(_ROOT, "data", "clean", "entities_auto.csv")
RELATION_CSV = os.path.join(_ROOT, "data", "clean", "relations_auto.csv")
SAMPLE_CSV = os.path.join(_ROOT, "data", "clean", "extraction_sample.csv")
FIELDS = ["序号", "类别", "抽取结果", "原文依据", "来源URL", "判定", "说明"]
SAMPLE_SIZE = 200
SEED = 20260916  # 固定种子：抽样单可复现
EVIDENCE_MAX = 120


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _entity_item(row):
    return {"类别": "实体·%s" % O.zh(row["label"]),
            "抽取结果": "%s（%s）" % (row["name"], O.zh(row["label"])),
            "原文依据": (row.get("content") or row.get("intro") or "")[:EVIDENCE_MAX],
            "来源URL": row.get("source", "")}


def _relation_item(row):
    return {"类别": "关系·%s" % O.zh(row["rel"]),
            "抽取结果": "(%s)-[%s%s]->(%s)" % (row["head"], O.zh(row["rel"]),
                                            "/" + row["position"] if row.get("position") else "",
                                            row["tail"]),
            "原文依据": "",  # 关系的依据即头实体所在条目，评估时回看来源 URL
            "来源URL": row.get("source", "")}


def build_sample(size=SAMPLE_SIZE):
    """按两类总体占比分配名额，组内固定种子无放回抽样。"""
    entities, relations = _read(ENTITY_CSV), _read(RELATION_CSV)
    total = len(entities) + len(relations)
    if not total:
        return [], (0, 0)
    n_rel = min(len(relations), max(1, round(size * len(relations) / total)))
    n_ent = min(len(entities), size - n_rel)
    rng = random.Random(SEED)
    picked = ([_entity_item(r) for r in rng.sample(entities, n_ent)]
              + [_relation_item(r) for r in rng.sample(relations, n_rel)])
    # 事件正文即关系的原文依据，补给关系行，省去人工再去翻留档
    content_of = {r["name"]: (r.get("content") or "") for r in entities}
    for item in picked:
        if not item["原文依据"] and item["抽取结果"].startswith("("):
            head = item["抽取结果"][1:].split(")-[")[0]
            item["原文依据"] = content_of.get(head, "")[:EVIDENCE_MAX]
    for index, item in enumerate(picked, 1):
        item["序号"] = index
        item.setdefault("判定", "")
        item.setdefault("说明", "")
    return picked, (n_ent, n_rel)


def report(rows):
    """按类别统计准确率；未判定的单列，不计入分母。"""
    stat = {}
    for row in rows:
        verdict = (row.get("判定") or "").strip()
        kind = row["类别"].split("·")[0]
        slot = stat.setdefault(kind, [0, 0, 0])  # 判对 / 判错 / 未判
        slot[0 if verdict == "对" else 1 if verdict == "错" else 2] += 1
    print("\n自动抽取准确率（V3 3.4 抽样评估，样本 %d 条）\n" % len(rows))
    print("  %-8s %6s %6s %6s %9s" % ("类别", "判对", "判错", "未判", "准确率"))
    judged_ok = judged = 0
    for kind in sorted(stat):
        ok, bad, todo = stat[kind]
        judged_ok += ok
        judged += ok + bad
        rate = "%.1f%%" % (ok * 100.0 / (ok + bad)) if ok + bad else "—"
        print("  %-8s %6d %6d %6d %9s" % (kind, ok, bad, todo, rate))
    rate = "%.1f%%" % (judged_ok * 100.0 / judged) if judged else "—"
    print("  %-8s %6d %6d %6d %9s"
          % ("合计", judged_ok, judged - judged_ok, len(rows) - judged, rate))
    wrong = [r for r in rows if (r.get("判定") or "").strip() == "错"]
    if wrong:
        print("\n错例（前 10 条，供论文错因分析）：")
        for row in wrong[:10]:
            print("  [%s] %s —— %s" % (row["类别"], row["抽取结果"][:40],
                                      row.get("说明") or "未填错因"))
    return judged, judged_ok


def main():
    parser = argparse.ArgumentParser(description="V3 3.4 自动抽取准确率抽样评估")
    parser.add_argument("--sample", action="store_true", help="重新生成抽样单（会覆盖判定结果）")
    args = parser.parse_args()

    if args.sample or not os.path.exists(SAMPLE_CSV):
        rows, (n_ent, n_rel) = build_sample()
        if not rows:
            print("未找到抽取产物，请先执行 kg.extract.build_entities 与 kg.extract.build_relations")
            return 1
        write_csv(SAMPLE_CSV, rows, FIELDS)
        print("已生成抽样单：%s（实体 %d 条 + 关系 %d 条，种子 %d）"
              % (os.path.relpath(SAMPLE_CSV, _ROOT).replace("\\", "/"), n_ent, n_rel, SEED))
        print("请在「判定」列填 对 / 错 后重跑本脚本出报告。")
        return 0

    rows = _read(SAMPLE_CSV)
    judged, _ = report(rows)
    if judged < len(rows):
        print("\n尚有 %d 条未判定，报告仅覆盖已判定部分。" % (len(rows) - judged))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
