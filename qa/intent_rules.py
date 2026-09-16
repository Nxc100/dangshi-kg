# -*- coding: utf-8 -*-
"""
意图规则表（独立配置，改规则不改管道代码）—— V3 6.1 ④ 定稿 15 类意图 + UNKNOWN。

每条规则 = 关键词集（任一命中）∧ require_all（每组至少命中一个）∧ 实体类型（链接实体类型须相交）→ 意图。
优先级：I14 / I15（两跳）> I1–I12 > I13；同级按本表书写顺序取先。
规则表变更后必须复跑 900 条数据集的测试集（准确率 ≥ 90%），并回写 V3 6.1。
"""
from backend.common.ontology import LABELS

INTENT_ZH = {
    "I1": "问时间",
    "I2": "问地点",
    "I3": "问内容",
    "I4": "问意义",
    "I5": "问领导人",
    "I6": "问参会者",
    "I7": "问作者",
    "I8": "问作品",
    "I9": "问人物事迹",
    "I10": "时期事件列举",
    "I11": "组织沿革",
    "I12": "问职务",
    "I13": "实体介绍",
    "I14": "两跳：参会者的事迹",
    "I15": "两跳：作者的职务",
    "UNKNOWN": "未识别",
}

INTENTS = [k for k in INTENT_ZH if k != "UNKNOWN"]

# example：槽位不符时给出的"该实体支持的问法示例"（{name} 占位）
RULES = [
    # ---- 两跳（最高优先级）----
    {
        "intent": "I14",
        "keywords": ["参加", "出席", "参会"],
        "require_all": [["领导", "参与", "发动", "指挥"]],
        "entity_types": ["Meeting"],
        "example": "参加{name}的人领导过哪些事件？",
    },
    {
        "intent": "I15",
        "keywords": ["作者", "谁写"],
        "require_all": [["担任", "职务", "任职", "什么职"]],
        "entity_types": ["Document"],
        "example": "{name}的作者担任过什么职务？",
    },
    # ---- 单跳 / 属性 ----
    {
        "intent": "I1",
        "keywords": ["哪一年", "什么时候", "何时", "哪年", "什么时间", "哪一天", "哪天", "几年", "时间"],
        "entity_types": ["Meeting", "Event", "Organization", "Document"],
        "example": "{name}是什么时候召开的？",
    },
    {
        "intent": "I2",
        "keywords": ["在哪", "哪里", "何地", "地点", "哪儿", "什么地方", "召开地"],
        "entity_types": ["Meeting", "Event"],
        "example": "{name}在哪里召开？",
    },
    {
        "intent": "I3",
        "keywords": ["主要内容", "内容", "讲了什么", "决定了什么", "议程", "通过了什么"],
        "entity_types": ["Meeting", "Event"],
        "example": "{name}的主要内容是什么？",
    },
    {
        "intent": "I4",
        "keywords": ["意义", "影响", "作用", "重要性", "历史地位"],
        "entity_types": ["Meeting", "Event"],
        "example": "{name}有什么历史意义？",
    },
    {
        "intent": "I5",
        "keywords": ["谁领导", "领导人", "由谁发动", "谁发动", "谁指挥", "领导者", "发动者", "谁领导的", "领导的"],
        "entity_types": ["Event"],
        "example": "{name}是谁领导的？",
    },
    {
        "intent": "I6",
        "keywords": ["谁参加", "出席", "参加者", "参会", "哪些人参加", "与会", "参加了"],
        "entity_types": ["Meeting"],
        "example": "哪些人参加了{name}？",
    },
    {
        "intent": "I7",
        "keywords": ["谁写", "作者", "由谁撰写", "谁著", "谁的著作"],
        "entity_types": ["Document"],
        "example": "{name}的作者是谁？",
    },
    {
        "intent": "I8",
        "keywords": ["写了哪些", "著作", "作品", "写过", "撰写了", "有哪些文章", "哪些书"],
        "entity_types": ["Person"],
        "example": "{name}写了哪些著作？",
    },
    {
        "intent": "I9",
        "keywords": ["领导过哪些", "参与过哪些", "领导了哪些", "事迹", "领导过", "参与过", "做了什么", "领导了什么"],
        "entity_types": ["Person"],
        "example": "{name}领导过哪些事件？",
    },
    {
        "intent": "I10",
        "keywords": ["有哪些大事", "重大事件", "哪些事件", "大事", "发生了什么", "有哪些事"],
        "entity_types": ["Period"],
        "example": "{name}有哪些重大事件？",
    },
    {
        "intent": "I11",
        "keywords": ["改编", "前身", "发展为", "沿革", "由什么改编", "演变", "改编而来", "改编成"],
        "entity_types": ["Organization"],
        "example": "{name}的前身是什么？",
    },
    {
        "intent": "I12",
        "keywords": ["担任", "职务", "任职", "什么职", "官职", "任什么"],
        "entity_types": ["Person"],
        "example": "{name}担任过什么职务？",
    },
    # ---- 实体介绍（最低优先级；无疑问词仅实体时由分类器直接判 I13）----
    {
        "intent": "I13",
        "keywords": ["介绍", "是什么", "是谁", "简介", "什么是", "了解", "讲讲"],
        "entity_types": list(LABELS),
        "example": "介绍一下{name}",
    },
]

# 槽位校验：意图所需实体类型（取规则表定义）
INTENT_ENTITY_TYPES = {rule["intent"]: list(rule["entity_types"]) for rule in RULES}


def rules_for_type(label):
    """给定实体类型，返回其支持的问法示例（澄清提示用）。"""
    return [rule for rule in RULES if label in rule["entity_types"]]
