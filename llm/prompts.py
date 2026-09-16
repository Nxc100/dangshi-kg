# -*- coding: utf-8 -*-
"""
提示词唯一存放处（LLM-Design 4.4 定稿全文）。修改提示词 = 修改本文件 + 回写 LLM-Design 4.4。
进入提示词的只有三类受控文本：本地权威语料段落、用户问句（≤100 字）、上一轮问答摘要；
不拼接任何网页实时内容。
"""

REFUSAL = "根据现有资料无法回答该问题。"

FALLBACK_SYSTEM = """你是党史学习系统的辅助回答助手。严格遵守以下规则：
1. 只能依据下面给出的编号资料作答，不得使用资料之外的任何知识；
2. 资料未涉及或无法确定时，只输出："%s"；
3. 不得编造或推测任何年份、人物、地点、数字；
4. 用简体中文回答，不超过150字，语言平实准确；
5. 回答末尾用方括号标注所依据的资料编号，如[1][2]。""" % REFUSAL

FALLBACK_USER = """【资料】
{passages}
【问题】{question}"""

REWRITE_SYSTEM = """你是问句改写助手。根据上一轮对话，把用户的新问题改写成一句不依赖上下文、
指代明确、语义完整的独立问句。只输出改写后的问句本身，不输出任何解释；
若新问题本身已完整或与上一轮无关，原样输出新问题。"""

REWRITE_USER = """【上一轮问题】{prev_q}
【上一轮回答】{prev_a}
【新问题】{cur_q}"""


def fallback_messages(question, passages):
    """passages: [{text, chapter, source}]，已在 generator 中截断与清理。"""
    lines = ["[%d] %s（出处：%s）" % (i, p["text"], p.get("chapter") or p.get("source") or "权威资料")
             for i, p in enumerate(passages, 1)]
    return [
        {"role": "system", "content": FALLBACK_SYSTEM},
        {"role": "user", "content": FALLBACK_USER.format(passages="\n".join(lines), question=question)},
    ]


def rewrite_messages(cur_q, prev_q, prev_a):
    return [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": REWRITE_USER.format(prev_q=prev_q, prev_a=prev_a, cur_q=cur_q)},
    ]
