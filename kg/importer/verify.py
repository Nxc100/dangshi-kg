# -*- coding: utf-8 -*-
"""
图谱质量验收核对（V3 5.3 / 开发规范 7.3）：python -m kg.importer.verify

核对项：七标签 / 十关系计数、跨标签重名为 0、七个 Period 节点齐备且每时期 BELONGS_TO 反查非空、
属性三元组总量、source 覆盖率、核心池（checked=1）规模、约束与索引存在性，
并对照 V3 3.7 达标线逐项给出结论。
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402

# V3 3.7 数据总验收达标线
TARGETS = {"entities": 1500, "relations": 2500, "properties": 8000,
           "core_pool": 500, "source_coverage": 1.0}
# 属性三元组按「实体属性展开计」，不计系统字段（校验标记与写入时间）
PROP_EXCLUDED = ["checked", "updated_at"]
CORE_POOL = {"Person": 120, "Meeting": 60, "Event": 150, "Organization": 40,
             "Document": 60, "Location": 63, "Period": 7}


def _fmt(ok):
    return "达标" if ok else "未达标"


def main():
    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_status, run_read

    app = create_app(load_resources=False)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            return 1

        print("=== 一、节点计数（按标签）===")
        label_counts = {r["label"]: r["c"] for r in run_read(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c ORDER BY label")}
        total_nodes = 0
        for label in O.LABELS:
            c = int(label_counts.get(label, 0))
            total_nodes += c
            print("  %-14s %6d   核心池目标 %d" % (label, c, CORE_POOL[label]))
        print("  合计 %d（达标线 ≥ %d，%s）" % (total_nodes, TARGETS["entities"],
                                          _fmt(total_nodes >= TARGETS["entities"])))

        print("=== 二、关系计数（按类型）===")
        rel_counts = {r["rel"]: r["c"] for r in run_read(
            "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS c ORDER BY rel")}
        total_rels = 0
        for rel in O.RELATIONS:
            c = int(rel_counts.get(rel, 0))
            total_rels += c
            print("  %-18s %-8s %6d" % (rel, O.RELATION_ZH[rel], c))
        print("  合计 %d（达标线 ≥ %d，%s）" % (total_rels, TARGETS["relations"],
                                          _fmt(total_rels >= TARGETS["relations"])))

        print("=== 三、实体主名跨标签唯一性 ===")
        dup = run_read("MATCH (n) WITH n.name AS name, collect(DISTINCT labels(n)[0]) AS labels "
                       "WHERE size(labels) > 1 RETURN name, labels LIMIT 20")
        print("  跨标签重名 %d 例%s" % (len(dup), ("：%s" % dup) if dup else "（要求 0 例）"))

        print("=== 四、七个历史时期 ===")
        for p in O.PERIODS:
            rows = run_read("MATCH (e)-[:BELONGS_TO]->(t:Period {name:$name}) RETURN count(e) AS c", name=p["name"])
            c = int(rows[0]["c"]) if rows else 0
            print("  %-24s order=%d  反查事件 %5d %s" % (p["name"], p["order"], c, "" if c else "← 为空"))

        print("=== 五、属性三元组（实体属性展开计）===")
        props = int(run_read(
            "MATCH (n) UNWIND keys(n) AS k WITH k WHERE NOT k IN $skip RETURN count(*) AS c",
            skip=PROP_EXCLUDED)[0]["c"])
        print("  属性三元组 %d（达标线 ≥ %d，%s）；不计 %s"
              % (props, TARGETS["properties"], _fmt(props >= TARGETS["properties"]),
                 "/".join(PROP_EXCLUDED)))

        print("=== 六、溯源与核心池 ===")
        with_source = int(run_read("MATCH (n) WHERE n.source IS NOT NULL AND n.source <> '' "
                                   "RETURN count(n) AS c")[0]["c"])
        coverage = with_source / total_nodes if total_nodes else 0
        print("  source 覆盖 %d/%d = %.1f%%（要求 100%%，%s）"
              % (with_source, total_nodes, coverage * 100, _fmt(coverage >= TARGETS["source_coverage"])))
        checked = int(run_read("MATCH (n) WHERE n.checked = 1 RETURN count(n) AS c")[0]["c"])
        print("  核心池 checked=1：%d（达标线 %d，%s）"
              % (checked, TARGETS["core_pool"], _fmt(checked >= TARGETS["core_pool"])))

        print("=== 七、约束与索引 ===")
        try:
            cons = run_read("SHOW CONSTRAINTS YIELD name RETURN count(*) AS c")[0]["c"]
            idx = run_read("SHOW INDEXES YIELD name RETURN count(*) AS c")[0]["c"]
            print("  约束 %s 条 / 索引 %s 条（schema.cypher 定义 7 约束 + 8 索引）" % (cons, idx))
        except Exception as exc:  # noqa: BLE001
            print("  查询失败：%s" % exc)

        print("=== 八、F9 语料 ===")
        from qa import fallback
        fallback.build()
        print("  paragraphs.csv 段落 %d（达标线 ≥ 2000，%s）" % (fallback.size(), _fmt(fallback.size() >= 2000)))
        return 0


if __name__ == "__main__":
    sys.exit(main())
