# -*- coding: utf-8 -*-
"""
时间轴（F3 / FR-G04，开发规范 6.5）：GET /api/timeline?period=

无参时返回 {periods, period, events}（一次请求完成冷启动）；
events = (e)-[:BELONGS_TO]->(p:Period) 的 Event 与 Meeting，按 time_sort 升序
（仅年 19359999 / 仅月 19350199 由补位规则自然排在末尾）；每条附 brief（intro 首句 ≤ 60 字）。
"""
import re

from backend.common import ontology as O
from backend.extensions import Neo4jUnavailable, run_read

BRIEF_MAX = 60
_SENT_END = re.compile(r"[。！？；]")

_PERIODS_CYPHER = (
    "MATCH (p:Period) RETURN p.name AS name, p.order AS order, "
    "p.start_year AS start_year, p.end_year AS end_year ORDER BY p.order"
)
_EVENTS_CYPHER = (
    "MATCH (e)-[:BELONGS_TO]->(p:Period {name:$period}) "
    "WHERE labels(e)[0] IN ['Event','Meeting'] "
    "RETURN e.name AS name, labels(e)[0] AS type, e.time_text AS time_text, "
    "e.time_sort AS time_sort, e.intro AS intro ORDER BY e.time_sort"
)


def brief_of(intro):
    """intro 首句 ≤ 60 字（规范决策⑨）。"""
    text = (intro or "").strip()
    if not text:
        return ""
    m = _SENT_END.search(text)
    first = text[:m.end()] if m else text
    return first if len(first) <= BRIEF_MAX else first[:BRIEF_MAX] + "…"


def list_periods():
    """图谱中的 Period 节点；图谱为空或未连接时回落为本体定稿的七个时期（前端页签恒可用）。"""
    try:
        rows = run_read(_PERIODS_CYPHER)
    except Neo4jUnavailable:
        rows = None
    if rows:
        return [{"name": r["name"], "order": r["order"],
                 "start_year": r["start_year"], "end_year": r["end_year"]} for r in rows]
    return [{"name": p["name"], "order": p["order"],
             "start_year": p["start_year"], "end_year": p["end_year"]} for p in O.PERIODS]


def events_of(period):
    """某时期的事件与会议，按 time_sort 升序（仅年 / 仅月条目由补位规则自然排在末尾）。"""
    try:
        rows = run_read(_EVENTS_CYPHER, period=period)
    except Neo4jUnavailable:
        return []  # 图库未连接时返回空事件列表，前端显示空态而非白屏（FR-G04）
    return [{
        "name": r["name"],
        "type": r["type"],
        "time_text": r["time_text"],
        "time_sort": r["time_sort"],
        "brief": brief_of(r["intro"]),
    } for r in rows]


def timeline(period=None):
    """时间轴数据：无参时返回时期列表 + 首个时期事件，一次请求完成冷启动（规范决策⑨）。"""
    periods = list_periods()
    current = period or (periods[0]["name"] if periods else None)
    return {"periods": periods, "period": current, "events": events_of(current) if current else []}
