# -*- coding: utf-8 -*-
"""
四层数据源合并（供 db/build_seed.py 调用，本模块只合并不校验）。

合并顺序即优先级，**先登记者占用该主名**，后来者整行跳过：
  1. db/seed_data/entities.py      —— 打通链路的种子数据，checked=1；
  2. db/seed_data/from_extraction.py —— DR-11 抽取后人工确认的历次党代会等，checked=1；
  3. db/seed_data/core_*.py        —— V3 3.6 核心实体池，checked=1；
  4. data/clean/entities_auto.csv  —— DR-13 自动实体，checked=0，
     其中主名出现在 core_promote.PROMOTE 中的提升为 checked=1。

另有一条降级规则：主名出现在 db/seed_data/core_unsourced.py（由 eval/core_check --emit
生成）中的行，checked 一律置 0——留档语料未覆盖它，不满足核心池的溯源要求。

跳过规则（两条，都是为了满足规范 6.5「主名跨类型全局唯一」与 3.5「别名无一对多歧义」）：
  · 主名已被占用 —— 跳过；
  · 主名与已登记实体的**别名**相同 —— 跳过（否则该别名同时指向两个实体）。
关系同理：两端实体有一端未能入库时，该关系整条丢弃，不产出悬空边。
"""
import csv
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from qa.dictionary import split_alias  # noqa: E402

try:
    from db.seed_data.core_unsourced import UNSOURCED
except ImportError:                     # 尚未跑过 eval/core_check --emit 时按空名单处理
    UNSOURCED = ()
UNSOURCED = frozenset(UNSOURCED)

AUTO_ENTITY_CSV = os.path.join(_ROOT, "data", "clean", "entities_auto.csv")
AUTO_RELATION_CSV = os.path.join(_ROOT, "data", "clean", "relations_auto.csv")
# 自动实体表里的空列不写入，避免把空串当成属性值
AUTO_SKIP_COLUMNS = ("label",)


class Registry(object):
    """登记表：记录已占用的主名与别名，并按标签收集最终行。"""

    def __init__(self):
        self.rows = {}
        self.names = {}          # 主名 → 标签
        self.aliases = {}        # 别名 → 主名
        self.skipped = {"name": 0, "alias": 0}

    def add(self, label, row):
        """
        登记一行；主名或别名冲突时跳过并计数，返回是否登记成功。

        主名在 UNSOURCED 名单内的一律降为 checked=0：留档语料没有覆盖它，
        按「每条知识可溯源」不得进核心池，但实体本身仍然入库可查。
        """
        name = str(row.get("name") or "").strip()
        if not name:
            return False
        if name in UNSOURCED:
            row["checked"] = 0
        if name in self.names:
            self.skipped["name"] += 1
            return False
        if name in self.aliases:
            self.skipped["alias"] += 1
            return False
        for alias in split_alias(row.get("alias")):
            if alias in self.names or (alias in self.aliases and self.aliases[alias] != name):
                self.skipped["alias"] += 1
                return False
        self.names[name] = label
        for alias in split_alias(row.get("alias")):
            self.aliases[alias] = name
        self.rows.setdefault(label, []).append(row)
        return True

    def has(self, name, label=None):
        return name in self.names and (label is None or self.names[name] == label)


def seed_layer(registry):
    """第 1 层：种子数据。"""
    from db.seed_data import entities as E

    for label, (fields, records, source) in E.SEED_ENTITIES.items():
        for record in records:
            row = dict(zip(fields, record))
            row["source"] = source
            registry.add(label, row)


def extraction_layer(registry):
    """
    第 2 层：DR-11 抽取后人工确认的记录，同时产出会议召开地关系。

    checked=1：这批记录（历次党代会、三个组织、一个地点）的每项属性都已逐条对照
    data/raw/meeting/ 的留档专题页与大事记条目核对过，并由 eval/core_check.py
    按 V3 3.6 交叉复核，故与核心池同等对待。
    """
    from db.seed_data import from_extraction as X

    relations = []
    for name, alias, time_text, place, content, intro in X.CONGRESSES:
        if registry.add("Meeting", {
                "name": name, "alias": alias, "time_text": time_text, "content": content,
                "intro": intro, "source": X.SOURCE_DDH, "checked": 1}):
            relations.append(_relation(name, "Meeting", "HELD_IN", place, "Location",
                                       source=X.SOURCE_DDH))
    for name, alias, modern in X.EXTRA_LOCATIONS:
        registry.add("Location", {"name": name, "alias": alias, "modern_name": modern,
                                  "source": X.SOURCE_DDH, "checked": 1})
    for name, alias, found_time, org_type, intro in X.EXTRA_ORGANIZATIONS:
        registry.add("Organization", {
            "name": name, "alias": alias, "found_time_text": found_time, "org_type": org_type,
            "intro": intro, "source": X.SOURCE_DDH, "checked": 1})
    return relations


def core_layer(registry):
    """第 3 层：V3 3.6 核心实体池。"""
    from db.seed_data import core_pool as C

    for label in ("Person", "Meeting", "Location", "Organization", "Document"):
        for row in C.rows_of(label):
            row.pop("place", None)  # place 只用于派生 HELD_IN，不是本体属性
            registry.add(label, row)
    return [_relation(head, head_type, rel, tail, tail_type, source=C.CORE_SOURCE)
            for head, head_type, rel, tail, tail_type, _, _ in C.held_in_relations()]


def auto_layer(registry):
    """第 4 层：DR-13 自动实体。主名在提升名单内的置 checked=1。"""
    from db.seed_data import core_pool as C

    promote = C.promoted()
    if not os.path.exists(AUTO_ENTITY_CSV):
        return 0, 0
    total = added = 0
    with open(AUTO_ENTITY_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            label = raw["label"]
            row = {key: value for key, value in raw.items()
                   if value not in (None, "") and key not in AUTO_SKIP_COLUMNS}
            row["checked"] = 1 if row["name"] in promote.get(label, ()) else 0
            total += 1
            added += 1 if registry.add(label, row) else 0
    return total, added


def auto_relations(registry):
    """第 4 层的关系：两端都已入库才保留。"""
    if not os.path.exists(AUTO_RELATION_CSV):
        return []
    out = []
    with open(AUTO_RELATION_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not (registry.has(row["head"], row["head_type"])
                    and registry.has(row["tail"], row["tail_type"])):
                continue
            out.append(_relation(row["head"], row["head_type"], row["rel"], row["tail"],
                                 row["tail_type"], row.get("position", ""),
                                 row.get("time_text", ""), row.get("source", "")))
    return out


def seed_relations():
    """种子关系表（人工维护，头尾均为种子实体）。"""
    from db.seed_data import entities as E
    from db.seed_data.relations import RELATIONS

    out = []
    for head, head_type, rel, tail, tail_type, position, time_text in RELATIONS:
        out.append(_relation(head, head_type, rel, tail, tail_type, position, time_text,
                             E.SEED_ENTITIES[head_type][2]))
    return out


def _relation(head, head_type, rel, tail, tail_type, position="", time_text="", source=""):
    return {"head": head, "head_type": head_type, "rel": rel, "tail": tail,
            "tail_type": tail_type, "position": position, "time_text": time_text,
            "source": source}


def collect():
    """按四层顺序合并，返回 (按标签分组的实体行, 关系行, 统计信息)。"""
    registry = Registry()
    seed_layer(registry)
    relations = seed_relations()
    relations += extraction_layer(registry)
    relations += core_layer(registry)
    auto_total, auto_added = auto_layer(registry)
    relations += auto_relations(registry)

    # 关系两端必须都已入库，且同一 (头, 关系, 尾) 只保留一条
    seen, kept = set(), []
    for row in relations:
        key = (row["head"], row["rel"], row["tail"])
        if key in seen:
            continue
        if not (registry.has(row["head"], row["head_type"])
                and registry.has(row["tail"], row["tail_type"])):
            continue
        seen.add(key)
        kept.append(row)
    stats = {"auto_input": auto_total, "auto_added": auto_added, "skipped": dict(registry.skipped),
             "dropped_relations": len(relations) - len(kept)}
    return registry.rows, kept, stats
