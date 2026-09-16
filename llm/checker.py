# -*- coding: utf-8 -*-
"""
忠实度后校验（LLM-Design 4.5，程序化闸门）——把"提示词约束"升级为"可验证约束"。

三项检查，任一不过整体降级：
  ① 年份校验：文本中所有"三或四位数字 + 年"与日期字符串逐一须出现在所引段落原文；
  ② 实体校验：用实体词典（含别名）匹配到的每个实体名须出现在所引段落；
  ③ 引用校验：末尾至少含一个 [n]，n ∈ 1–3 且对应段落存在。
固定拒答句免于 ①② 直接放行。
"""
import re

from llm.prompts import REFUSAL

_YEAR = re.compile(r"\d{3,4}\s*年")
_MONTH_DAY = re.compile(r"\d{1,2}\s*[月日]")
_CITE = re.compile(r"\[(\d)\]")


def _norm(text):
    return re.sub(r"\s+", "", text or "")


def extract_citations(text):
    """返回文本中出现的引用编号列表（去重保序）。"""
    out = []
    for n in _CITE.findall(text or ""):
        idx = int(n)
        if idx not in out:
            out.append(idx)
    return out


def check(text, passages):
    """返回 (passed: bool, reason: str|None, cited: list[int])。"""
    text = (text or "").strip()
    if not text:
        return False, "empty", []
    cited = extract_citations(text)

    if _norm(text) == _norm(REFUSAL):  # 固定拒答句免检放行
        return True, None, cited

    # ③ 引用校验
    valid = [n for n in cited if 1 <= n <= len(passages)]
    if not valid:
        return False, "citation", cited
    corpus = _norm("".join(passages[n - 1]["text"] for n in valid))

    # ① 年份 / 日期校验
    for token in _YEAR.findall(text) + _MONTH_DAY.findall(text):
        if _norm(token) not in corpus:
            return False, "year:%s" % token, cited

    # ② 实体校验
    try:
        from qa import dictionary
        d = dictionary.get()
        for term in d.terms():
            if len(term) >= 2 and term in text and term not in corpus:
                hit = d.lookup(term)
                main = hit[0] if hit else term
                if main not in corpus:
                    return False, "entity:%s" % term, cited
    except Exception:  # noqa: BLE001 —— 词典不可用时不阻断（①③ 仍然生效）
        pass

    return True, None, valid
