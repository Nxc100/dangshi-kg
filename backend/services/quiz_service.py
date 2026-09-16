# -*- coding: utf-8 -*-
"""
知识测验出题与判分（F7 / FR-G06 / FR-U06，开发规范 6.6）—— 唯一实现，游客试做与登录用户共用。

六模板（与 V3 7.7 一一对应），只从 checked=1 核心池取三元组：
  会议→时间 / 会议→地点 / 事件→领导人 / 文献→作者 / 事件→时期 / 组织→沿革或创建
算法：随机选模板 → 核心池随机取三元组 → 答案唯一性校验（正确答案计数 = 1）→ 同类型实体抽 3 个干扰项
（排除正确答案及其全部别名，别名取自 dictionary）→ 选项洗牌；模板不足自动切换；单卷尝试上限 60 次。
提交时后端以 answer_key 复算得分，不信任前端上报。
"""
import json
import random

from backend.common.errors import BadRequest, NotFound, ServiceError
from backend.common.response import page_data
from backend.extensions import db_session, run_read
from backend.models import QuizRecord
from qa import dictionary

MAX_ATTEMPTS = 60
OPTION_KEYS = ("A", "B", "C", "D")

# 模板定义：三元组查询（返回 subject / answer）、答案唯一性校验、干扰项来源标签、题干与解析模板
TEMPLATES = {
    "meeting_time": {
        "cypher": ("MATCH (m:Meeting) WHERE m.checked = 1 AND m.time_text IS NOT NULL "
                   "RETURN m.name AS subject, m.time_text AS answer"),
        "unique": ("MATCH (m:Meeting {name:$subject}) WHERE m.time_text IS NOT NULL RETURN count(m) AS c"),
        "distractor": ("MATCH (m:Meeting) WHERE m.checked = 1 AND m.time_text IS NOT NULL AND m.name <> $subject "
                       "RETURN DISTINCT m.time_text AS text"),
        "question": "{subject}召开于____",
        "explanation": "{subject}召开于{answer}。",
        "entity_type": "Meeting",
    },
    "meeting_place": {
        "cypher": ("MATCH (m:Meeting)-[:HELD_IN]->(l:Location) WHERE m.checked = 1 "
                   "RETURN m.name AS subject, l.name AS answer"),
        "unique": ("MATCH (m:Meeting {name:$subject})-[:HELD_IN]->(l:Location) RETURN count(DISTINCT l) AS c"),
        "distractor": ("MATCH (l:Location) WHERE l.checked = 1 AND l.name <> $answer RETURN DISTINCT l.name AS text"),
        "question": "{subject}的召开地是____",
        "explanation": "{subject}的召开地是{answer}。",
        "entity_type": "Meeting",
    },
    "event_leader": {
        "cypher": ("MATCH (p:Person)-[:LED]->(e:Event) WHERE e.checked = 1 AND p.checked = 1 "
                   "RETURN e.name AS subject, p.name AS answer"),
        "unique": ("MATCH (p:Person)-[:LED]->(e:Event {name:$subject}) RETURN count(DISTINCT p) AS c"),
        "distractor": ("MATCH (p:Person) WHERE p.checked = 1 AND p.name <> $answer RETURN DISTINCT p.name AS text"),
        "question": "____领导了{subject}",
        "explanation": "{answer}领导了{subject}。",
        "entity_type": "Event",
    },
    "document_author": {
        "cypher": ("MATCH (p:Person)-[:AUTHORED]->(d:Document) WHERE d.checked = 1 AND p.checked = 1 "
                   "RETURN d.name AS subject, p.name AS answer"),
        "unique": ("MATCH (p:Person)-[:AUTHORED]->(d:Document {name:$subject}) RETURN count(DISTINCT p) AS c"),
        "distractor": ("MATCH (p:Person) WHERE p.checked = 1 AND p.name <> $answer RETURN DISTINCT p.name AS text"),
        "question": "{subject}的作者是____",
        "explanation": "{subject}的作者是{answer}。",
        "entity_type": "Document",
    },
    "event_period": {
        "cypher": ("MATCH (e:Event)-[:BELONGS_TO]->(t:Period) WHERE e.checked = 1 "
                   "RETURN e.name AS subject, t.name AS answer"),
        "unique": ("MATCH (e:Event {name:$subject})-[:BELONGS_TO]->(t:Period) RETURN count(DISTINCT t) AS c"),
        "distractor": ("MATCH (t:Period) WHERE t.name <> $answer RETURN DISTINCT t.name AS text"),
        "question": "{subject}发生于____",
        "explanation": "{subject}发生于{answer}。",
        "entity_type": "Event",
    },
    "org_reorganize": {
        "cypher": ("MATCH (a:Organization)-[:REORGANIZED_TO]->(b:Organization) "
                   "WHERE a.checked = 1 AND b.checked = 1 RETURN b.name AS subject, a.name AS answer"),
        "unique": ("MATCH (a:Organization)-[:REORGANIZED_TO]->(b:Organization {name:$subject}) "
                   "RETURN count(DISTINCT a) AS c"),
        "distractor": ("MATCH (o:Organization) WHERE o.checked = 1 AND o.name <> $answer "
                       "RETURN DISTINCT o.name AS text"),
        "question": "{subject}由____改编而来",
        "explanation": "{subject}由{answer}改编而来。",
        "entity_type": "Organization",
    },
}


def _excluded(answer):
    """正确答案及其全部别名（干扰项排除口径）。"""
    d = dictionary.get()
    hit = d.lookup(answer)
    name = hit[0] if hit else answer
    return {answer, name} | set(d.aliases_of(name))


def _make_question(key, row, rng):
    tpl = TEMPLATES[key]
    subject, answer = row["subject"], row["answer"]
    unique = run_read(tpl["unique"], subject=subject)
    if not unique or int(unique[0]["c"]) != 1:  # 答案唯一性校验
        return None
    excluded = _excluded(answer)
    pool = [r["text"] for r in run_read(tpl["distractor"], subject=subject, answer=answer)
            if r["text"] and r["text"] not in excluded]
    if len(pool) < 3:
        return None
    options = rng.sample(pool, 3) + [answer]
    rng.shuffle(options)
    answer_key = OPTION_KEYS[options.index(answer)]
    return {
        "question": tpl["question"].format(subject=subject, answer=answer),
        "options": [{"key": OPTION_KEYS[i], "text": text} for i, text in enumerate(options)],
        "answer_key": answer_key,
        "explanation": tpl["explanation"].format(subject=subject, answer=answer),
        "entity": {"name": subject, "type": tpl["entity_type"]},
        "template": key,
    }


def generate(n=5, entities=None, rng=None):
    """一次返回整卷；entities 非空时优先以这些实体出题，不足 n 题自动补随机题。"""
    rng = rng or random.Random()
    cache = {}
    for key, tpl in TEMPLATES.items():
        rows = run_read(tpl["cypher"])
        if rows:
            rng.shuffle(rows)
            cache[key] = rows
    if not cache:
        raise ServiceError("题库暂不可用：核心池（checked=1）中尚无可出题的三元组")

    wanted = set(entities or [])
    questions, used, attempts = [], set(), 0
    priority = [(k, [r for r in rows if r["subject"] in wanted]) for k, rows in cache.items()] if wanted else []

    while len(questions) < n and attempts < MAX_ATTEMPTS:
        attempts += 1
        row = key = None
        for k, rows in priority:  # 先用错题实体出题
            while rows:
                cand = rows.pop()
                if (k, cand["subject"]) not in used:
                    key, row = k, cand
                    break
            if row:
                break
        if row is None:
            key = rng.choice(list(cache.keys()))
            rows = cache[key]
            while rows:
                cand = rows.pop()
                if (key, cand["subject"]) not in used:
                    row = cand
                    break
            if row is None:
                cache.pop(key, None)
                if not cache:
                    break
                continue
        used.add((key, row["subject"]))
        q = _make_question(key, row, rng)
        if q:
            q["id"] = len(questions) + 1
            questions.append(q)

    if len(questions) < n:
        # 六模板都凑不满整卷时明确报错，不静默少发（前端按 5 / 10 题渲染，题数不符会误导用户）
        raise ServiceError("核心池数据不足，当前仅能生成 %d 题（需要 %d 题）：请先补充 checked=1 的三元组"
                           % (len(questions), n))
    return {"questions": questions, "total": len(questions)}


def submit(user_id, questions, answers, duration_sec=0):
    """后端以 answer_key 复算得分，不信任前端上报的 score。"""
    if not isinstance(questions, list) or not questions:
        raise BadRequest("试卷数据不完整", errors={"questions": "试卷不能为空"})
    answers = answers if isinstance(answers, list) else []
    if len(answers) != len(questions):
        raise BadRequest("作答数与题数不一致", errors={"answers": "作答数必须与题数一致"})

    detail, score = [], 0
    for q, chosen in zip(questions, answers):
        correct = str(chosen) == str(q.get("answer_key"))
        score += 1 if correct else 0
        detail.append({
            "question": q.get("question"), "options": q.get("options"), "answer_key": q.get("answer_key"),
            "chosen": chosen, "correct": correct, "entity": q.get("entity"),
            "template": q.get("template"), "explanation": q.get("explanation"),
        })
    record = QuizRecord(
        user_id=user_id, score=score, total=len(questions),
        detail_json=json.dumps({"questions": detail, "duration_sec": int(duration_sec or 0)}, ensure_ascii=False),
    )
    db_session.add(record)
    db_session.commit()
    return {"record_id": record.id, "score": score, "total": len(questions)}


def list_records(user_id, page, size):
    """本人测验记录，倒序分页（FR-U06）。"""
    q = db_session.query(QuizRecord).filter_by(user_id=user_id).order_by(QuizRecord.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    return page_data([r.to_dict() for r in rows], page, size, total)


def record_detail(user_id, record_id):
    """测验记录详情：逐题回顾，错题供前端标红与百科复习（FR-U06）。"""
    row = db_session.query(QuizRecord).filter_by(id=record_id, user_id=user_id).first()
    if row is None:
        raise NotFound("记录不存在")
    data = row.to_dict()
    try:
        data["detail"] = json.loads(row.detail_json)
    except (TypeError, ValueError):
        data["detail"] = {"questions": [], "duration_sec": 0}
    return data
