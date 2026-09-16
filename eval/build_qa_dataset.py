# -*- coding: utf-8 -*-
"""
构建 200 条端到端问答评测集（V3 9.1 核心实验的数据来源）。

用法（项目根目录）：venv\\Scripts\\python -m eval.build_qa_dataset

口径（V3 9.1）：200 条 = 8 大类 × 25 条，含 **10% 错字/同音干扰**样本。
判定要三条同时满足，故每条都要带三个标注：
  · `intent`         —— 该问句的正确意图；
  · `entity`         —— 该问句指向的实体（干扰样本记**正确实体**，问句里写的是错字版）；
  · `expect_contains`—— 答案必须出现的关键串，**在建集时直接向图谱要**，
                        保证"答案内容与图谱事实一致"这一条是对着图谱事实核的，不是人拍脑袋写的。

**主语实体不按"答得出"筛选。** 从核心池里按类别该问的实体类型随机取，
取到属性缺失的就让它缺——V3 9.1 的错误归因本来就有「图谱知识缺失」一类，
筛掉它们会把准确率刷虚，也就看不出该回补哪些数据（缺失项回补走 F6）。

数据集一经冻结**不得为提分反向修改**；数据可以回补，题目不能改。
产出 `eval/datasets/qa200.csv`。
"""
import argparse
import os
import random
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from eval import entity_pool  # noqa: E402
from eval.dataset_templates import INTENT_TEMPLATES, QA_CATEGORIES, perturb  # noqa: E402
from kg.crawler.common import write_csv  # noqa: E402
from qa.intent_rules import INTENT_ZH  # noqa: E402

OUT_CSV = os.path.join(_ROOT, "eval", "datasets", "qa200.csv")
FIELDS = ["id", "category", "intent", "intent_zh", "question", "entity", "entity_type",
          "expect_contains", "perturbed", "note"]
PER_CATEGORY = 25
PERTURB_RATE = 0.10  # V3 9.1：10% 错字 / 同音干扰
SEED = 20260916
NAME_MAX = 20  # 评测集比意图集更严：整句式的长事件名不像真人提问


def expected_answer(intent, name, label, run_read):
    """向图谱要该问句的正确答案关键串；图谱答不出时返回空串（记为知识缺失）。"""
    from qa import cypher_builder

    cypher, params = cypher_builder.build(intent, {"name": name, "type": label})
    if not cypher:
        return ""
    try:
        rows = run_read(cypher, **params)
    except Exception:  # noqa: BLE001 —— 建集阶段单条失败不影响整体
        return ""
    if not rows:
        return ""
    row = rows[0]
    for key in ("value", "other", "mid"):
        value = row.get(key)
        if value:
            return str(value)
    return name if intent == "I13" else ""


def pick(pool, intents, count, rng):
    """为一个类别取 count 条 (意图, 实体, 类型)，类别内多意图轮转。"""
    picked = []
    while len(picked) < count:
        for intent in intents:
            if len(picked) >= count:
                break
            labels = INTENT_TEMPLATES[intent]["label"]
            candidates = [(n, l) for l in labels for n in pool.get(l, []) if len(n) <= NAME_MAX]
            if not candidates:
                continue
            name, label = rng.choice(candidates)
            picked.append((intent, name, label))
    return picked


def build(run_read):
    pool = entity_pool.load()
    rng = random.Random(SEED)
    rows = []
    for category, intents in QA_CATEGORIES:
        for intent, name, label in pick(pool, intents, PER_CATEGORY, rng):
            spec = INTENT_TEMPLATES[intent]
            phrasings = spec["templates"] + spec["rewrites"]
            rows.append({
                "category": category, "intent": intent, "intent_zh": INTENT_ZH[intent],
                "question": rng.choice(phrasings).format(name=name),
                "entity": name, "entity_type": label,
                "expect_contains": expected_answer(intent, name, label, run_read),
                "perturbed": 0, "note": "",
            })
    # 均匀抽 10% 做同音干扰：把问句里的实体名换成错字版，标注仍记正确实体
    index = list(range(len(rows)))
    rng.shuffle(index)
    for i in index[: int(len(rows) * PERTURB_RATE)]:
        row = rows[i]
        wrong = perturb(row["entity"])
        if wrong == row["entity"]:
            continue
        row["question"] = row["question"].replace(row["entity"], wrong)
        row["perturbed"] = 1
        row["note"] = "同音干扰：%s → %s" % (row["entity"], wrong)
    for row in rows:
        if not row["expect_contains"] and not row["note"]:
            row["note"] = "图谱暂无该属性/关系，预期回答「暂未收录」"
    for number, row in enumerate(rows, 1):
        row["id"] = number
    return rows, pool


def main():
    parser = argparse.ArgumentParser(description="构建 200 条端到端问答评测集")
    parser.add_argument("--sample", type=int, default=0, help="每类打印 N 条样本")
    args = parser.parse_args()

    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_status, run_read

    app = create_app(load_resources=False)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            return 1
        rows, pool = build(run_read)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    write_csv(OUT_CSV, rows, FIELDS)

    from collections import Counter
    cat = Counter(r["category"] for r in rows)
    missing = sum(1 for r in rows if not r["expect_contains"])
    print("\n端到端评测集构建完成")
    print("  实体池（核心池 checked=1）：%s" % entity_pool.summary(pool))
    print("  合计 %d 条，八大类各 %s" % (len(rows), "/".join(str(cat[c]) for c, _ in QA_CATEGORIES)))
    print("  同音干扰 %d 条（%.0f%%）；图谱暂答不出 %d 条（%.0f%%，预期回答「暂未收录」，"
          "按 V3 9.1 归因为「图谱知识缺失」）"
          % (sum(r["perturbed"] for r in rows), PERTURB_RATE * 100,
             missing, missing * 100.0 / len(rows)))
    if args.sample:
        for category, _ in QA_CATEGORIES:
            print("\n  %s：" % category)
            for row in [r for r in rows if r["category"] == category][:args.sample]:
                print("    [%s] %s  → 期望含「%s」%s"
                      % (row["intent"], row["question"], row["expect_contains"][:24],
                         " ⚠干扰" if row["perturbed"] else ""))
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
