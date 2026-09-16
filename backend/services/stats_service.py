# -*- coding: utf-8 -*-
"""
统计口径唯一实现（F10 / FR-A07 / FR-L04，开发规范 6.8）：后台总览四数字 + 看板五图 + LLM 三指标。

- 数据全部来自 qa_log 聚合（不看 user_visible，用户删除历史不影响计数）与 Neo4j 计数；
- 近 30 天趋势按日 GROUP BY，无记录日期补零；兜底率 = fallback=1 ÷ 总数；
- LLM 三指标（近 30 天）：调用次数 = llm_latency_ms IS NOT NULL；成功率 = llm ÷（llm + 降级）；平均时延 = AVG。
- 无缓存，每次"刷新"重新聚合。
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func

from backend.extensions import db_session, neo4j_available, run_read
from backend.models import QaLog, User

TOP_N = 10
TREND_DAYS = 30


def _graph_counts():
    if not neo4j_available():
        return 0, 0
    try:
        nodes = run_read("MATCH (n) RETURN count(n) AS c")[0]["c"]
        rels = run_read("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        return int(nodes), int(rels)
    except Exception:  # noqa: BLE001 —— 图库异常时总览显示 0，不阻断页面
        return 0, 0


def overview():
    """后台总览四数字卡：实体总数 / 关系总数 / 注册用户数 / 今日问答量。"""
    entity_count, relation_count = _graph_counts()
    today = date.today().strftime("%Y-%m-%d")
    today_qa = (db_session.query(func.count(QaLog.id))
                .filter(func.date(QaLog.created_at) == today).scalar() or 0)
    return {
        "entity_count": entity_count,
        "relation_count": relation_count,
        "user_count": db_session.query(func.count(User.id)).scalar() or 0,
        "today_qa_count": int(today_qa),
    }


def _top_questions():
    rows = (db_session.query(QaLog.question, func.count(QaLog.id).label("c"))
            .group_by(QaLog.question).order_by(func.count(QaLog.id).desc()).limit(TOP_N).all())
    return [{"name": q, "value": int(c)} for q, c in rows]


def _top_entities():
    """matched_entity 以 | 分隔存多实体，拆分后计数。"""
    counter = {}
    for (value,) in db_session.query(QaLog.matched_entity).filter(QaLog.matched_entity.isnot(None)).all():
        for name in (value or "").split("|"):
            name = name.strip()
            if name:
                counter[name] = counter.get(name, 0) + 1
    top = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    return [{"name": n, "value": v} for n, v in top]


def _intent_dist():
    rows = (db_session.query(QaLog.intent, func.count(QaLog.id))
            .group_by(QaLog.intent).order_by(func.count(QaLog.id).desc()).all())
    return [{"name": i or "UNKNOWN", "value": int(c)} for i, c in rows]


def _trend():
    """近 30 天按日问答量，无记录日期补零（前端不自行计算）。"""
    start = date.today() - timedelta(days=TREND_DAYS - 1)
    rows = (db_session.query(func.date(QaLog.created_at), func.count(QaLog.id))
            .filter(QaLog.created_at >= datetime.combine(start, datetime.min.time()))
            .group_by(func.date(QaLog.created_at)).all())
    counts = {str(d): int(c) for d, c in rows}
    return [{"date": str(start + timedelta(days=i)),
             "value": counts.get(str(start + timedelta(days=i)), 0)} for i in range(TREND_DAYS)]


def _llm_metrics():
    since = datetime.combine(date.today() - timedelta(days=TREND_DAYS - 1), datetime.min.time())
    base = db_session.query(QaLog).filter(QaLog.created_at >= since, QaLog.llm_latency_ms.isnot(None))
    calls = base.count()
    success = base.filter(QaLog.answer_source == "llm").count()
    avg = (db_session.query(func.avg(QaLog.llm_latency_ms))
           .filter(QaLog.created_at >= since, QaLog.llm_latency_ms.isnot(None)).scalar())
    return {
        "calls": calls,
        "success_rate": round(success / calls, 4) if calls else 0.0,
        "avg_latency_ms": int(avg) if avg else 0,
    }


def dashboard():
    """GET /api/stats/overview 一次返回全部（五图 + 兜底率 + LLM 三指标）。"""
    total = db_session.query(func.count(QaLog.id)).scalar() or 0
    fallback_count = db_session.query(func.count(QaLog.id)).filter(QaLog.fallback == 1).scalar() or 0
    return {
        "top_questions": _top_questions(),
        "top_entities": _top_entities(),
        "intent_dist": _intent_dist(),
        "trend_30d": _trend(),
        "total": int(total),
        "fallback_count": int(fallback_count),
        "fallback_rate": round(fallback_count / total, 4) if total else 0.0,
        "llm": _llm_metrics(),
    }
