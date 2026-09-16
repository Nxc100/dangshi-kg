# -*- coding: utf-8 -*-
"""
⑧ 答案生成：每意图中文回答模板 + 溯源子图 {nodes,links} + entities[{id,name,type}]（V3 6.3）。

- answer_text 只能由本模块模板基于第⑦步查询结果生成；entities / subgraph 只含本次查询实际涉及的节点与边；
- 列表类答案 ≤ 10 项，超出显示前 10 并注明总数；属性为空 / 查询为空 → "该信息暂未收录"（empty=True，由管道转兜底）。
"""
from backend.common.ontology import zh
from backend.config import Config
from backend.services import graph_service as G
from qa.cypher_builder import relation_of

MISSING_TEXT = "该信息暂未收录"

ATTR_TEMPLATES = {
    "I1": {
        "Meeting": "{name}召开于{value}。",
        "Event": "{name}发生于{value}。",
        "Organization": "{name}成立于{value}。",
        "Document": "{name}发表于{value}。",
    },
    "I3": "{name}的主要内容：{value}",
    "I4": "{name}的历史意义：{value}",
}

LIST_TEMPLATES = {
    "I2": {"Meeting": "{name}的召开地点是{list}。", "Event": "{name}发生于{list}。"},
    "I5": "{name}的领导者有：{list}。",
    "I6": "参加{name}的人物有：{list}。",
    "I7": "{name}的作者是：{list}。",
    "I8": "{name}的著作有：{list}。",
    "I9": "{name}领导过的事件有：{list}。",
    "I10": "{name}的重大事件有：{list}。",
    "I11": "{name}的组织沿革：{list}。",
    "I12": "{name}的任职情况：{list}。",
    "I14": "参加{name}的人物及其领导的事件：{list}",
    "I15": "{name}的作者及其任职：{list}",
}

ATTR_INTENTS = ("I1", "I3", "I4")
TWO_HOP_INTENTS = ("I14", "I15")


def _template(table, intent, label):
    t = table.get(intent)
    return t.get(label) if isinstance(t, dict) else t


def _fmt_list(items, sep="、"):
    """列表类答案 ≤10 项，超出显示前 10 并注明总数（V3 6.3）。"""
    total, limit = len(items), Config.ANSWER_LIST_MAX
    text = sep.join(items[:limit])
    if total > limit:
        text += "……（共 %d 项，显示前 %d 项）" % (total, limit)
    return text


def _result(text, nodes, links, empty=False):
    graph = G.build_subgraph(nodes, links)
    return {"answer_text": text, "entities": graph["nodes"], "subgraph": graph, "empty": empty}


def _item_text(intent, row):
    props = row.get("rprops") or {}
    if intent == "I11":
        time = "（%s）" % props["time_text"] if props.get("time_text") else ""
        return ("改编为%s%s" if row.get("direction") == "out" else "由%s改编而来%s") % (row["other"], time)
    if intent == "I12":
        return "%s（%s）" % (row["other"], props.get("position") or "职务未收录")
    return row["other"]


def _link_for(intent, center, row):
    spec = relation_of(intent, center["type"])
    if not spec:
        return None
    rel, direction = spec[0], spec[1]
    if direction == "both":
        direction = row.get("direction", "out")
    if direction == "out":
        return G.make_link(center["type"], center["name"], rel, row["other_type"], row["other"])
    return G.make_link(row["other_type"], row["other"], rel, center["type"], center["name"])


def _build_attr(intent, center, rows):
    value = rows[0].get("value") if rows else None
    if not value:
        return _result(MISSING_TEXT, [center], [], empty=True)
    tpl = _template(ATTR_TEMPLATES, intent, center["type"]) or "{name}：{value}"
    return _result(tpl.format(name=center["name"], value=value), [center], [])


def _build_intro(center, rows):
    props = (rows[0].get("props") if rows else None) or {}
    intro = props.get("intro")
    head = "%s（%s）" % (center["name"], zh(center["type"]))
    if not intro:
        return _result("%s：%s" % (head, MISSING_TEXT), [center], [], empty=True)
    extras = []
    for key, label in (("time_text", "时间"), ("found_time_text", "成立时间"), ("pub_time_text", "发表时间"),
                       ("birth_year", "生年"), ("death_year", "卒年"), ("org_type", "类型"), ("doc_type", "类型")):
        if props.get(key):
            extras.append("%s：%s" % (label, props[key]))
    text = "%s：%s" % (head, intro) + ("（%s）" % "；".join(extras) if extras else "")
    return _result(text, [center], [])


def _build_relation(intent, center, rows):
    if not rows:
        return _result(MISSING_TEXT, [center], [], empty=True)
    nodes, links, items = [center], [], []
    for row in rows:
        nodes.append(G.make_node(row["other_type"], row["other"]))
        link = _link_for(intent, center, row)
        if link:
            links.append(link)
        items.append(_item_text(intent, row))
    tpl = _template(LIST_TEMPLATES, intent, center["type"]) or "{name}：{list}。"
    return _result(tpl.format(name=center["name"], list=_fmt_list(items)), nodes, links)


def _build_two_hop(intent, center, rows):
    if not rows:
        return _result(MISSING_TEXT, [center], [], empty=True)
    (rel1, _d1, mid_label), (rel2, _d2, other_label) = relation_of(intent, center["type"])
    nodes, links, items = [center], [], []
    for row in rows:
        mid = G.make_node(mid_label, row["mid"])
        nodes.append(mid)
        links.append(G.make_link(mid_label, row["mid"], rel1, center["type"], center["name"]))
        parts = []
        for other in row.get("others") or []:
            if intent == "I15":
                if not other or not other.get("org"):
                    continue
                nodes.append(G.make_node(other_label, other["org"]))
                links.append(G.make_link(mid_label, row["mid"], rel2, other_label, other["org"]))
                parts.append("在%s担任%s" % (other["org"], other.get("position") or "职务未收录"))
            elif other:
                nodes.append(G.make_node(other_label, other))
                links.append(G.make_link(mid_label, row["mid"], rel2, other_label, other))
                parts.append(other)
        items.append("%s：%s" % (row["mid"], "、".join(parts) if parts else "（暂未收录）"))
    tpl = LIST_TEMPLATES[intent]
    # 两跳同样遵守"≤10 项，超出显示前 10 并注明总数"（V3 6.3）
    return _result(tpl.format(name=center["name"], list=_fmt_list(items, sep="；")), nodes, links)


def build(intent, entity, rows):
    """返回 {answer_text, entities, subgraph, empty}。"""
    center = G.make_node(entity["type"], entity["name"])
    if intent in ATTR_INTENTS:
        return _build_attr(intent, center, rows)
    if intent == "I13":
        return _build_intro(center, rows)
    if intent in TWO_HOP_INTENTS:
        return _build_two_hop(intent, center, rows)
    return _build_relation(intent, center, rows)
