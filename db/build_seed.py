# -*- coding: utf-8 -*-
"""
由四层数据源生成图谱导入所需的 Excel 七表与别名表（生成物不要手改）。

用法（项目根目录）：python -m db.build_seed [--out data/excel]

数据源的合并顺序与跳过规则见 db/merge_sources.py；本模块只做**校验与落盘**。

产出（与 kg/importer/import_all.py 约定的文件名一致）：
  data/excel/person.xlsx / organization.xlsx / event.xlsx / meeting.xlsx /
             location.xlsx / document.xlsx / relation.xlsx / alias.xlsx

校验依据 backend/common/ontology.py：
  实体 —— 必填属性非空、枚举值域合法、主名跨类型全局唯一、时间原文可解析；
  关系 —— 关系类型在十类之内、头尾类型组合符合约束、头尾实体均已定义、
          拒绝自指、HELD_POSITION 的 position 必填、别名无一对多歧义。
任何一条不合规即中止并打印前若干条问题，不产出半成品。
"""
import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402
from db import merge_sources  # noqa: E402
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
PROBLEM_PREVIEW = 30  # 校验失败时最多打印的问题条数


def check_entity_rows(rows_by_label, problems):
    """逐条按本体校验实体行，返回主名 → 标签的映射。"""
    name_owner = {}
    for label, rows in rows_by_label.items():
        allowed = {p["name"] for p in O.props_of(label)} | {"checked"}
        required = set(O.required_props(label))
        enums = [p for p in O.props_of(label) if p["kind"] == "enum"]
        time_field = TIME_FIELD.get(label)
        for row in rows:
            name = str(row.get("name") or "").strip()
            unknown = set(row) - allowed - {"source"}
            if unknown:
                problems.append("%s「%s」含本体未定义字段：%s" % (label, name, sorted(unknown)))
            for field in required:
                if field != "source" and not str(row.get(field) or "").strip():
                    problems.append("%s「%s」缺必填属性 %s" % (label, name, field))
            for prop in enums:
                value = row.get(prop["name"])
                if value and value not in prop.get("enum", []):
                    problems.append("%s「%s」的 %s 取值不合法：%s"
                                    % (label, name, prop["name"], value))
            if name in name_owner:
                problems.append("实体主名跨类型重复：%s（%s / %s）" % (name, name_owner[name], label))
            else:
                name_owner[name] = label
            if time_field and row.get(time_field) and timeparse.parse(row[time_field])[0] is None:
                problems.append("%s「%s」的 %s 无法解析：%s"
                                % (label, name, time_field, row[time_field]))
    return name_owner


def build_alias_rows(rows_by_label, problems):
    """别名 → 主名映射；一对多歧义拒绝入库并记录（规范 3.5 / 7.3）。"""
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


def check_relation_rows(relations, name_owner, problems):
    """校验关系行；BELONGS_TO 由导入脚本按 time_sort 自动归属，不在此手填。"""
    for row in relations:
        head, rel, tail = row["head"], row["rel"], row["tail"]
        tag = "(%s)-[%s]->(%s)" % (head, rel, tail)
        if not O.is_relation(rel):
            problems.append("%s 关系类型不在十类之内" % tag)
            continue
        if not O.is_allowed(row["head_type"], rel, row["tail_type"]):
            problems.append("%s 头尾类型组合不符合本体约束：%s → %s"
                            % (tag, row["head_type"], row["tail_type"]))
        if head == tail:
            problems.append("%s 头尾实体相同" % tag)
        for role, name, label in (("头", head, row["head_type"]), ("尾", tail, row["tail_type"])):
            if name_owner.get(name) != label:
                problems.append("%s %s实体未定义或类型不符：%s（声明 %s，实际 %s）"
                                % (tag, role, name, label, name_owner.get(name) or "未定义"))
        if rel == "HELD_POSITION" and not str(row.get("position") or "").strip():
            problems.append("%s 缺 position（HELD_POSITION 必填）" % tag)
    return relations


def write_excel(out_dir, rows_by_label, relation_rows, alias_rows):
    import pandas as pd

    os.makedirs(out_dir, exist_ok=True)
    written = []
    for label, filename in SHEET_OF.items():
        rows = rows_by_label.get(label) or []
        # 列顺序：本体属性定义顺序（不含派生列）+ source + checked
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


def summarize(rows_by_label, relation_rows, stats):
    """打印实体 / 关系分布，并对照 V3 3.7 与 3.6 的达标线给出结论。"""
    from db.seed_data import core_pool as C

    print("\n--- 实体 ---")
    total, checked_total = 0, 0
    for label in O.LABELS:
        if label == "Period":
            print("  %-14s %5d（由 import_all 按本体定稿写入，全部 checked=1）" % (O.zh(label), len(O.PERIODS)))
            total += len(O.PERIODS)
            checked_total += len(O.PERIODS)
            continue
        rows = rows_by_label.get(label) or []
        checked = sum(1 for r in rows if int(r.get("checked") or 0) == 1)
        total += len(rows)
        checked_total += checked
        print("  %-14s %5d（核心池 checked=1 共 %d，目标 %d）"
              % (O.zh(label), len(rows), checked, C.CORE_TARGET.get(label, 0)))
    print("  合计 %d 个实体（V3 3.7 达标线 ≥1500，%s）"
          % (total, "达标" if total >= 1500 else "未达标"))
    print("  核心池合计 %d（V3 3.6 达标线 500，%s）"
          % (checked_total, "达标" if checked_total >= 500 else "未达标"))

    print("--- 关系 ---")
    counter = {}
    for row in relation_rows:
        counter[row["rel"]] = counter.get(row["rel"], 0) + 1
    for rel in O.RELATIONS:
        if rel == "BELONGS_TO":
            print("  %-18s %-8s %s" % (rel, O.zh(rel), "由 import_all 按 time_sort 自动归属"))
        else:
            print("  %-18s %-8s %5d" % (rel, O.zh(rel), counter.get(rel, 0)))
    print("  显式关系合计 %d，另加 BELONGS_TO 自动归属（事件 + 会议各一条）" % len(relation_rows))
    print("--- 合并统计 ---")
    print("  自动实体输入 %d 行，入库 %d 行；因主名占用跳过 %d，因别名冲突跳过 %d；丢弃悬空关系 %d"
          % (stats["auto_input"], stats["auto_added"], stats["skipped"]["name"],
             stats["skipped"]["alias"], stats["dropped_relations"]))


def main():
    parser = argparse.ArgumentParser(description="由四层数据源生成 data/excel 七表")
    parser.add_argument("--out", default=OUT_DIR, help="输出目录，默认 data/excel")
    args = parser.parse_args()

    problems = []
    rows_by_label, relation_rows, stats = merge_sources.collect()
    name_owner = check_entity_rows(rows_by_label, problems)
    alias_rows = build_alias_rows(rows_by_label, problems)
    check_relation_rows(relation_rows, name_owner, problems)

    if problems:
        print("校验未通过，共 %d 个问题，未产出任何文件；前 %d 条："
              % (len(problems), min(len(problems), PROBLEM_PREVIEW)))
        for item in problems[:PROBLEM_PREVIEW]:
            print("  · %s" % item)
        return 1

    print("校验通过。")
    for filename, count in write_excel(args.out, rows_by_label, relation_rows, alias_rows):
        print("  已写出 %-18s %5d 行" % (filename, count))
    summarize(rows_by_label, relation_rows, stats)
    print("\n下一步：python -m kg.importer.import_all --schema  然后  python -m kg.importer.verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
