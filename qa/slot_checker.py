# -*- coding: utf-8 -*-
"""
⑤ 槽位校验：意图所需实体类型与第③步输出不符时（如 I6 配了人物实体），
返回澄清提示 + 该实体支持的问法示例，不强行查询。
"""
from backend.common.ontology import zh
from qa.intent_rules import INTENT_ENTITY_TYPES, rules_for_type


def pick_entity(intent, entities):
    """返回第一个满足意图类型要求的实体；无则 None。"""
    required = set(INTENT_ENTITY_TYPES.get(intent, []))
    for e in entities:
        if e["type"] in required:
            return e
    return None


def check(intent, entities):
    """校验通过返回 None；不通过返回 clarify = {text, examples}。"""
    if not entities or intent == "UNKNOWN":
        return None
    if pick_entity(intent, entities) is not None:
        return None
    e = entities[0]
    examples = [rule["example"].format(name=e["name"]) for rule in rules_for_type(e["type"])][:3]
    text = "「%s」是%s，暂不支持这样提问。您可以试试：" % (e["name"], zh(e["type"]))
    return {"text": text, "examples": examples}
