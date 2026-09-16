# -*- coding: utf-8 -*-
"""
⑥ 查询构建：INTENT_CYPHER —— 15 类意图 ↔ 15 个参数化 Cypher 模板一一对应（V3 6.2）。

- 实体名一律以 $name 参数传入（杜绝字符串拼接，防注入）；
- 标签 / 关系名只允许取自 ontology 白名单常量拼入（Cypher 不支持标签参数化）；
- I1 / I2 / I3 / I4 / I13 按实体类型分流到对应属性 / 关系。

返回行约定（供 answer_builder 统一组装）：
  attr 类：name, value                     单跳关系类：name, other, other_type, rprops[, direction]
  I13   ：name, props                      两跳类   ：name, mid, others
"""
from backend.common import ontology as O

_L = {label: label for label in O.LABELS}  # 标签白名单
_R = {rel: rel for rel in O.RELATIONS}  # 关系白名单


def _attr(label, attr):
    return "MATCH (n:%s {name:$name}) RETURN n.name AS name, n.%s AS value" % (_L[label], attr)


def _out(label, rel, other_label=None, order=None):
    other = ":" + _L[other_label] if other_label else ""
    q = ("MATCH (n:%s {name:$name})-[r:%s]->(m%s) "
         "RETURN n.name AS name, m.name AS other, labels(m)[0] AS other_type, properties(r) AS rprops"
         % (_L[label], _R[rel], other))
    return q + (" ORDER BY %s" % order if order else "")


def _in(label, rel, other_label=None, order=None):
    other = ":" + _L[other_label] if other_label else ""
    q = ("MATCH (m%s)-[r:%s]->(n:%s {name:$name}) "
         "RETURN n.name AS name, m.name AS other, labels(m)[0] AS other_type, properties(r) AS rprops"
         % (other, _R[rel], _L[label]))
    return q + (" ORDER BY %s" % order if order else "")


INTENT_CYPHER = {
    "I1": {
        "Meeting": _attr("Meeting", "time_text"),
        "Event": _attr("Event", "time_text"),
        "Organization": _attr("Organization", "found_time_text"),
        "Document": _attr("Document", "pub_time_text"),
    },
    "I2": {
        "Meeting": _out("Meeting", "HELD_IN", "Location"),
        "Event": _out("Event", "OCCURRED_IN", "Location"),
    },
    "I3": {"Meeting": _attr("Meeting", "content"), "Event": _attr("Event", "content")},
    "I4": {"Meeting": _attr("Meeting", "meaning"), "Event": _attr("Event", "meaning")},
    "I5": _in("Event", "LED"),
    "I6": _in("Meeting", "PARTICIPATED_IN", "Person"),
    "I7": _in("Document", "AUTHORED", "Person"),
    "I8": _out("Person", "AUTHORED", "Document", order="m.time_sort"),
    "I9": _out("Person", "LED", "Event", order="m.time_sort"),
    "I10": _in("Period", "BELONGS_TO", order="m.time_sort"),
    "I11": (
        "MATCH (n:%s {name:$name})-[r:%s]-(m:%s) "
        "RETURN n.name AS name, m.name AS other, labels(m)[0] AS other_type, properties(r) AS rprops, "
        "CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END AS direction"
        % (_L["Organization"], _R["REORGANIZED_TO"], _L["Organization"])
    ),
    "I12": _out("Person", "HELD_POSITION", "Organization"),
    "I13": {label: "MATCH (n:%s {name:$name}) RETURN n.name AS name, properties(n) AS props" % _L[label]
            for label in O.LABELS},
    "I14": (
        "MATCH (p:%s)-[:%s]->(n:%s {name:$name}) OPTIONAL MATCH (p)-[:%s]->(e:%s) "
        "RETURN n.name AS name, p.name AS mid, collect(e.name) AS others ORDER BY mid"
        % (_L["Person"], _R["PARTICIPATED_IN"], _L["Meeting"], _R["LED"], _L["Event"])
    ),
    "I15": (
        "MATCH (p:%s)-[:%s]->(n:%s {name:$name}) OPTIONAL MATCH (p)-[r:%s]->(o:%s) "
        "RETURN n.name AS name, p.name AS mid, collect({org: o.name, position: r.position}) AS others ORDER BY mid"
        % (_L["Person"], _R["AUTHORED"], _L["Document"], _R["HELD_POSITION"], _L["Organization"])
    ),
}

# 每意图涉及的关系与方向（溯源子图组装用）：(关系, 方向)；两跳为两段
INTENT_RELATION = {
    "I2": {"Meeting": ("HELD_IN", "out"), "Event": ("OCCURRED_IN", "out")},
    "I5": ("LED", "in"),
    "I6": ("PARTICIPATED_IN", "in"),
    "I7": ("AUTHORED", "in"),
    "I8": ("AUTHORED", "out"),
    "I9": ("LED", "out"),
    "I10": ("BELONGS_TO", "in"),
    "I11": ("REORGANIZED_TO", "both"),
    "I12": ("HELD_POSITION", "out"),
    "I14": (("PARTICIPATED_IN", "in", "Person"), ("LED", "out", "Event")),
    "I15": (("AUTHORED", "in", "Person"), ("HELD_POSITION", "out", "Organization")),
}


def build(intent, entity):
    """返回 (cypher, params)；该意图对此实体类型无模板时返回 (None, None)。"""
    template = INTENT_CYPHER.get(intent)
    if template is None:
        return None, None
    if isinstance(template, dict):
        template = template.get(entity["type"])
        if template is None:
            return None, None
    return template, {"name": entity["name"]}


def relation_of(intent, label):
    """该意图涉及的 (关系, 方向)，供第⑧步组装溯源子图的边；两跳意图返回两段。"""
    spec = INTENT_RELATION.get(intent)
    if isinstance(spec, dict):
        return spec.get(label)
    return spec
