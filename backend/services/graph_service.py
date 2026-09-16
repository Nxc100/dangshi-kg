# -*- coding: utf-8 -*-
"""
子图组装唯一实现 + 图谱页三接口（开发规范 4.3 / 6.5）。

子图数据契约：{nodes:[{id,name,type}], links:[{source,target,relation,label}]}
  - id = "{label}:{name}" 由 node_id() 唯一生成；type 为英文标签；relation 为 Cypher 关系名、label 为中文名
  - 图谱页 2 跳 / 百科 1 跳 / 问答溯源三处产出同构结构
图谱数据不做任何应用层缓存（保证"后台改前台即时生效"）。
"""
from rapidfuzz import fuzz, process

from backend.common import ontology as O
from backend.common.errors import NotFound
from backend.config import Config
from backend.extensions import run_read
from qa import dictionary

_L = {label: label for label in O.LABELS}  # 标签白名单

_FIND_CYPHER = " UNION ALL ".join(
    "MATCH (n:%s {name:$name}) RETURN '%s' AS label, properties(n) AS props" % (_L[label], _L[label])
    for label in O.LABELS
)
# 一跳边（与中心直接相连）排在前面，保证 LIMIT 截断时优先保留一跳邻居；排序在数据库侧完成
_EDGES_CYPHER = (
    "MATCH (c:%s {name:$name})-[rs*1..%d]-() UNWIND rs AS r WITH DISTINCT r, c "
    "MATCH (a)-[r]->(b) "
    "WITH a, b, r, CASE WHEN a = c OR b = c THEN 0 ELSE 1 END AS hop "
    "ORDER BY hop, a.name, b.name "
    "RETURN labels(a)[0] AS sa, a.name AS na, type(r) AS rel, labels(b)[0] AS sb, b.name AS nb "
    "LIMIT $edge_limit"
)
_DEGREE_CYPHER = "MATCH (n:%s {name:$name})-[r]-() RETURN count(r) AS degree"
_NEIGHBOR_CYPHER = (
    "MATCH (n:%s {name:$name})-[r]-(m) "
    "RETURN type(r) AS rel, labels(m)[0] AS neighbor_type, m.name AS neighbor, "
    "CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END AS direction, properties(r) AS rprops "
    "ORDER BY rel, neighbor"
)


# ---------------------------------------------------------------------------
# 结构组装（纯函数，qa/answer_builder 与各 service 共用）
# ---------------------------------------------------------------------------
def node_id(label, name):
    return "%s:%s" % (label, name)


def make_node(label, name):
    return {"id": node_id(label, name), "name": name, "type": label}


def make_link(src_label, src_name, rel, dst_label, dst_name):
    return {
        "source": node_id(src_label, src_name),
        "target": node_id(dst_label, dst_name),
        "relation": rel,
        "label": O.RELATION_ZH.get(rel, rel),
    }


def build_subgraph(nodes, links):
    """去重后返回 {nodes, links}；links 只保留两端都存在的边。"""
    node_map = {}
    for n in nodes:
        node_map.setdefault(n["id"], n)
    seen, out_links = set(), []
    for l in links:
        key = (l["source"], l["target"], l["relation"])
        if key in seen or l["source"] not in node_map or l["target"] not in node_map:
            continue
        seen.add(key)
        out_links.append(l)
    return {"nodes": list(node_map.values()), "links": out_links}


# ---------------------------------------------------------------------------
# 图谱查询
# ---------------------------------------------------------------------------
def find_node(name):
    """按七标签依次查找（唯一约束索引）；返回 {name, type, props} 或 None。"""
    rows = run_read(_FIND_CYPHER, name=name)
    if not rows:
        return None
    return {"name": name, "type": rows[0]["label"], "props": rows[0]["props"] or {}}


def require_node(name):
    node = find_node(name)
    if node is None:
        raise NotFound("未找到该词条")
    return node


def degree(name, label=None):
    label = label or (find_node(name) or {}).get("type")
    if label not in _L:
        return 0
    rows = run_read(_DEGREE_CYPHER % _L[label], name=name)
    return int(rows[0]["degree"]) if rows else 0


def run_read_neighbors(label, name):
    """百科页用：某实体的全部 1 跳邻居（含关系方向与关系属性）。"""
    return run_read(_NEIGHBOR_CYPHER % _L[label], name=name)


def _edge_rows(label, name, hops, edge_limit):
    """取中心实体的 1 / 2 跳边；一跳优先由 Cypher 的 ORDER BY 保证（截断前排序）。"""
    hops = 2 if hops not in (1, 2) else hops
    return run_read(_EDGES_CYPHER % (_L[label], hops), name=name, edge_limit=int(edge_limit))


def _assemble(center, rows, limit):
    nodes = {center["id"]: center}
    links, truncated = [], False
    for r in rows:
        src, dst = make_node(r["sa"], r["na"]), make_node(r["sb"], r["nb"])
        for n in (src, dst):
            if n["id"] not in nodes:
                if len(nodes) >= limit:
                    truncated = True
                    continue
                nodes[n["id"]] = n
        if src["id"] in nodes and dst["id"] in nodes:
            links.append(make_link(r["sa"], r["na"], r["rel"], r["sb"], r["nb"]))
    graph = build_subgraph(nodes.values(), links)
    graph["truncated"] = truncated
    graph["center"] = center
    return graph


def subgraph(name, hops=2, limit=None):
    """以实体为中心的 1 / 2 跳子图；孤立节点返回仅含自身的 nodes 与空 links；不存在 → 404。"""
    limit = limit or Config.SUBGRAPH_LIMIT
    node = require_node(name)
    center = make_node(node["type"], name)
    rows = _edge_rows(node["type"], name, hops, edge_limit=limit * 4)
    return _assemble(center, rows, limit)


def neighbors(name, limit=None):
    """1 跳邻居（≤ limit），前端合并去重后追加到画布。"""
    return subgraph(name, hops=1, limit=limit or Config.SUBGRAPH_LIMIT)


def search(kw, limit=10):
    """搜索联想：词典前缀匹配 + rapidfuzz 模糊候选，别名命中回链主名，返回 ≤ limit 条 {name, type}。"""
    d = dictionary.get()
    terms = d.terms()
    if not terms:
        return []
    ordered = [t for t in terms if t.startswith(kw)]
    ordered += [t for t in terms if kw in t and t not in ordered]
    if len(ordered) < limit:
        for term, score, _idx in process.extract(kw, terms, scorer=fuzz.partial_ratio, limit=limit * 2, score_cutoff=60):
            if term not in ordered:
                ordered.append(term)
    out, seen = [], set()
    for term in ordered:
        name, label = d.lookup(term)
        if name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "type": label})
        if len(out) >= limit:
            break
    return out
