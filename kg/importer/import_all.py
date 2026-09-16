# -*- coding: utf-8 -*-
"""
Excel 七张表 → Neo4j 批量导入（V3 5.2 / 开发规范 7.3），幂等可重跑。
用法（项目根目录）：python -m kg.importer.import_all [--excel data/excel] [--schema]

- 先执行 schema.cypher 建约束索引（--schema 或首次导入）；
- 实体：MERGE (n:Label {name:$name}) SET n += $props，写入 checked 与 updated_at；
- 关系：MATCH 头, 尾 MERGE，HELD_POSITION.position 等关系属性一并写入；
- UNWIND 每 500 行一批提交；全部写操作参数化，标签 / 关系名只从 ontology 白名单取值。
- 时间字段由 timeparse 派生 time_sort / time_precision；Event / Meeting 自动挂 BELONGS_TO 时期。

Excel 约定：data/excel/ 下六张实体表（person/organization/event/meeting/location/document.xlsx）
+ 一张关系表 relation.xlsx（列：head, head_type, rel, tail, tail_type, position, time_text, source）
+ alias.xlsx（列：alias, name）。列 = 4.1 属性定义 + source + checked + 校验日期。
"""
import argparse
import os
import sys
from datetime import datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from kg.extract import period_assign, timeparse  # noqa: E402

BATCH = 500
EXCEL_DIR = os.path.join(_ROOT, "data", "excel")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.cypher")

# 标签与关系名白名单：Cypher 不支持标签参数化，只允许从 ontology 常量取值拼入（规范 4.3）
_L = {label: label for label in O.LABELS}
_R = {rel: rel for rel in O.RELATIONS}

SHEET_OF = {
    "Person": "person.xlsx",
    "Organization": "organization.xlsx",
    "Event": "event.xlsx",
    "Meeting": "meeting.xlsx",
    "Location": "location.xlsx",
    "Document": "document.xlsx",
}
RELATION_SHEET = "relation.xlsx"
TIME_FIELD = {"Event": "time_text", "Meeting": "time_text",
              "Organization": "found_time_text", "Document": "pub_time_text"}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_schema(session):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        body = f.read()
    count = 0
    for stmt in [s.strip() for s in body.split(";")]:
        stmt = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("//")).strip()
        if stmt:
            session.run(stmt)
            count += 1
    print("schema.cypher 已执行：%d 条约束 / 索引" % count)


def _clean_row(label, row):
    """按 ontology 保留已定义属性 + checked，派生时间三字段。"""
    props, allowed = {}, {p["name"] for p in O.props_of(label)}
    for key, value in row.items():
        key = str(key).strip()
        if key in allowed and value not in (None, ""):
            props[key] = int(value) if key in ("birth_year", "death_year", "start_year", "end_year", "order") \
                and str(value).strip().lstrip("-").isdigit() else str(value).strip() \
                if not isinstance(value, (int, float)) else value
    field = TIME_FIELD.get(label)
    if field and props.get(field):
        time_sort, precision = timeparse.parse(props[field])
        if time_sort:
            props["time_sort"] = time_sort
            if label in ("Event", "Meeting"):
                props["time_precision"] = precision
    props["checked"] = int(row.get("checked") or 0)
    props["updated_at"] = _now()
    return props


def _batches(items, size=BATCH):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def import_entities(session, label, rows):
    payload = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        payload.append({"name": name, "props": _clean_row(label, row)})
    cypher = "UNWIND $rows AS row MERGE (n:%s {name: row.name}) SET n += row.props" % _L[label]
    for batch in _batches(payload):
        session.run(cypher, rows=batch)
    return len(payload)


def import_periods(session):
    payload = [{"name": p["name"], "props": {"name": p["name"], "order": p["order"],
                                             "start_year": p["start_year"], "end_year": p["end_year"],
                                             "checked": 1, "updated_at": _now()}} for p in O.PERIODS]
    session.run("UNWIND $rows AS row MERGE (n:Period {name: row.name}) SET n += row.props", rows=payload)
    return len(payload)


def import_relations(session, rows):
    grouped, skipped = {}, 0
    for row in rows:
        head, tail = str(row.get("head") or "").strip(), str(row.get("tail") or "").strip()
        rel = str(row.get("rel") or "").strip()
        head_type, tail_type = str(row.get("head_type") or "").strip(), str(row.get("tail_type") or "").strip()
        if not (head and tail and O.is_relation(rel) and O.is_allowed(head_type, rel, tail_type)):
            skipped += 1
            continue
        props = {}
        for p in O.RELATION_PROPS.get(rel, []):
            if row.get(p["name"]) not in (None, ""):
                props[p["name"]] = str(row[p["name"]]).strip()
        grouped.setdefault((head_type, rel, tail_type), []).append(
            {"head": head, "tail": tail, "props": props})

    total = 0
    for (head_type, rel, tail_type), items in grouped.items():
        cypher = ("UNWIND $rows AS row MATCH (h:%s {name: row.head}) MATCH (t:%s {name: row.tail}) "
                  "MERGE (h)-[r:%s]->(t) SET r += row.props" % (_L[head_type], _L[tail_type], _R[rel]))
        for batch in _batches(items):
            session.run(cypher, rows=batch)
        total += len(items)
    return total, skipped


def assign_periods(session):
    """按 time_sort 为 Event / Meeting 自动挂 BELONGS_TO（period_assign 唯一实现）。"""
    rows = session.run("MATCH (n) WHERE labels(n)[0] IN ['Event','Meeting'] AND n.time_sort IS NOT NULL "
                       "RETURN labels(n)[0] AS label, n.name AS name, n.time_sort AS ts").data()
    payload = []
    for r in rows:
        period = period_assign.assign(r["ts"])
        if period:
            payload.append({"name": r["name"], "period": period})
    for batch in _batches(payload):
        session.run("UNWIND $rows AS row MATCH (n {name: row.name}) MATCH (p:Period {name: row.period}) "
                    "MERGE (n)-[:BELONGS_TO]->(p)", rows=batch)
    return len(payload)


def read_excel(path):
    import pandas as pd

    if not os.path.exists(path):
        return None
    df = pd.read_excel(path, dtype=object)
    df = df.where(df.notna(), None)
    return df.to_dict("records")


def main():
    parser = argparse.ArgumentParser(description="Excel 七表 → Neo4j 批量导入（幂等）")
    parser.add_argument("--excel", default=EXCEL_DIR, help="Excel 目录，默认 data/excel")
    parser.add_argument("--schema", action="store_true", help="导入前执行 schema.cypher")
    args = parser.parse_args()

    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_session, neo4j_status

    app = create_app(load_resources=False)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            return 1
        with neo4j_session() as session:
            if args.schema:
                run_schema(session)
            print("Period 节点：%d" % import_periods(session))
            for label, filename in SHEET_OF.items():
                rows = read_excel(os.path.join(args.excel, filename))
                if rows is None:
                    print("%-14s 跳过（%s 不存在）" % (label, filename))
                    continue
                print("%-14s 导入 %d 行" % (label, import_entities(session, label, rows)))
            rel_rows = read_excel(os.path.join(args.excel, RELATION_SHEET))
            if rel_rows is None:
                print("关系表跳过（%s 不存在）" % RELATION_SHEET)
            else:
                total, skipped = import_relations(session, rel_rows)
                print("关系导入 %d 条（跳过不合约束 %d 条）" % (total, skipped))
            print("自动归属时期：%d 条 BELONGS_TO" % assign_periods(session))

    from qa import dictionary
    with app.app_context():
        print("实体词典已刷新：%s" % dictionary.reload())
    return 0


if __name__ == "__main__":
    sys.exit(main())
