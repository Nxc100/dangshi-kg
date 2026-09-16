# -*- coding: utf-8 -*-
"""
④ 意图分类：关键词 + 词性 + 实体类型三特征联合规则表，按优先级顺序匹配，命中即定；全未中 → UNKNOWN。

匹配策略：
  1) 严格匹配：关键词命中 ∧ 未命中 exclude ∧ 链接实体类型与规则相交 → 意图
  2) 宽松匹配：仅关键词命中 → 意图（交由第⑤步槽位校验给出澄清提示，如"谁参加了毛泽东"）
  3) 无疑问词且已链接实体 → I13 实体介绍
"""
from qa.intent_rules import RULES


def _hit(rule, question):
    if not any(k in question for k in rule["keywords"]):
        return False
    # exclude：命中即否决。用于「在哪」这类过于贪心的关键词——
    # 「重要性体现在哪」问的是意义不是地点，靠否定条件让位给后面的规则
    if any(k in question for k in rule.get("exclude", ())):
        return False
    for group in rule.get("require_all", []):
        if not any(k in question for k in group):
            return False
    return True


def classify(question, pos_feats, entities):
    """④ 返回 I1–I15 或 UNKNOWN；规则表书写顺序即优先级 I14/I15 > I1–I12 > I13。"""
    types = {e["type"] for e in entities}
    for rule in RULES:
        if _hit(rule, question) and (types & set(rule["entity_types"])):
            return rule["intent"]
    for rule in RULES:
        if _hit(rule, question):
            return rule["intent"]
    if entities and not pos_feats.get("has_question"):
        return "I13"
    return "UNKNOWN"
