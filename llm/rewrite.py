# -*- coding: utf-8 -*-
"""
追问改写（FR-L03）：触发判定 + 调 client + 安全校验。LLM 只产出问句，答案仍由图谱产出，零幻觉风险。

触发（满足其一，且携带 prev_q）：a. 第③步实体识别三级全未中；b. 问句命中指代词表且未识别出实体。
安全校验：非空 / ≤100 字 / 无换行；多句取第一句并去引号，仍不合规视为失败（按原句继续原流程）。
"""
import logging
import re

from llm import client, config, prompts

log = logging.getLogger(__name__)

PRONOUNS = ("它", "他", "她", "这", "那", "这次", "那次", "该会议", "该事件", "此人", "此次", "上述", "前面")
MAX_LEN = 100
PREV_A_MAX = 200
_SENT_END = re.compile(r"[。？！?!]")


def should_rewrite(question, entities):
    """触发条件（LLM-Design FR-L03）：a. 实体识别三级全未中；或 b. 命中指代词表且未识别出实体。
    两者都以"未识别出实体"为前提，故已识别出实体时一律不改写。"""
    if entities:
        return False
    return True


def has_pronoun(question):
    """问句是否命中指代词表（供日志与实验分析区分 a / b 两类触发）。"""
    return any(p in (question or "") for p in PRONOUNS)


def _sanitize(text):
    text = (text or "").strip().strip("\"'“”‘’《》")
    if not text or "\n" in text or "\r" in text:
        text = re.split(r"[\r\n]+", text or "")[0].strip()
    if not text:
        return None
    m = _SENT_END.search(text)  # 多句取第一句
    if m:
        text = text[:m.end()]
    text = text.strip().strip("\"'“”‘’")
    if not text or len(text) > MAX_LEN:
        return None
    return text


def rewrite(cur_q, prev_q, prev_a):
    """返回改写后的独立问句，或 None（失败按原句处理）。"""
    if not config.available() or not prev_q:
        return None
    raw = client.chat(
        prompts.rewrite_messages(cur_q, prev_q, (prev_a or "")[:PREV_A_MAX]),
        timeout=config.rewrite_timeout(), max_tokens=120,
    )
    if raw is None:
        return None
    result = _sanitize(raw)
    if result is None:
        log.info("追问改写结果不合规，按原问句处理")
    return result
