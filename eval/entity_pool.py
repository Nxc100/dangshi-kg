# -*- coding: utf-8 -*-
"""
评测数据集共用的实体池（两个构建脚本共用，避免各自维护一份口径不同的池子）。

口径：取 `data/excel` 六张表中 **checked=1 的核心池**，外加本体定稿的七个时期。
不用全量池的理由——真实用户问的多是知名实体，用 4 000 多个自动池实体抽样会让
评测分布偏离真实提问，评出来的准确率既不好看也没参考价值。

读 Excel 而不读 Neo4j：数据集构建不应依赖图数据库是否启动，且 Excel 是导入的源头，
两者一致（`import_all --prune` 保证）。
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology as O  # noqa: E402

EXCEL_DIR = os.path.join(_ROOT, "data", "excel")
SHEET_OF = {"Person": "person.xlsx", "Organization": "organization.xlsx",
            "Event": "event.xlsx", "Meeting": "meeting.xlsx",
            "Location": "location.xlsx", "Document": "document.xlsx"}
NAME_MAX = 30  # 过长的整句事件名不像真实提问，评测集里不取


def load(name_max=NAME_MAX):
    """返回 {标签: [主名, ...]}，按名称排序保证可复现。"""
    import pandas as pd

    pool = {}
    for label, filename in SHEET_OF.items():
        path = os.path.join(EXCEL_DIR, filename)
        if not os.path.exists(path):
            continue
        frame = pd.read_excel(path).fillna("")
        names = [str(row["name"]).strip() for row in frame.to_dict("records")
                 if int(row.get("checked") or 0) == 1 and 0 < len(str(row["name"]).strip()) <= name_max]
        pool[label] = sorted(set(names))
    pool["Period"] = [p["name"] for p in O.PERIODS]
    return pool


def summary(pool):
    return "、".join("%s %d" % (O.zh(label), len(names)) for label, names in sorted(pool.items()))
