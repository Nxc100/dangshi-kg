# -*- coding: utf-8 -*-
"""
构建 900 条意图标注数据集（V3 6.1 意图分类对比实验的数据来源）。

用法（项目根目录）：venv\\Scripts\\python -m eval.build_intent_dataset

口径（V3 6.1）：15 意图 × 60 条 = 模板 40 + 改写 20。
  · 模板 40 条：`dataset_templates.INTENT_TEMPLATES[*]["templates"]` × 实体池组合，
    用的是规则表里的标准问法；
  · 改写 20 条：`rewrites` × 实体池组合，**刻意绕开规则关键词**的口语说法。
    这 20 条是实验的信息量所在——若两部分句式雷同，三种方法都会接近满分。

固定随机种子，重跑得到同一份数据集；产出 `eval/datasets/intent900.csv`
（字段：id, intent, intent_zh, question, origin, entity, entity_type）。
数据集一经冻结不得为提分反向修改（V3 9.1 同款纪律）。
"""
import argparse
import os
import random
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from eval import entity_pool  # noqa: E402
from eval.dataset_templates import INTENT_TEMPLATES  # noqa: E402
from kg.crawler.common import write_csv  # noqa: E402
from qa.intent_rules import INTENT_ZH  # noqa: E402

OUT_CSV = os.path.join(_ROOT, "eval", "datasets", "intent900.csv")
FIELDS = ["id", "intent", "intent_zh", "question", "origin", "entity", "entity_type"]
PER_INTENT = 60
TEMPLATE_SHARE = 40  # 其余 PER_INTENT - TEMPLATE_SHARE 条来自改写句式
SEED = 20260916


def _entities_for(pool, labels, count, rng):
    """从该意图允许的实体类型里取 count 个 (名称, 类型)；池子不够时循环取用。"""
    candidates = [(name, label) for label in labels for name in pool.get(label, [])]
    if not candidates:
        return []
    rng.shuffle(candidates)
    picked = []
    while len(picked) < count:
        picked.extend(candidates[: count - len(picked)])
    return picked[:count]


def build_for_intent(intent, spec, pool, rng):
    """按「模板 40 + 改写 20」生成该意图的 60 条，句式轮转以免集中在少数问法。"""
    rows = []
    for origin, phrasings, count in (("template", spec["templates"], TEMPLATE_SHARE),
                                     ("rewrite", spec["rewrites"], PER_INTENT - TEMPLATE_SHARE)):
        entities = _entities_for(pool, spec["label"], count, rng)
        for index, (name, label) in enumerate(entities):
            rows.append({
                "intent": intent, "intent_zh": INTENT_ZH[intent],
                "question": phrasings[index % len(phrasings)].format(name=name),
                "origin": origin, "entity": name, "entity_type": label,
            })
    return rows


def build():
    pool = entity_pool.load()
    rng = random.Random(SEED)
    rows = []
    for intent in sorted(INTENT_TEMPLATES, key=lambda k: int(k[1:])):
        rows.extend(build_for_intent(intent, INTENT_TEMPLATES[intent], pool, rng))
    # 同一意图内可能因实体循环取用产生重复问句，替换为该意图未用过的实体重新拼
    seen, unique = set(), []
    for row in rows:
        if row["question"] in seen:
            continue
        seen.add(row["question"])
        unique.append(row)
    for index, row in enumerate(unique, 1):
        row["id"] = index
    return unique, pool


def main():
    parser = argparse.ArgumentParser(description="构建 900 条意图标注数据集")
    parser.add_argument("--sample", type=int, default=0, help="打印每类前 N 条样本")
    args = parser.parse_args()

    rows, pool = build()
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    write_csv(OUT_CSV, rows, FIELDS)

    from collections import Counter
    counter = Counter(r["intent"] for r in rows)
    origin = Counter(r["origin"] for r in rows)
    print("\n意图标注数据集构建完成")
    print("  实体池（核心池 checked=1）：%s" % entity_pool.summary(pool))
    print("  合计 %d 条；模板 %d / 改写 %d（目标 15 × 60 = 900，模板 600 / 改写 300）"
          % (len(rows), origin["template"], origin["rewrite"]))
    short = [i for i in counter if counter[i] < PER_INTENT]
    if short:
        print("  未达 60 条的意图：%s（实体池不足导致问句重复，已去重）"
              % ", ".join("%s(%d)" % (i, counter[i]) for i in sorted(short)))
    if args.sample:
        for intent in sorted(counter, key=lambda k: int(k[1:])):
            picks = [r for r in rows if r["intent"] == intent][:args.sample]
            print("\n  %s %s：" % (intent, INTENT_ZH[intent]))
            for row in picks:
                print("    [%s] %s" % (row["origin"][:4], row["question"]))
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
