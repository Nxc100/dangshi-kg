# -*- coding: utf-8 -*-
"""
知识写入口唯一实现（F6 / FR-A02 / FR-A03，开发规范 6.7）——实体与三元组的全部写操作。

强制规则：
- 蓝图层不得出现 Cypher；标签 / 关系名只从 ontology 白名单取值拼入，属性值一律参数化；
- 实体主名跨标签全局唯一；新增实体 checked=0；Event / Meeting 含 time_sort 时自动挂 BELONGS_TO；
- 级联删除的 n 实时查询；n ≥ 20 且 confirm_name ≠ name → 422；
- 双库写序：SQLite 会话内写 op_log（flush 不提交）→ 提交 Neo4j → 提交 SQLite；Neo4j 失败则 SQLite 回滚；
- 写操作后 dictionary.reload() 热刷新（新增 / 改名 / 改别名 / 删除）。
"""
import json
import logging
from datetime import datetime

from backend.common import ontology as O
from backend.common.errors import BadRequest, NotFound
from backend.common.response import page_data
from backend.config import Config
from backend.extensions import db_session, neo4j_session, run_read
from backend.models import OpLog
from kg.extract import period_assign, timeparse
from qa import dictionary

log = logging.getLogger(__name__)

_L = {label: label for label in O.LABELS}
_R = {rel: rel for rel in O.RELATIONS}

_EXISTS_CYPHER = " UNION ALL ".join(
    "MATCH (n:%s {name:$name}) RETURN '%s' AS label" % (_L[l], _L[l]) for l in O.LABELS)
_DEGREE_CYPHER = "MATCH (n:%s {name:$name})-[r]-() RETURN count(r) AS degree"
_LIST_CYPHER = (
    "MATCH (n) WHERE labels(n)[0] IN $labels AND ($kw = '' OR n.name CONTAINS $kw) "
    "RETURN n.name AS name, labels(n)[0] AS type, n.updated_at AS updated_at, "
    "coalesce(n.checked, 0) AS checked, COUNT { (n)--() } AS degree "
    "ORDER BY n.name SKIP $skip LIMIT $limit"
)
_COUNT_CYPHER = "MATCH (n) WHERE labels(n)[0] IN $labels AND ($kw = '' OR n.name CONTAINS $kw) RETURN count(n) AS c"
_TRIPLE_LIST_CYPHER = (
    "MATCH (h)-[r]->(t) WHERE ($rel = '' OR type(r) = $rel) "
    "AND ($head = '' OR h.name CONTAINS $head) AND ($tail = '' OR t.name CONTAINS $tail) "
    "RETURN h.name AS head, labels(h)[0] AS head_type, type(r) AS rel, "
    "t.name AS tail, labels(t)[0] AS tail_type, properties(r) AS props "
    "ORDER BY head, rel, tail SKIP $skip LIMIT $limit"
)
_TRIPLE_COUNT_CYPHER = (
    "MATCH (h)-[r]->(t) WHERE ($rel = '' OR type(r) = $rel) "
    "AND ($head = '' OR h.name CONTAINS $head) AND ($tail = '' OR t.name CONTAINS $tail) RETURN count(r) AS c"
)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write(fn, op_log_row):
    """双库写序：op_log flush（不提交）→ Neo4j 事务提交 → SQLite 提交。"""
    db_session.add(op_log_row)
    db_session.flush()
    try:
        with neo4j_session() as session:
            result = session.execute_write(fn)
    except Exception:
        db_session.rollback()
        raise
    try:
        db_session.commit()
    except Exception as exc:  # noqa: BLE001 —— 极低概率，记录后重试一次
        log.error("op_log 提交失败，重试：%s", exc)
        db_session.rollback()
        db_session.add(op_log_row)
        db_session.commit()
    return result


def _op(admin_id, action, object_type, object_label, object_name, summary):
    return OpLog(admin_id=admin_id, action=action, object_type=object_type, object_label=object_label,
                 object_name=object_name, summary=json.dumps(summary, ensure_ascii=False))


def find_label(name):
    """跨标签查实体主名，返回标签或 None（实体主名全局唯一）。"""
    rows = run_read(_EXISTS_CYPHER, name=name)
    return rows[0]["label"] if rows else None


def degree(name, label):
    """实体的关系数，供级联删除提示实时查询（规范 6.7：不得用列表页缓存值）。"""
    rows = run_read(_DEGREE_CYPHER % _L[label], name=name)
    return int(rows[0]["degree"]) if rows else 0


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------
def list_entities(kw="", label=None, page=1, size=10):
    """实体管理列表：名称 / 类型 / 关系数 / 核心池标记 / 更新时间（FR-A02）。"""
    labels = [label] if label else list(O.LABELS)
    total = run_read(_COUNT_CYPHER, labels=labels, kw=kw or "")[0]["c"]
    rows = run_read(_LIST_CYPHER, labels=labels, kw=kw or "", skip=(page - 1) * size, limit=size)
    return page_data([dict(r) for r in rows], page, size, int(total))


def list_triples(head="", tail="", rel=None, page=1, size=10):
    """关系管理列表：头实体、关系（附中文名）、尾实体与关系属性（FR-A03）。"""
    params = {"head": head or "", "tail": tail or "", "rel": rel or "",
              "skip": (page - 1) * size, "limit": size}
    total = run_read(_TRIPLE_COUNT_CYPHER, **{k: params[k] for k in ("head", "tail", "rel")})[0]["c"]
    rows = run_read(_TRIPLE_LIST_CYPHER, **params)
    items = [dict(r, label=O.RELATION_ZH.get(r["rel"], r["rel"])) for r in rows]
    return page_data(items, page, size, int(total))


# ---------------------------------------------------------------------------
# 实体写操作
# ---------------------------------------------------------------------------
def _derive_time(label, props):
    """表单只填 time_text，后端派生 time_sort / time_precision；解析失败 → 422 可读提示。"""
    field = {"Event": "time_text", "Meeting": "time_text",
             "Organization": "found_time_text", "Document": "pub_time_text"}.get(label)
    if not field or not props.get(field):
        return props
    time_sort, precision = timeparse.parse(props[field])
    if time_sort is None:
        raise BadRequest("时间格式无法识别，请按「1935 年 1 月 15 日」格式填写", errors={field: "时间格式无法识别"})
    props["time_sort"] = time_sort
    if label in ("Event", "Meeting"):
        props["time_precision"] = precision
    return props


def create_entity(admin_id, label, name, props):
    """新增实体：主名跨标签全局唯一，checked=0，Event / Meeting 自动挂时期（规范 6.7 / 决策⑦）。"""
    exists = find_label(name)
    if exists:
        raise BadRequest("实体已存在，是否前往编辑？", data={"exists_type": exists})
    props = _derive_time(label, dict(props))
    props.update({"name": name, "checked": 0, "updated_at": _now()})
    period = period_assign.assign(props.get("time_sort")) if label in ("Event", "Meeting") else None

    def _fn(tx):
        tx.run("MERGE (n:%s {name:$name}) SET n += $props" % _L[label], name=name, props=props)
        if period:  # 新增事件 / 会议自动归属时期（规范决策⑦）
            tx.run("MATCH (n:%s {name:$name}) MATCH (p:Period {name:$period}) MERGE (n)-[:BELONGS_TO]->(p)"
                   % _L[label], name=name, period=period)
        return True

    _write(_fn, _op(admin_id, "add", "entity", label, name, {"props": props, "period": period}))
    dictionary.reload()
    return {"name": name, "type": label, "period": period}


def update_entity(admin_id, label, name, props, new_name=None, checked=None):
    """
    编辑实体（规范 6.7 / 规范决策⑦）。
    改名时校验新名跨标签全局唯一；checked 传 0/1 时同步"已校验"标记；
    Event / Meeting 的时间被改动后按新 time_sort 重算 BELONGS_TO，避免时期归属滞留旧值。
    """
    if find_label(name) != label:
        raise NotFound("实体不存在")
    if new_name and new_name != name and find_label(new_name):
        raise BadRequest("新名称已被占用", errors={"new_name": "该名称已存在"})
    props = _derive_time(label, dict(props))
    props["updated_at"] = _now()
    props.pop("name", None)
    if checked in (0, 1, "0", "1"):
        props["checked"] = int(checked)
    target = new_name or name
    period = period_assign.assign(props.get("time_sort")) if label in ("Event", "Meeting") else None

    def _fn(tx):
        tx.run("MATCH (n:%s {name:$name}) SET n += $props" % _L[label], name=name, props=props)
        if new_name and new_name != name:
            tx.run("MATCH (n:%s {name:$name}) SET n.name = $new_name" % _L[label], name=name, new_name=new_name)
        if props.get("time_sort"):  # 时间变更后重挂时期，先删旧的 BELONGS_TO 再 MERGE 新的
            tx.run("MATCH (n:%s {name:$name})-[r:BELONGS_TO]->(:Period) DELETE r" % _L[label], name=target)
            if period:
                tx.run("MATCH (n:%s {name:$name}) MATCH (p:Period {name:$period}) "
                       "MERGE (n)-[:BELONGS_TO]->(p)" % _L[label], name=target, period=period)
        return True

    _write(_fn, _op(admin_id, "edit", "entity", label, target,
                    {"props": props, "renamed_from": name if new_name else None, "period": period}))
    dictionary.reload()
    return {"name": target, "type": label, "period": period}


def delete_entity(admin_id, label, name, confirm_name=None):
    """删除实体：级联关系数实时查询，≥20 需输入名称确认；DETACH DELETE 并刷新词典（规范 6.7）。"""
    if find_label(name) != label:
        raise NotFound("实体不存在")
    n = degree(name, label)
    if n >= Config.HIGH_DEGREE_THRESHOLD and confirm_name != name:
        raise BadRequest("高连接度实体需输入名称确认", data={"degree": n, "require_confirm": True})

    def _fn(tx):
        tx.run("MATCH (n:%s {name:$name}) DETACH DELETE n" % _L[label], name=name)
        return True

    _write(_fn, _op(admin_id, "delete", "entity", label, name, {"cascade_relations": n}))
    dictionary.reload()
    return {"name": name, "type": label, "cascade_relations": n}


# ---------------------------------------------------------------------------
# 三元组写操作
# ---------------------------------------------------------------------------
def _check_triple(head, head_type, rel, tail, tail_type, props):
    if head == tail:
        raise BadRequest("头尾实体不能相同", errors={"tail": "头尾实体不能相同"})
    if not O.is_allowed(head_type, rel, tail_type):
        raise BadRequest("该类型组合不允许此关系", errors={"rel": "该类型组合不允许此关系"})
    if find_label(head) != head_type:
        raise BadRequest("实体不存在，请先新增实体", errors={"head": "头实体不存在或类型不符"})
    if find_label(tail) != tail_type:
        raise BadRequest("实体不存在，请先新增实体", errors={"tail": "尾实体不存在或类型不符"})
    cleaned = {}
    for p in O.RELATION_PROPS.get(rel, []):
        value = (props or {}).get(p["name"])
        value = value.strip() if isinstance(value, str) else value
        if p["required"] and not value:
            raise BadRequest("%s为必填项" % p["zh"], errors={p["name"]: "%s为必填项" % p["zh"]})
        if value:
            cleaned[p["name"]] = value
    return cleaned


def create_triple(admin_id, head, head_type, rel, tail, tail_type, props=None):
    """新增三元组：头尾须存在、组合须符合本体约束、拒绝自指，重复提示「该关系已存在」（规范 6.7）。"""
    cleaned = _check_triple(head, head_type, rel, tail, tail_type, props)
    exists = run_read(
        "MATCH (h:%s {name:$head})-[r:%s]->(t:%s {name:$tail}) RETURN count(r) AS c"
        % (_L[head_type], _R[rel], _L[tail_type]), head=head, tail=tail)
    if exists and int(exists[0]["c"]) > 0:
        raise BadRequest("该关系已存在")

    def _fn(tx):
        tx.run("MATCH (h:%s {name:$head}) MATCH (t:%s {name:$tail}) MERGE (h)-[r:%s]->(t) SET r += $props"
               % (_L[head_type], _L[tail_type], _R[rel]), head=head, tail=tail, props=cleaned)
        return True

    _write(_fn, _op(admin_id, "add", "triple", rel, "%s → %s" % (head, tail),
                    {"head_type": head_type, "tail_type": tail_type, "props": cleaned}))
    return {"head": head, "rel": rel, "tail": tail}


def delete_triple(admin_id, head, head_type, rel, tail, tail_type):
    """删除三元组，同步写 op_log（规范 6.7）。"""
    if not O.is_allowed(head_type, rel, tail_type):
        raise BadRequest("该类型组合不允许此关系", errors={"rel": "该类型组合不允许此关系"})
    exists = run_read(
        "MATCH (h:%s {name:$head})-[r:%s]->(t:%s {name:$tail}) RETURN count(r) AS c"
        % (_L[head_type], _R[rel], _L[tail_type]), head=head, tail=tail)
    if not exists or int(exists[0]["c"]) == 0:
        raise NotFound("关系不存在")

    def _fn(tx):
        tx.run("MATCH (h:%s {name:$head})-[r:%s]->(t:%s {name:$tail}) DELETE r"
               % (_L[head_type], _R[rel], _L[tail_type]), head=head, tail=tail)
        return True

    _write(_fn, _op(admin_id, "delete", "triple", rel, "%s → %s" % (head, tail),
                    {"head_type": head_type, "tail_type": tail_type}))
    return {"head": head, "rel": rel, "tail": tail}


# ---------------------------------------------------------------------------
# 操作日志（只读，无删除接口）
# ---------------------------------------------------------------------------
def list_oplog(action=None, date_from=None, date_to=None, page=1, size=10):
    """知识操作日志：只读、倒序分页，按动作与日期筛选（FR-A04；op_log 只增不删）。"""
    from backend.models import User

    q = db_session.query(OpLog, User.username).outerjoin(User, OpLog.admin_id == User.id)
    if action:
        q = q.filter(OpLog.action == action)
    if date_from:
        q = q.filter(OpLog.created_at >= "%s 00:00:00" % date_from)
    if date_to:
        q = q.filter(OpLog.created_at <= "%s 23:59:59" % date_to)
    q = q.order_by(OpLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    items = [dict(r.to_dict(), admin_name=u or "-") for r, u in rows]
    return page_data(items, page, size, total)
