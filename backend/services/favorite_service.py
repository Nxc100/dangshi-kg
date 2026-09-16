# -*- coding: utf-8 -*-
"""
收藏（FR-U05，开发规范 6.8）：唯一索引 (user_id, fav_type, ref_id) 保证幂等；取消校验归属；
fav_type=entity 的 ref_id 存实体主名，fav_type=qa 存 qa_log.id；
被收藏实体若已被后台删除，列表项标记 deleted=True（前端显示"词条已删除"并可移除）。
"""
from backend.common.errors import BadRequest, NotFound
from backend.common.response import page_data
from backend.extensions import db_session
from backend.models import Favorite, QaLog

FAV_TYPES = ("entity", "qa")


def _check_type(fav_type):
    if fav_type not in FAV_TYPES:
        raise BadRequest("收藏类型不合法", errors={"fav_type": "fav_type 只能为 entity 或 qa"})
    return fav_type


def exists(user_id, fav_type, ref_id):
    """收藏态查询，供百科页按钮初始状态使用（FR-U05）。"""
    return db_session.query(Favorite).filter_by(
        user_id=user_id, fav_type=fav_type, ref_id=str(ref_id)).first() is not None


def _check_qa_owner(user_id, ref_id):
    """fav_type=qa 时 ref_id 为 qa_log.id：必须是本人的问答记录，防止越权收藏并读取他人问答。"""
    if not str(ref_id).isdigit():
        raise BadRequest("问答记录标识不合法", errors={"ref_id": "问答记录标识不合法"})
    owned = db_session.query(QaLog.id).filter(QaLog.id == int(ref_id), QaLog.user_id == user_id).first()
    if owned is None:
        raise NotFound("问答记录不存在")


def add(user_id, fav_type, ref_id):
    """幂等：重复收藏返回既有记录，不报错、不产生重复行。"""
    _check_type(fav_type)
    ref_id = str(ref_id).strip()
    if not ref_id:
        raise BadRequest("收藏对象不能为空", errors={"ref_id": "收藏对象不能为空"})
    if fav_type == "qa":
        _check_qa_owner(user_id, ref_id)
    row = db_session.query(Favorite).filter_by(user_id=user_id, fav_type=fav_type, ref_id=ref_id).first()
    if row is None:
        row = Favorite(user_id=user_id, fav_type=fav_type, ref_id=ref_id)
        db_session.add(row)
        db_session.commit()
    return row.to_dict()


def remove(user_id, fav_type, ref_id):
    """取消收藏，校验记录归属（规范 6.1）。"""
    _check_type(fav_type)
    row = db_session.query(Favorite).filter_by(user_id=user_id, fav_type=fav_type, ref_id=str(ref_id)).first()
    if row is None:
        raise NotFound("收藏不存在")
    db_session.delete(row)
    db_session.commit()
    return True


def _entity_items(rows):
    """一次批量查回本页全部实体的类型，避免逐行查询（N+1）。"""
    from backend.extensions import neo4j_available, run_read

    types = {}
    names = [r.ref_id for r in rows]
    if names and neo4j_available():
        try:
            for hit in run_read("MATCH (n) WHERE n.name IN $names "
                                "RETURN n.name AS name, labels(n)[0] AS label", names=names):
                types[hit["name"]] = hit["label"]
        except Exception:  # noqa: BLE001 —— 图库异常时按未知处理，不阻断收藏夹
            types = {}
    return [{
        "id": r.id, "fav_type": r.fav_type, "ref_id": r.ref_id,
        "name": r.ref_id, "type": types.get(r.ref_id),
        # 被后台删除的实体在收藏夹显示"词条已删除"并可移除（规范 6.8）
        "deleted": r.ref_id not in types, "created_at": r.to_dict()["created_at"],
    } for r in rows]


def _qa_items(user_id, rows):
    """问答收藏项只回填本人的 qa_log，杜绝越权读取他人问答内容。"""
    ids = [int(r.ref_id) for r in rows if str(r.ref_id).isdigit()]
    logs = {}
    if ids:
        owned = db_session.query(QaLog).filter(QaLog.id.in_(ids), QaLog.user_id == user_id).all()
        logs = {l.id: l for l in owned}
    items = []
    for r in rows:
        log = logs.get(int(r.ref_id)) if str(r.ref_id).isdigit() else None
        items.append({
            "id": r.id, "fav_type": r.fav_type, "ref_id": r.ref_id,
            "question": log.question if log else "",
            "answer": log.answer if log else "",
            "deleted": log is None, "created_at": r.to_dict()["created_at"],
        })
    return items


def list_favorites(user_id, fav_type, page, size):
    """收藏夹分页：实体页签回填类型与删除态，问答页签只回填本人 qa_log（FR-U05）。"""
    _check_type(fav_type)
    q = (db_session.query(Favorite)
         .filter_by(user_id=user_id, fav_type=fav_type)
         .order_by(Favorite.id.desc()))
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    items = _entity_items(rows) if fav_type == "entity" else _qa_items(user_id, rows)
    return page_data(items, page, size, total)
