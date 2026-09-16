# -*- coding: utf-8 -*-
"""
③ 命名实体识别与链接（基于领域词典）—— 三级策略逐级降级（V3 6.1 ③）：
  1. 精确匹配：最长匹配优先扫描 + 分词结果（及相邻 token 拼接）查词典（主名 + 别名，别名回链主名）
  2. 模糊纠错：问句子串与词典词条 rapidfuzz ratio ≥ 85 取最高（"尊义会议 → 遵义会议"）
  3. 同音纠错：问句子串与词条拼音精确比对
三级全未中 → 返回 []，由管道给出 candidates（Top3 相似候选）并转兜底。
"""
from rapidfuzz import fuzz, process

from qa import dictionary

FUZZY_CUTOFF = 85
SUGGEST_CUTOFF = 50
MAX_WINDOW = 16


def _entity(name, label, method, matched):
    return {"name": name, "type": label, "method": method, "matched": matched}


def _scan_longest(question, d):
    """
    最长匹配优先的词典扫描（maximal munch）：从每个起点由长到短试子串，
    命中即吃掉该跨度，被更长命中包含的短词条不再单独成实体。

    没有这一遍，超过 4 个 token 的词条（图谱里两千多个整句式事件名）永远拼不出来，
    只会链到嵌在其中的短实体——问「毛泽东作《改造我们的学习》报告的举办城市」
    会链成「毛泽东」，再按人物提问被拒。
    """
    lengths = [n for n in d.term_lengths() if n >= 2]
    if not lengths:
        return [], set()
    longest = min(max(lengths), len(question))
    found, covered, start = {}, set(), 0
    while start < len(question):
        for size in range(min(longest, len(question) - start), 1, -1):
            span = question[start:start + size]
            hit = d.lookup(span)
            if hit:
                found.setdefault(hit[0], _entity(hit[0], hit[1], "exact", span))
                covered.update(range(start, start + size))
                start += size
                break
        else:
            start += 1
    return list(found.values()), covered


def _exact(tokens, d, question=""):
    """先做最长匹配扫描，再用分词结果补未被覆盖的短实体。"""
    scanned, covered = _scan_longest(question, d) if question else ([], set())
    found = {item["name"]: item for item in scanned}
    candidates = list(tokens)
    for k in (2, 3, 4):
        candidates.extend("".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1))
    for term in candidates:
        hit = d.lookup(term)
        if not hit or hit[0] in found:
            continue
        # 已被更长命中覆盖的跨度不再产出短实体（它是长名的一部分，不是另一个被问实体）
        at = question.find(term) if question else -1
        if at >= 0 and any(pos in covered for pos in range(at, at + len(term))):
            continue
        found[hit[0]] = _entity(hit[0], hit[1], "exact", term)
    return list(found.values())


def _windows(question, length):
    return [question[i:i + length] for i in range(len(question) - length + 1)]


def _fuzzy(question, d):
    best = None
    for length in d.term_lengths():
        if length < 2 or length > MAX_WINDOW or length > len(question):
            continue
        pool = d.terms_by_len(length - 1) + d.terms_by_len(length) + d.terms_by_len(length + 1)
        if not pool:
            continue
        for sub in _windows(question, length):
            hit = process.extractOne(sub, pool, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
            if hit and (best is None or hit[1] > best[1]):
                best = (hit[0], hit[1], sub)
    if best is None:
        return []
    name, label = d.lookup(best[0])
    return [_entity(name, label, "fuzzy", best[2])]


def _pinyin(question, d):
    index = d.pinyin_index()
    for length in d.term_lengths():
        if length < 2 or length > MAX_WINDOW or length > len(question):
            continue
        for sub in _windows(question, length):
            terms = index.get(dictionary.to_pinyin(sub))
            if terms:
                name, label = d.lookup(terms[0])
                return [_entity(name, label, "pinyin", sub)]
    return []


def link(question, tokens):
    """返回 [{name, type, method, matched}]；method ∈ exact / fuzzy / pinyin。"""
    d = dictionary.get()
    if not d.terms():
        return []
    for stage in (lambda: _exact(tokens, d, question), lambda: _fuzzy(question, d),
                  lambda: _pinyin(question, d)):
        result = stage()
        if result:
            return result
    return []


def suggest(question, k=3):
    """三级未中时的"你是不是想问"候选：partial_ratio Top-k（可为空）。"""
    d = dictionary.get()
    if not d.terms():
        return []
    hits = process.extract(question, d.terms(), scorer=fuzz.partial_ratio, limit=k * 3)
    out, seen = [], set()
    for term, score, _idx in hits:
        if score < SUGGEST_CUTOFF:
            continue
        name, label = d.lookup(term)
        if name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "type": label})
        if len(out) >= k:
            break
    return out
