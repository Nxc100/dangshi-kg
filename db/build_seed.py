# -*- coding: utf-8 -*-
"""
由 db/seed_data 生成图谱导入所需的 Excel 七表与别名表（生成物不要手改）。

用法（项目根目录）：python -m db.build_seed [--out data/excel]

产出（与 kg/importer/import_all.py 约定的文件名一致）：
  data/excel/person.xlsx / organization.xlsx / event.xlsx / meeting.xlsx /
             location.xlsx / document.xlsx / relation.xlsx / alias.xlsx

生成前按 backend/common/ontology.py 逐条校验：
  实体 —— 必填属性非空、枚举值域合法、主名跨类型全局唯一、时间原文可解析；
  关系 —— 关系类型在十类之内、头尾类型组合符合约束、头尾实体均已定义、
          拒绝自指、HELD_POSITION 的 position 必填、别名无一对多歧义。
任何一条不合规即中止并打印全部问题，不产出半成品。
"""
import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from db.seed_data import entities as E  # noqa: E402
from db.seed_data import from_extraction as X  # noqa: E402
from db.seed_data.relations import RELATIONS  # noqa: E402
from kg.extract import timeparse  # noqa: E402
from qa.dictionary import split_alias  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "data", "excel")
SHEET_OF = {
    "Person": "person.xlsx", "Organization": "organization.xlsx", "Event": "event.xlsx",
    "Meeting": "meeting.xlsx", "Location": "location.xlsx", "Document": "document.xlsx",
}
RELATION_SHEET = "relation.xlsx"
ALIAS_SHEET = "alias.xlsx"
# 时间原文字段（build 时校验可解析，time_sort / time_precision 由导入脚本派生）
TIME_FIELD = {"Event": "time_text", "Meeting": "time_text",
              "Organization": "found_time_text", "Document": "pub_time_text"}


def merge_extracted():
    """
    把 DR-11 抽取并经人工确认的记录并入种子数据（V3 3.4 第 2 步产物）。

    会议拆成实体行与「召开于」关系行；checked 一律为 0，表示尚未经 3.6 校验规程。
    返回 (按类型追加的实体记录, 追加的关系三元组)。
    """
    extra_ent = {"Meeting": [], "Location": [], "Organization": []}
    extra_rel = []
    for name, alias, time_text, place, content, intro in X.CONGRESSES:
        extra_ent["Meeting"].append({
            "name": name, "alias": alias, "time_text": time_text, "content": content,
            "intro": intro, "source": X.SOURCE_DDH, "checked": 0})
        extra_rel.append((name, "Meeting", "HELD_IN", place, "Location", "", ""))
    for name, alias, modern in X.EXTRA_LOCATIONS:
        extra_ent["Location"].append({
            "name": name, "alias": alias, "modern_name": modern,
            "source": X.SOURCE_DDH, "checked": 0})
    for name, alias, found_time, org_type, intro in X.EXTRA_ORGANIZATIONS:
        extra_ent["Organization"].append({
            "name": name, "alias": alias, "found_time_text": found_time,
            "org_type": org_type, "intro": intro, "source": X.SOURCE_DDH, "checked": 0})
    return extra_ent, extra_rel


def build_entity_rows(problems, extra_ent=None):
    """把 seed_data 的元组记录展开为带 source 的字典行，并逐条校验。"""
    extra_ent = extra_ent or {}
    rows_by_label, name_owner = {}, {}
    for label, (fields, records, source) in E.SEED_ENTITIES.items():
        allowed = {p["name"] for p in O.props_of(label)} | {"checked"}
        required = set(O.required_props(label))
        rows = []
        for record in records:
            row = dict(zip(fields, record))
            row["source"] = source
            name = str(row.get("name") or "").strip()

            unknown = set(row) - allowed - {"source"}
            if unknown:
                problems.append("%s「%s」含本体未定义字段：%s" % (label, name, sorted(unknown)))
            for field in required:
                if field != "source" and not str(row.get(field) or "").strip():
                    problems.append("%s「%s」缺必填属性 %s" % (label, name, field))
            for prop in O.props_of(label):
                value = row.get(prop["name"])
                if prop["kind"] == "enum" and value and value not in prop.get("enum", []):
                    problems.append("%s「%s」的 %s 取值不合法：%s" % (label, name, prop["name"], value))
            # 主名跨标签全局唯一（规范 6.5）
            if name in name_owner:
                problems.append("实体主名跨类型重复：%s（%s / %s）" % (name, name_owner[name], label))
            else:
                name_owner[name] = label
            # 时间原文须能派生出三字段
            field = TIME_FIELD.get(label)
            if field and row.get(field) and timeparse.parse(row[field])[0] is None:
                problems.append("%s「%s」的 %s 无法解析：%s" % (label, name, field, row[field]))
            rows.append(row)
        # 追加 DR-11 抽取确认的记录，走同一套校验
        for row in extra_ent.get(label, []):
            name = str(row.get("name") or "").strip()
            for field in required:
                if field != "source" and not str(row.get(field) or "").strip():
                    problems.append("%s「%s」缺必填属性 %s（抽取来源）" % (label, name, field))
            if name in name_owner:
                problems.append("实体主名跨类型重复：%s（%s / %s）" % (name, name_owner[name], label))
            else:
                name_owner[name] = label
            field = TIME_FIELD.get(label)
            if field and row.get(field) and timeparse.parse(row[field])[0] is None:
                problems.append("%s「%s」的 %s 无法解析：%s" % (label, name, field, row[field]))
            rows.append(row)
        rows_by_label[label] = rows
    return rows_by_label, name_owner


def build_alias_rows(rows_by_label, problems):
    """别名 → 主名映射；一对多歧义拒绝入库并记录（规范 7.3）。"""
    owner, alias_rows = {}, []
    main_names = {row["name"] for rows in rows_by_label.values() for row in rows}
    for label, rows in rows_by_label.items():
        for row in rows:
            for alias in split_alias(row.get("alias")):
                if alias in main_names:
                    problems.append("别名与其他实体主名冲突：%s（来自 %s）" % (alias, row["name"]))
                elif alias in owner and owner[alias] != row["name"]:
                    problems.append("别名一对多歧义：%s → %s / %s" % (alias, owner[alias], row["name"]))
                else:
                    owner[alias] = row["name"]
                    alias_rows.append({"别名": alias, "实体主名": row["name"], "实体类型": label})
    return alias_rows


def build_relation_rows(name_owner, problems, extra_rel=None):
    """校验并展开关系行；BELONGS_TO 由导入脚本按 time_sort 自动归属，不在此手填。"""
    rows, seen = [], set()
    for record in list(RELATIONS) + list(extra_rel or []):
        head, head_type, rel, tail, tail_type, position, time_text = record
        tag = "(%s)-[%s]->(%s)" % (head, rel, tail)
        if not O.is_relation(rel):
            problems.append("%s 关系类型不在十类之内" % tag)
            continue
        if not O.is_allowed(head_type, rel, tail_type):
            problems.append("%s 头尾类型组合不符合本体约束：%s → %s" % (tag, head_type, tail_type))
        if head == tail:
            problems.append("%s 头尾实体相同" % tag)
        for role, name, label in (("头", head, head_type), ("尾", tail, tail_type)):
            if name_owner.get(name) != label:
                problems.append("%s %s实体未定义或类型不符：%s（声明 %s，实际 %s）"
                                % (tag, role, name, label, name_owner.get(name) or "未定义"))
        if rel == "HELD_POSITION" and not position.strip():
            problems.append("%s 缺 position（HELD_POSITION 必填）" % tag)
        if tag in seen:
            problems.append("%s 重复定义" % tag)
        seen.add(tag)
        rows.append({
            "head": head, "head_type": head_type, "rel": rel, "tail": tail, "tail_type": tail_type,
            "position": position, "time_text": time_text,
            "source": E.SEED_ENTITIES[head_type][2],
        })
    return rows


def write_excel(out_dir, rows_by_label, relation_rows, alias_rows):
    import pandas as pd

    os.makedirs(out_dir, exist_ok=True)
    written = []
    for label, filename in SHEET_OF.items():
        rows = rows_by_label.get(label) or []
        # 列顺序：本体属性定义顺序（含派生列占位）+ source + checked
        columns = [p["name"] for p in O.props_of(label) if not p["derived"]] + ["source", "checked"]
        columns = list(dict.fromkeys(columns))
        frame = pd.DataFrame(rows).reindex(columns=columns)
        path = os.path.join(out_dir, filename)
        frame.to_excel(path, index=False)
        written.append((filename, len(rows)))
    pd.DataFrame(relation_rows).to_excel(os.path.join(out_dir, RELATION_SHEET), index=False)
    written.append((RELATION_SHEET, len(relation_rows)))
    pd.DataFrame(alias_rows).to_excel(os.path.join(out_dir, ALIAS_SHEET), index=False)
    written.append((ALIAS_SHEET, len(alias_rows)))
    return written


def summarize(rows_by_label, relation_rows):
    print("\n--- 实体 ---")
    total = 0
    for label in O.LABELS:
        if label == "Period":
            print("  %-14s %3d（由 import_all 按本体定稿写入）" % (O.zh(label), len(O.PERIODS)))
            continue
        rows = rows_by_label.get(label) or []
        checked = sum(1 for r in rows if int(r.get("checked") or 0) == 1)
        total += len(rows)
        print("  %-14s %3d（checked=1 共 %d）" % (O.zh(label), len(rows), checked))
    print("  合计 %d 个实体（不含 7 个时期）" % total)

    print("--- 关系 ---")
    counter = {}
    for row in relation_rows:
        counter[row["rel"]] = counter.get(row["rel"], 0) + 1
    for rel in O.RELATIONS:
        if rel == "BELONGS_TO":
            print("  %-18s %-8s 由 import_all 按 time_sort 自动归属" % (rel, O.zh(rel)))
        else:
            print("  %-18s %-8s %3d" % (rel, O.zh(rel), counter.get(rel, 0)))
    print("  合计 %d 条关系" % len(relation_rows))


def main():
    parser = argparse.ArgumentParser(description="由 db/seed_data 生成 data/excel 七表")
    parser.add_argument("--out", default=OUT_DIR, help="输出目录，默认 data/excel")
    args = parser.parse_args()

    problems = []
    extra_ent, extra_rel = merge_extracted()
    rows_by_label, name_owner = build_entity_rows(problems, extra_ent)
    alias_rows = build_alias_rows(rows_by_label, problems)
    relation_rows = build_relation_rows(name_owner, problems, extra_rel)

    if problems:
        print("校验未通过，共 %d 个问题，未产出任何文件：" % len(problems))
        for item in problems:
            print("  · %s" % item)
        return 1

    print("校验通过。")
    for filename, count in write_excel(args.out, rows_by_label, relation_rows, alias_rows):
        print("  已写出 %-18s %3d 行" % (filename, count))
    summarize(rows_by_label, relation_rows)
    print("\n下一步：python -m kg.importer.import_all --schema  然后  python -m kg.importer.verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
