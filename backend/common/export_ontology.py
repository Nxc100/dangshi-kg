# -*- coding: utf-8 -*-
"""
导出 backend/common/ontology.py -> frontend/src/utils/ontology.js（生成文件，禁止手改）。

用法（项目根目录）：python -m backend.common.export_ontology
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common import ontology  # noqa: E402

TARGET = os.path.join(_ROOT, "frontend", "src", "utils", "ontology.js")

HEADER = """/* eslint-disable */
// ============================================================================
// 【生成文件，禁止手改】由 backend/common/export_ontology.py 从 backend/common/ontology.py 生成
// 重新生成：python -m backend.common.export_ontology
// 七类实体 / 十类关系 / 中文名 / 色值 / 头尾约束 / 属性定义 / 枚举 / 七个历史时期（全站唯一来源镜像）
// ============================================================================
"""

FOOTER = """
export const labelZh = (label) => LABEL_ZH[label] || label
export const labelColor = (label) => LABEL_COLOR[label] || '#999999'
export const relationZh = (rel) => RELATION_ZH[rel] || rel
export const formProps = (label) => (PROPS[label] || []).filter((p) => !p.derived)
export const requiredProps = (label) => formProps(label).filter((p) => p.required).map((p) => p.name)
export const allowedRelations = (headLabel) =>
  RELATIONS.filter((r) => RELATION_CONSTRAINTS[r].some(([h]) => h === headLabel))
export const allowedTails = (headLabel, rel) =>
  (RELATION_CONSTRAINTS[rel] || []).filter(([h]) => h === headLabel).map(([, t]) => t)
export const isAllowed = (headLabel, rel, tailLabel) =>
  (RELATION_CONSTRAINTS[rel] || []).some(([h, t]) => h === headLabel && t === tailLabel)
"""


def main():
    data = ontology.as_export_dict()
    lines = [HEADER]
    for key, value in data.items():
        lines.append("export const %s = %s\n" % (key, json.dumps(value, ensure_ascii=False, indent=2)))
    lines.append(FOOTER)
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("ontology.js generated -> " + TARGET)


if __name__ == "__main__":
    main()
