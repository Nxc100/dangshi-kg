# -*- coding: utf-8 -*-
"""
兜底受约束生成（FR-L02）：段落编号 + 注入清理 + 调 client + 调 checker。
任一环节失败（无 key / 超时 / 报错 / 校验不过）返回 text=None，由管道无感降级为原路径段落展示。
"""
import logging
import re
import time

from llm import checker, client, config, prompts

log = logging.getLogger(__name__)

PASSAGE_MAX_CHARS = 500
MAX_TOKENS = 300
ANSWER_MAX_CHARS = 150  # 提示词要求正文 ≤150 字；留一倍余量，超出即视为不合规走降级
ANSWER_HARD_LIMIT = ANSWER_MAX_CHARS * 2

# 提示注入清理：语料侧不可能出现，属防御性处理
_INJECT = re.compile(r"(忽略(以上|上述|前面).{0,10}(指令|要求|规则)|ignore\s+(the\s+)?(above|previous)|"
                     r"system\s*[:：]|assistant\s*[:：])", re.IGNORECASE)


def _clean(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = _INJECT.sub("", text)
    return text[:PASSAGE_MAX_CHARS]


def generate(question, passages):
    """
    返回 {text, cited, latency_ms, detail}。
    text 为 None 表示降级；latency_ms 含失败尝试耗时；detail 供 qa_log.llm_detail 审计留痕。
    """
    prepared = [{"text": _clean(p["text"]), "chapter": p.get("chapter", ""), "source": p.get("source", "")}
                for p in (passages or [])[:3]]
    detail = {"text": None, "cited": [], "check_passed": False, "degraded_reason": None,
              "passages": [{"idx": i, "text": p["text"], "chapter": p["chapter"], "source": p["source"]}
                           for i, p in enumerate(prepared, 1)]}
    if not prepared:
        detail["degraded_reason"] = "no_passage"
        return {"text": None, "cited": [], "latency_ms": None, "detail": detail}

    start = time.time()
    raw = client.chat(prompts.fallback_messages(question, prepared),
                      timeout=config.timeout(), max_tokens=MAX_TOKENS)
    latency = int((time.time() - start) * 1000)
    detail["text"] = raw
    if raw is None:
        detail["degraded_reason"] = "client_none"
        return {"text": None, "cited": [], "latency_ms": latency, "detail": detail}

    # 超长直接降级，不做事后截断：截断会切掉末尾的 [n] 引用，使上屏内容与 cited 不再一一对应
    if len(raw) > ANSWER_HARD_LIMIT:
        detail["degraded_reason"] = "too_long:%d" % len(raw)
        log.info("LLM 回答超出 %d 字，降级为段落展示", ANSWER_HARD_LIMIT)
        return {"text": None, "cited": [], "latency_ms": latency, "detail": detail}

    passed, reason, cited = checker.check(raw, prepared)
    detail["cited"], detail["check_passed"] = cited, passed
    if not passed:
        detail["degraded_reason"] = "check:%s" % reason
        log.info("LLM 忠实度校验未通过（%s），降级为段落展示", reason)
        return {"text": None, "cited": [], "latency_ms": latency, "detail": detail}

    return {"text": raw, "cited": cited, "latency_ms": latency, "detail": detail}
