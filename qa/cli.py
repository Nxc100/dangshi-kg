# -*- coding: utf-8 -*-
"""
命令行问答（中期检查材料）：python -m qa.cli
与 POST /api/qa 共用 qa.pipeline.answer()；启动时经 create_app() 加载词典 / TF-IDF / Neo4j driver。
输入 exit / quit / q 退出。
"""
import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.common.ontology import zh  # noqa: E402
from qa.intent_rules import INTENT_ZH  # noqa: E402


def render(resp):
    ents = "、".join("%s(%s)" % (e["name"], zh(e["type"])) for e in resp["entities"]) or "-"
    print("[意图] %s %s   [实体] %s   [来源] %s%s" % (
        resp["intent"], INTENT_ZH.get(resp["intent"], ""), ents, resp["answer_source"],
        "   [兜底]" if resp["fallback"] else ""))
    if resp.get("rewritten_from"):
        print("[改写] 已按「%s」查询（原问句：%s）" % (resp["question"], resp["rewritten_from"]))
    if resp["answer_text"]:
        print("答：%s" % resp["answer_text"])
    if resp.get("clarify"):
        for ex in resp["clarify"]["examples"]:
            print("   · %s" % ex)
    if resp.get("candidates"):
        print("你是不是想问：%s" % " / ".join(c["name"] for c in resp["candidates"]))
    if resp.get("llm"):
        print("AI 生成，仅供参考：%s" % resp["llm"]["text"])
    for i, p in enumerate(resp.get("fallback_passages") or [], 1):
        print("[%d] %s（出处：%s，相似度 %.3f）" % (i, p["text"][:120], p["chapter"] or p["source"], p["score"]))
    if resp["subgraph"]["links"]:
        print("[溯源] %d 节点 / %d 边" % (len(resp["subgraph"]["nodes"]), len(resp["subgraph"]["links"])))


def main(argv=None):
    from backend.app import create_app
    from backend.common.validators import validate_question
    from backend.common.errors import ApiError
    from qa import dictionary, fallback, pipeline

    app = create_app()
    with app.app_context():
        print("党史知识图谱问答（命令行版）  词典实体 %d 个 | 兜底语料 %d 段 | 输入 exit 退出"
              % (dictionary.get().size(), fallback.size()))
        args = list(argv if argv is not None else sys.argv[1:])
        if args:  # 非交互：python -m qa.cli "遵义会议在哪召开"
            resp, _ = pipeline.strip_meta(pipeline.answer(" ".join(args)))
            render(resp)
            if "--json" in args:
                print(json.dumps(resp, ensure_ascii=False, indent=2))
            return
        while True:
            try:
                q = input("问> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if q.lower() in ("exit", "quit", "q"):
                break
            if not q:
                continue
            try:
                q = validate_question(q)
            except ApiError as exc:
                print("提示：%s" % exc.msg)
                continue
            resp, _ = pipeline.strip_meta(pipeline.answer(q))
            render(resp)


if __name__ == "__main__":
    main()
