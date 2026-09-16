# -*- coding: utf-8 -*-
"""
问答管道唯一入口：answer(question, ctx) —— 命令行版 qa.cli 与 POST /api/qa 共用（开发规范 6.3）。

ctx：{use_llm: bool, prev_q: str, prev_a: str, user_id: int|None}
响应（V3 6.3 六字段 + FRS 边界字段 + LLM-Design 4.6 增量）：
  answer_text, intent, entities, subgraph, fallback, log_id, candidates, clarify, rewritten_from,
  answer_source(kg/passage/llm), fallback_passages, llm；另附 _meta（llm_latency_ms / llm_detail，仅供落库，接口层剥离）
三类边界（未识别实体 candidates / 属性缺失 / 槽位不符 clarify）均为业务响应，不是错误。
LLM 仅在两处以 try-import 引用（⓪追问改写 / 兜底生成），导入失败即视为系统层关闭。
"""
import logging

from neo4j import exceptions as neo4j_exceptions

from backend.extensions import Neo4jUnavailable
from backend.services import graph_service as G
from qa import (answer_builder, cypher_builder, entity_linker, fallback, graph_query, intent_classifier,
                pos_tagger, slot_checker, tokenizer)

log = logging.getLogger(__name__)

# 判定为"图库不可用"从而降级兜底的异常；其余异常（如 Cypher 语法错误）照常抛出为 500
_UNAVAILABLE = (Neo4jUnavailable, neo4j_exceptions.ServiceUnavailable,
                neo4j_exceptions.SessionExpired, neo4j_exceptions.AuthError)

GUIDE_TEXT = "抱歉，暂未找到相关资料。您可以换个问法，或试试下面的示例问题。"


def _base(question):
    return {
        "answer_text": "",
        "intent": "UNKNOWN",
        "entities": [],
        "subgraph": {"nodes": [], "links": []},
        "fallback": False,
        "log_id": None,
        "candidates": [],
        "clarify": None,
        "rewritten_from": None,
        "answer_source": "kg",
        "fallback_passages": [],
        "llm": None,
        "question": question,
        # _meta 仅供接口层落库，返回前由 strip_meta 剥离
        # linked_entities：第③步实体链接的主名列表，qa_log.matched_entity 的唯一来源
        # （不能用 entities，后者含第⑧步溯源子图的邻居节点，会污染高频实体统计）
        "_meta": {"llm_latency_ms": None, "llm_detail": None, "linked_entities": []},
    }


def _llm_wanted(ctx):
    if not ctx.get("use_llm"):
        return False
    try:
        from llm import config as llm_config
    except Exception:  # noqa: BLE001 —— llm/ 目录被移除即视为系统层关闭
        return False
    return llm_config.available()


def rewrite_should(question, entities):
    """⓪ 追问改写的触发判定（FR-L03）：实体识别三级全未中即触发；llm/ 不可用时恒为 False。"""
    try:
        from llm import rewrite
    except Exception:  # noqa: BLE001 —— llm/ 目录被移除即视为系统层关闭
        return False
    return rewrite.should_rewrite(question, entities)


def _try_rewrite(question, ctx):
    """调用改写并返回独立问句；未携带上一轮问答、开关未开或改写失败均返回 None。"""
    if not ctx.get("prev_q") or not _llm_wanted(ctx):
        return None
    try:
        from llm import rewrite
    except Exception:  # noqa: BLE001
        return None
    return rewrite.rewrite(question, ctx.get("prev_q"), ctx.get("prev_a") or "")


def _fallback(resp, question, ctx, keep_text=False):
    resp["fallback"] = True
    passages = fallback.retrieve(question)
    resp["fallback_passages"] = passages
    resp["answer_source"] = "passage"
    if not keep_text:
        resp["answer_text"] = "" if passages else GUIDE_TEXT
    if passages and _llm_wanted(ctx):
        try:
            from llm import generator
        except Exception:  # noqa: BLE001
            return resp
        outcome = generator.generate(question, passages)
        resp["_meta"]["llm_latency_ms"] = outcome.get("latency_ms")
        resp["_meta"]["llm_detail"] = outcome.get("detail")
        if outcome.get("text"):
            resp["llm"] = {"text": outcome["text"], "cited": outcome.get("cited", []), "latency_ms": outcome.get("latency_ms")}
            resp["answer_source"] = "llm"
    return resp


def _run(question, ctx, rewritten_from=None, allow_rewrite=True):
    resp = _base(question)
    resp["rewritten_from"] = rewritten_from
    tokens = tokenizer.cut(question)  # ①
    feats = pos_tagger.features(pos_tagger.tag(question), question)  # ②
    entities = entity_linker.link(question, tokens)  # ③
    if allow_rewrite and rewrite_should(question, entities):
        new_q = _try_rewrite(question, ctx)
        if new_q and new_q != question:
            return _run(new_q, ctx, rewritten_from=question, allow_rewrite=False)
    resp["_meta"]["linked_entities"] = [e["name"] for e in entities]
    intent = intent_classifier.classify(question, feats, entities)  # ④
    resp["intent"] = intent
    if not entities:
        resp["candidates"] = entity_linker.suggest(question)
        return _fallback(resp, question, ctx)
    clarify = slot_checker.check(intent, entities)  # ⑤
    if clarify:
        resp["clarify"] = clarify
        resp["answer_text"] = clarify["text"]
        resp["entities"] = [G.make_node(e["type"], e["name"]) for e in entities]
        return resp
    if intent == "UNKNOWN":
        resp["entities"] = [G.make_node(e["type"], e["name"]) for e in entities]
        return _fallback(resp, question, ctx)
    entity = slot_checker.pick_entity(intent, entities)
    cypher, params = cypher_builder.build(intent, entity)  # ⑥
    if cypher is None:
        resp["entities"] = [G.make_node(entity["type"], entity["name"])]
        return _fallback(resp, question, ctx)
    try:
        rows = graph_query.query(cypher, params)  # ⑦
    except _UNAVAILABLE as exc:
        # 只有"图库连不上"才降级为兜底；模板写错等 Cypher 语法错误必须抛出，不能伪装成兜底
        log.warning("图数据库不可用，转兜底：%s", exc)
        rows = []
    built = answer_builder.build(intent, entity, rows)  # ⑧
    resp["answer_text"] = built["answer_text"]
    resp["entities"] = built["entities"]
    resp["subgraph"] = built["subgraph"]
    if built["empty"]:
        return _fallback(resp, question, ctx, keep_text=True)
    return resp


def answer(question, ctx=None):
    """唯一入口。question 已由接口层 / CLI 完成校验（非空、≤100 字、非纯符号）。"""
    ctx = dict(ctx or {})
    return _run(question.strip(), ctx)


def strip_meta(resp):
    """接口层返回前剥离 _meta（落库用）。"""
    meta = resp.pop("_meta", {}) or {}
    return resp, meta
