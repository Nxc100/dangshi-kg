# -*- coding: utf-8 -*-
"""
每日学习（F8 / FR-G01，开发规范 6.5）：GET /api/daily

- 今日推荐 = random.Random(int(YYYYMMDD)).choice(核心池按 name 排序列表)，核心池 = checked=1 的七类实体，
  全站当日一致、跨日 0 点后变化；核心池为空时回落为全部实体，仍为空则返回 None（前端降级引导语）。
- 历史上的今天 = time_precision='day' 且 time_sort 的 MMDD 与今日相同的 Event / Meeting；
  为空数组时前端整栏隐藏（唯一不显示空态处）。
"""
import random
from datetime import date

from backend.services.timeline_service import brief_of
from backend.extensions import Neo4jUnavailable, run_read

_POOL_CYPHER = (
    "MATCH (n) WHERE labels(n)[0] IN $labels AND n.checked = 1 "
    "RETURN n.name AS name, labels(n)[0] AS type, n.intro AS intro ORDER BY n.name"
)
_POOL_FALLBACK_CYPHER = (
    "MATCH (n) WHERE labels(n)[0] IN $labels "
    "RETURN n.name AS name, labels(n)[0] AS type, n.intro AS intro ORDER BY n.name LIMIT 500"
)
_TODAY_CYPHER = (
    "MATCH (e) WHERE labels(e)[0] IN ['Event','Meeting'] AND e.time_precision = 'day' "
    "AND substring(e.time_sort, 4, 4) = $mmdd "
    "RETURN e.name AS name, labels(e)[0] AS type, e.time_text AS time_text, "
    "e.intro AS intro ORDER BY e.time_sort"
)


def daily(today=None):
    """每日学习：今日推荐（日期为随机种子，全站当日一致）+ 历史上的今天（FR-G01）。"""
    from backend.common.ontology import LABELS

    today = today or date.today()
    try:
        rows = run_read(_POOL_CYPHER, labels=LABELS) or run_read(_POOL_FALLBACK_CYPHER, labels=LABELS)
        events = run_read(_TODAY_CYPHER, mmdd=today.strftime("%m%d"))
    except Neo4jUnavailable:
        # 图库未连接：首页降级为固定引导语 + 示例问句，不白屏（FR-G01）
        return {"recommend": None, "today_events": [], "date": today.strftime("%Y-%m-%d"), "degraded": True}

    recommend = None
    if rows:
        seed = int(today.strftime("%Y%m%d"))
        pick = random.Random(seed).choice(rows)
        recommend = {"name": pick["name"], "type": pick["type"], "intro": brief_of(pick["intro"]) or (pick["intro"] or "")}

    today_events = [{
        "name": r["name"], "type": r["type"], "time_text": r["time_text"], "brief": brief_of(r["intro"]),
    } for r in events]

    return {"recommend": recommend, "today_events": today_events, "date": today.strftime("%Y-%m-%d")}
