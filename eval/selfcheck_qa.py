# -*- coding: utf-8 -*-
"""
问答管道离线自检（开发规范 3 节回归清单第 2–3 条、9.1 核心实验的前置回归）。

不依赖 Neo4j 与 Flask：用合成实体词典驱动 ①~⑧ 步，校验
  15 类意图分类、实体链接三级降级、槽位澄清、Cypher 参数化与注入防护、答案模板与列表截断。
图谱导入完成后，正式评测（200 条端到端 / 900 条意图数据集）另行编写并置于本目录。

用法（项目根目录）：python -m eval.selfcheck_qa
退出码 0 表示全部通过，非 0 表示有用例失败。
"""
import io
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from backend.services import graph_service as G  # noqa: E402
from qa import (answer_builder, cypher_builder, dictionary, entity_linker,  # noqa: E402
                intent_classifier, pos_tagger, slot_checker, tokenizer)

# 合成词典：覆盖七类标签与别名，模拟图谱已导入的最小样本
FIXTURES = [
    ("遵义会议", "Meeting", ""),
    ("中国共产党第一次全国代表大会", "Meeting", "一大/中共一大/党的一大"),
    ("秋收起义", "Event", "湘赣边界秋收起义"),
    ("毛泽东", "Person", "毛主席/润之"),
    ("论持久战", "Document", "《论持久战》"),
    ("八路军", "Organization", "十八集团军"),
    ("遵义", "Location", ""),
    ("土地革命战争时期", "Period", ""),
]

# (问句, 期望意图, 期望链接实体, 期望匹配方式或 None)
CASES = [
    ("遵义会议是什么时候召开的", "I1", "遵义会议", "exact"),
    ("遵义会议在哪里召开", "I2", "遵义会议", "exact"),
    ("遵义会议的主要内容是什么", "I3", "遵义会议", "exact"),
    ("遵义会议有什么历史意义", "I4", "遵义会议", "exact"),
    ("秋收起义是谁领导的", "I5", "秋收起义", "exact"),
    ("哪些人参加了中共一大", "I6", "中国共产党第一次全国代表大会", "exact"),
    ("《论持久战》的作者是谁", "I7", "论持久战", "exact"),
    ("毛泽东写了哪些著作", "I8", "毛泽东", "exact"),
    ("毛泽东领导过哪些事件", "I9", "毛泽东", "exact"),
    ("土地革命战争时期有哪些重大事件", "I10", "土地革命战争时期", "exact"),
    ("八路军由什么改编而来", "I11", "八路军", "exact"),
    ("毛泽东担任过什么职务", "I12", "毛泽东", "exact"),
    ("介绍一下遵义会议", "I13", "遵义会议", "exact"),
    ("遵义会议", "I13", "遵义会议", "exact"),
    # 两跳优先级：I14 / I15 高于单跳（V3 6.1 冲突裁决）
    ("参加遵义会议的人领导过哪些事件", "I14", "遵义会议", None),
    ("《论持久战》的作者担任过什么职务", "I15", "论持久战", None),
    # 实体链接三级降级：别名回链、模糊纠错
    ("毛主席写了哪些著作", "I8", "毛泽东", "exact"),
    ("一大在哪里召开", "I2", "中国共产党第一次全国代表大会", "exact"),
    ("尊义会议在哪里召开", "I2", "遵义会议", "fuzzy"),
]

INJECTION = "遵义会议'}) DETACH DELETE (n) //"


class Checker:
    def __init__(self):
        self.passed = self.failed = 0

    def check(self, title, condition, detail=""):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        print("[%s] %-44s %s" % ("PASS" if condition else "FAIL", title, detail))
        return condition


def build_dictionary():
    """构建合成词典并生成 jieba 自定义词典（覆盖模块级单例，仅本进程有效）。"""
    d = dictionary.EntityDict()
    for name, label, alias in FIXTURES:
        d.add_entity(name, label, alias)
    d.finalize()
    dictionary._current = d
    dictionary.write_userdict(d)
    tokenizer.load_userdict()
    return d


def understand(question):
    """执行 ①分词 ②词性标注 ③实体链接 ④意图分类，返回 (实体列表, 意图)。"""
    tokens = tokenizer.cut(question)
    feats = pos_tagger.features(pos_tagger.tag(question), question)
    entities = entity_linker.link(question, tokens)
    return entities, intent_classifier.classify(question, feats, entities)


def check_understanding(c):
    print("一、问句理解：15 类意图 + 实体链接三级降级")
    for question, want_intent, want_name, want_method in CASES:
        entities, intent = understand(question)
        name = entities[0]["name"] if entities else None
        method = entities[0]["method"] if entities else None
        hit = intent == want_intent and name == want_name and (want_method is None or method == want_method)
        c.check(question, hit, "意图 %s / 实体 %s / 方式 %s" % (intent, name, method))


def check_slot(c):
    print("\n二、槽位校验：类型不符应澄清而非查询（规范 9.2）")
    entities, intent = understand("谁参加了毛泽东")
    clarify = slot_checker.check(intent, entities)
    c.check("「谁参加了毛泽东」返回澄清与问法示例",
            bool(clarify and clarify.get("examples")),
            (clarify or {}).get("text", ""))


def check_cypher(c):
    print("\n三、查询构建：15 模板参数化，注入样例不进入 Cypher 文本（规范 6.3）")
    from qa.intent_rules import INTENT_ENTITY_TYPES

    missing = []
    for intent, types in INTENT_ENTITY_TYPES.items():
        cypher, params = cypher_builder.build(intent, {"name": "样本", "type": types[0]})
        if cypher is None or "$name" not in cypher or params.get("name") != "样本":
            missing.append(intent)
    c.check("15 类意图均有参数化模板", not missing, "缺失：%s" % (missing or "无"))

    cypher, params = cypher_builder.build("I1", {"name": INJECTION, "type": "Meeting"})
    c.check("注入样例仅作为 $name 参数传入",
            "DETACH DELETE" not in cypher and params["name"] == INJECTION)


def check_answers(c):
    print("\n四、答案生成：中文模板 + 溯源子图 + 列表 ≤10 项（V3 6.3）")
    r = answer_builder.build("I1", {"name": "遵义会议", "type": "Meeting"},
                             [{"name": "遵义会议", "value": "1935年1月15日至17日"}])
    c.check("I1 属性模板", r["answer_text"] == "遵义会议召开于1935年1月15日至17日。", r["answer_text"])

    r = answer_builder.build("I5", {"name": "秋收起义", "type": "Event"},
                             [{"name": "秋收起义", "other": "毛泽东", "other_type": "Person", "rprops": {}}])
    link = r["subgraph"]["links"][0] if r["subgraph"]["links"] else {}
    c.check("I5 溯源子图方向与中文关系名",
            link.get("source") == G.node_id("Person", "毛泽东") and link.get("label") == "领导",
            str(link))

    rows = [{"name": "中共一大", "other": "代表%02d" % i, "other_type": "Person", "rprops": {}}
            for i in range(1, 13)]
    r = answer_builder.build("I6", {"name": "中共一大", "type": "Meeting"}, rows)
    c.check("列表超 10 项显示前 10 并注明总数", "共 12 项" in r["answer_text"], r["answer_text"][-28:])

    r = answer_builder.build("I3", {"name": "遵义会议", "type": "Meeting"},
                             [{"name": "遵义会议", "value": None}])
    c.check("属性为空返回「该信息暂未收录」并标记 empty",
            r["empty"] and r["answer_text"] == answer_builder.MISSING_TEXT)


def check_search(c):
    print("\n五、搜索联想：别名命中回链主名（规范 6.5）")
    hits = [x["name"] for x in G.search("一大")]
    c.check("别名「一大」回链主名", "中国共产党第一次全国代表大会" in hits, str(hits))


def main():
    build_dictionary()
    c = Checker()
    print("=" * 96)
    check_understanding(c)
    check_slot(c)
    check_cypher(c)
    check_answers(c)
    check_search(c)
    print("=" * 96)
    print("汇总：PASS %d / FAIL %d" % (c.passed, c.failed))
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
