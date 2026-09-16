# -*- coding: utf-8 -*-
"""
生成核心池提升名单 db/seed_data/core_promote.py（V3 3.6 核心实体池的事件与文献部分）。

用法（项目根目录）：venv\\Scripts\\python -m db.make_promote [--events 150] [--documents 10]

为什么用「提升」而不是另写一份核心事件表：自动池的事件名就是《中国共产党一百年大事记》
条目的整句原文，时间、正文、来源 URL 均逐字来自留档；重抄一遍只会引入转录错误。
人工要做的判断是「这条算不算核心知识」，因此这里只产出**主名清单**。

入选规则（可重跑、结果确定）：
  事件 —— 必须来自 DR-01《中国共产党一百年大事记》（该文献本身即百年最重要事件的官方遴选），
          且时间精度为 day、已归属到七个时期之一；按时期配额抽取，每个时期至少 10 条，
          其余按各时期可选条数比例分配；时期内按正文长度降序取（正文越长史实越完整）。
  文献 —— 在留档条目中被提及次数最多的若干篇，保证核心文献确有史料支撑。

生成的 core_promote.py 是**名单文件，可人工增删**；重跑本脚本会覆盖它，
故人工调整后如需保留，应在提交信息中说明并不再重跑。
"""
import argparse
import collections
import csv
import io
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402

ENTITY_CSV = os.path.join(_ROOT, "data", "clean", "entities_auto.csv")
DSJ_CSV = os.path.join(_ROOT, "data", "clean", "events_raw.csv")
TTD_CSV = os.path.join(_ROOT, "data", "clean", "ttd_raw.csv")
OUT_PY = os.path.join(_ROOT, "db", "seed_data", "core_promote.py")
MIN_PER_PERIOD = 10

HEADER = '''# -*- coding: utf-8 -*-
"""
核心池提升名单（由 db/make_promote.py 生成，可人工增删；重跑脚本会覆盖）。

PROMOTE 中列出的主名，在 db/build_seed.py 合并自动池时把该行的 checked 置 1，
使其进入 V3 3.6 核心实体池（F7 测验与 F8 每日推荐只从核心池取数）。

入选规则见生成脚本的模块注释；每条的属性均逐字来自留档原文，
并由 eval/core_check.py 对照 data/corpus 与 data/clean 的原文做交叉复核。
"""

PROMOTE = {
'''


def load_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pick_events(quota):
    """按时期配额从大事记条目中选出核心事件主名。"""
    from kg.extract.build_entities import event_name

    by_period = collections.defaultdict(dict)
    for row in load_rows(DSJ_CSV):
        if row["time_precision"] != "day" or not row["所属时期"]:
            continue
        name = event_name(row["条目正文"].strip())
        if name:
            # 同名条目保留正文最长的一条，正文长度作为排序依据
            body = row["条目正文"]
            slot = by_period[row["所属时期"]]
            if name not in slot or len(body) > len(slot[name]):
                slot[name] = body

    periods = [p["name"] for p in O.PERIODS if by_period.get(p["name"])]
    available = {name: len(by_period[name]) for name in periods}
    plan = _allocate(quota, available)
    picked = []
    for name in periods:
        items = sorted(by_period[name].items(), key=lambda kv: (-len(kv[1]), kv[0]))
        picked.extend(key for key, _ in items[:plan[name]])
    return picked, plan, available


def _allocate(quota, available):
    """按可选条数比例分配配额，每个时期至少 MIN_PER_PERIOD 条，且不超过可选数。"""
    plan = {name: min(MIN_PER_PERIOD, count) for name, count in available.items()}
    rest = quota - sum(plan.values())
    pool = sum(max(0, available[name] - plan[name]) for name in available)
    if rest <= 0 or pool <= 0:
        return plan
    for name in available:
        room = max(0, available[name] - plan[name])
        plan[name] += min(room, int(rest * room / pool))
    # 取整余数补给还有余量的时期，保证总数达到配额
    for name in sorted(available, key=lambda n: -(available[n] - plan[n])):
        if sum(plan.values()) >= quota:
            break
        if plan[name] < available[name]:
            plan[name] += 1
    return plan


def pick_documents(quota):
    """按留档条目中的提及次数选出核心文献主名。"""
    names = [row["name"] for row in load_rows(ENTITY_CSV) if row["label"] == "Document"]
    texts = [row["条目正文"] for row in load_rows(DSJ_CSV) + load_rows(TTD_CSV)]
    counter = collections.Counter()
    for name in names:
        token = "《%s》" % name
        counter[name] = sum(1 for text in texts if token in text)
    return [name for name, count in counter.most_common(quota) if count >= 2]


def write_promote(events, documents):
    with io.open(OUT_PY, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER)
        for label, names in (("Event", events), ("Document", documents)):
            f.write('    "%s": [\n' % label)
            for name in names:
                f.write('        "%s",\n' % name.replace('"', '\\"'))
            f.write("    ],\n")
        f.write("}\n")


def main():
    parser = argparse.ArgumentParser(description="生成核心池提升名单")
    parser.add_argument("--events", type=int, default=150, help="核心事件数，默认 150")
    parser.add_argument("--documents", type=int, default=10, help="核心文献补充数，默认 10")
    args = parser.parse_args()

    if not os.path.exists(DSJ_CSV):
        print("未找到 %s，请先执行：python -m kg.extract.parse_events" % DSJ_CSV)
        return 1
    events, plan, available = pick_events(args.events)
    documents = pick_documents(args.documents)
    write_promote(events, documents)

    print("核心池提升名单已生成：%s\n" % os.path.relpath(OUT_PY, _ROOT).replace("\\", "/"))
    print("  %-26s %8s %8s" % ("时期", "可选", "入选"))
    for name in plan:
        print("  %-26s %8d %8d" % (name, available[name], plan[name]))
    print("  事件合计入选 %d（目标 %d）" % (len(events), args.events))
    print("  文献补充入选 %d：%s" % (len(documents), "、".join(documents[:6])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
