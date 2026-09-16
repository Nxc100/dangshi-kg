# -*- coding: utf-8 -*-
"""
实体百科页聚合（F4 / FR-G05，开发规范 6.5）：GET /api/entity/<name> 一次返回全部。

{entity:{name,type,alias[],props{}}, intro, source, relations:[{relation,label,direction,neighbor_type,items}],
 subgraph(1 跳), favorited}
props 只含非空字段（时间展示 time_text）；按七标签依次查找，均不存在 → 404。
"""
from backend.common import ontology as O
from backend.services import graph_service as G
from qa import dictionary

# 关系分组的中文标题：(关系, 方向) -> 标题
_GROUP_TITLE = {
    ("LED", "in"): "领导者",
    ("LED", "out"): "领导的事件",
    ("PARTICIPATED_IN", "in"): "出席人物",
    ("PARTICIPATED_IN", "out"): "参加的会议",
    ("AUTHORED", "in"): "作者",
    ("AUTHORED", "out"): "创作的文献",
    ("HELD_POSITION", "in"): "任职人员",
    ("HELD_POSITION", "out"): "任职组织",
    ("HELD_IN", "in"): "在此召开的会议",
    ("HELD_IN", "out"): "召开地点",
    ("OCCURRED_IN", "in"): "在此发生的事件",
    ("OCCURRED_IN", "out"): "发生地点",
    ("PRODUCED", "in"): "形成于",
    ("PRODUCED", "out"): "形成文献",
    ("FOUNDED", "in"): "创建于",
    ("FOUNDED", "out"): "创建的组织",
    ("REORGANIZED_TO", "in"): "前身",
    ("REORGANIZED_TO", "out"): "改编为",
    ("BELONGS_TO", "in"): "该时期的事件",
    ("BELONGS_TO", "out"): "所属时期",
}


def detail(name, user_id=None):
    """百科页聚合：属性、简介与出处、按「关系 × 邻居类型」分组的关联实体、1 跳子图、收藏态（FR-G05）。"""
    node = G.require_node(name)
    label, props = node["type"], dict(node["props"] or {})
    rows = G.run_read_neighbors(label, name)

    groups = {}
    nodes, links = [G.make_node(label, name)], []
    for r in rows:
        key = (r["rel"], r["direction"])
        group = groups.setdefault(key, {
            "relation": r["rel"],
            "label": O.RELATION_ZH.get(r["rel"], r["rel"]),
            "direction": r["direction"],
            "neighbor_type": r["neighbor_type"],
            "title": _GROUP_TITLE.get(key, O.RELATION_ZH.get(r["rel"], r["rel"])),
            "items": [],
        })
        item = {"name": r["neighbor"], "type": r["neighbor_type"]}
        if r["rel"] == "HELD_POSITION" and (r.get("rprops") or {}).get("position"):
            item["position"] = r["rprops"]["position"]
        group["items"].append(item)
        nodes.append(G.make_node(r["neighbor_type"], r["neighbor"]))
        if r["direction"] == "out":
            links.append(G.make_link(label, name, r["rel"], r["neighbor_type"], r["neighbor"]))
        else:
            links.append(G.make_link(r["neighbor_type"], r["neighbor"], r["rel"], label, name))

    intro = props.pop("intro", "") or ""
    source = props.pop("source", "") or ""
    alias = dictionary.split_alias(props.pop("alias", ""))
    visible = {p["name"] for p in O.props_of(label)} - {"intro", "source", "alias"}
    clean_props = {k: v for k, v in props.items() if k in visible and v not in (None, "")}

    favorited = False
    if user_id:
        from backend.services import favorite_service
        favorited = favorite_service.exists(user_id, "entity", name)

    return {
        "entity": {"name": name, "type": label, "alias": alias, "props": clean_props,
                   "checked": int(props.get("checked", 0) or 0)},
        "intro": intro,
        "source": source,
        "relations": list(groups.values()),
        "subgraph": G.build_subgraph(nodes, links),
        "favorited": favorited,
    }
