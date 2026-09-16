# -*- coding: utf-8 -*-
"""
② 词性标注：jieba.posseg 输出 词/词性 序列，并抽取疑问词（代词 r）与动词触发词特征，
供意图分类与论文对比实验（词 + 词性组合特征）使用。
"""
import jieba.posseg as pseg

QUESTION_WORDS = ("哪", "谁", "什么", "何", "几", "怎", "多少", "吗")
TRIGGER_VERBS = (
    "领导", "参加", "召开", "写", "发动", "指挥", "出席", "创作", "担任",
    "改编", "成立", "创建", "发生", "举行", "撰写", "通过", "任职", "介绍",
)


def tag(text):
    """返回 [(word, flag), ...]。"""
    return [(pair.word, pair.flag) for pair in pseg.cut(text or "")]


def features(pairs, text=""):
    """
    抽取特征：
      question_words —— 词性 r 且含疑问字，或文本中直接出现疑问字
      triggers       —— 词性 v 且属触发词表
      has_question   —— 是否为疑问句式（无疑问词仅实体 → I13 介绍卡）
    """
    question_words = [w for w, f in pairs if f.startswith("r") and any(c in w for c in QUESTION_WORDS)]
    if not question_words:
        question_words = [qw for qw in QUESTION_WORDS if qw in (text or "")]
    triggers = [w for w, f in pairs if f.startswith("v") and w in TRIGGER_VERBS]
    return {
        "question_words": question_words,
        "triggers": triggers,
        "has_question": bool(question_words),
    }
