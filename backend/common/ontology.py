# -*- coding: utf-8 -*-
"""
本体常量（全项目唯一来源）—— 对应实施方案 V3 第四章 + 开发规范 1.1 / 2 / 4.3。

七类实体标签、十类关系、头尾约束、各类型属性（必填 / 派生）、枚举值域、中文名、色值、七个历史时期。
后端校验、动态表单、图谱着色、schema 生成、Cypher 白名单全部引用本文件；
前端镜像 frontend/src/utils/ontology.js 由 export_ontology.py 生成，禁止手改。

变更纪律：新增 / 变更标签、关系、约束、必填属性只改本文件，然后
  1) python -m backend.common.export_ontology  重新生成前端镜像
  2) 同步 kg/importer/schema.cypher 与 V3 第四章
"""

# ---------------------------------------------------------------------------
# 1. 实体标签（7 类）
# ---------------------------------------------------------------------------
LABELS = ["Person", "Organization", "Event", "Meeting", "Location", "Document", "Period"]

LABEL_ZH = {
    "Person": "人物",
    "Organization": "组织",
    "Event": "事件",
    "Meeting": "会议",
    "Location": "地点",
    "Document": "文献",
    "Period": "时期",
}

# 实体类型七色映射（开发规范 1.1，全站唯一来源）
LABEL_COLOR = {
    "Person": "#C0392B",
    "Organization": "#E67E22",
    "Event": "#2E86C1",
    "Meeting": "#8E44AD",
    "Location": "#27AE60",
    "Document": "#B7950B",
    "Period": "#7F8C8D",
}

# ---------------------------------------------------------------------------
# 2. 枚举值域
# ---------------------------------------------------------------------------
ENUMS = {
    "org_type": ["政党", "军队", "群团", "机构"],
    "doc_type": ["著作", "报告", "决议", "宣言", "章程"],
    "time_precision": ["day", "month", "year"],
}


def _p(name, zh, required=False, kind="text", enum=None, derived=False):
    """属性描述：kind 取 text / longtext / number / enum / time；derived=True 表示由后端派生、表单不渲染。"""
    d = {"name": name, "zh": zh, "required": required, "kind": kind, "derived": derived}
    if enum:
        d["enum"] = enum
    return d


# 各标签属性定义（V3 4.1 表）。time_sort / time_precision 由 kg/extract/timeparse.py 从 time_text 派生。
PROPS = {
    "Person": [
        _p("name", "姓名", True),
        _p("alias", "别名"),
        _p("birth_year", "出生年", kind="number"),
        _p("death_year", "逝世年", kind="number"),
        _p("birthplace", "籍贯"),
        _p("intro", "简介", True, "longtext"),
        _p("source", "来源", True),
    ],
    "Organization": [
        _p("name", "名称", True),
        _p("alias", "别名"),
        _p("found_time_text", "成立时间", kind="time"),
        _p("time_sort", "排序键", derived=True),
        _p("org_type", "组织类型", True, "enum", ENUMS["org_type"]),
        _p("intro", "简介", True, "longtext"),
        _p("source", "来源", True),
    ],
    "Event": [
        _p("name", "名称", True),
        _p("alias", "别名"),
        _p("time_text", "时间", True, "time"),
        _p("time_sort", "排序键", True, derived=True),
        _p("time_precision", "时间精度", True, "enum", ENUMS["time_precision"], derived=True),
        _p("content", "主要内容", kind="longtext"),
        _p("meaning", "历史意义", kind="longtext"),
        _p("intro", "简介", True, "longtext"),
        _p("source", "来源", True),
    ],
    "Meeting": [
        _p("name", "名称", True),
        _p("alias", "别名"),
        _p("time_text", "时间", True, "time"),
        _p("time_sort", "排序键", True, derived=True),
        _p("time_precision", "时间精度", True, "enum", ENUMS["time_precision"], derived=True),
        _p("content", "主要内容", kind="longtext"),
        _p("meaning", "历史意义", kind="longtext"),
        _p("intro", "简介", True, "longtext"),
        _p("source", "来源", True),
    ],
    "Location": [
        _p("name", "名称", True),
        _p("alias", "别名"),
        _p("modern_name", "今地名"),
        _p("source", "来源"),
    ],
    "Document": [
        _p("name", "名称", True),
        _p("alias", "别名"),
        _p("pub_time_text", "发表时间", kind="time"),
        _p("time_sort", "排序键", derived=True),
        _p("doc_type", "文献类型", kind="enum", enum=ENUMS["doc_type"]),
        _p("intro", "简介", kind="longtext"),
        _p("source", "来源", True),
    ],
    "Period": [
        _p("name", "名称", True),
        _p("start_year", "起始年", True, "number"),
        _p("end_year", "结束年", kind="number"),
        _p("order", "序号(1-7)", True, "number"),
    ],
}

# 系统维护属性（导入 / 后台写操作维护，不进表单）：checked 0/1 核心池标记；updated_at 最近更新时间
SYSTEM_PROPS = ["checked", "updated_at"]

# ---------------------------------------------------------------------------
# 3. 关系类型（10 类）与头尾约束（V3 4.2 表）
# ---------------------------------------------------------------------------
RELATIONS = [
    "LED", "PARTICIPATED_IN", "AUTHORED", "HELD_POSITION", "HELD_IN",
    "OCCURRED_IN", "PRODUCED", "FOUNDED", "REORGANIZED_TO", "BELONGS_TO",
]

RELATION_ZH = {
    "LED": "领导",
    "PARTICIPATED_IN": "参加",
    "AUTHORED": "创作",
    "HELD_POSITION": "任职",
    "HELD_IN": "召开于",
    "OCCURRED_IN": "发生于",
    "PRODUCED": "形成",
    "FOUNDED": "创建",
    "REORGANIZED_TO": "改编为",
    "BELONGS_TO": "属于时期",
}

# 关系 -> 允许的 (头标签, 尾标签) 组合
RELATION_CONSTRAINTS = {
    "LED": [("Person", "Event"), ("Organization", "Event")],
    "PARTICIPATED_IN": [("Person", "Meeting")],
    "AUTHORED": [("Person", "Document")],
    "HELD_POSITION": [("Person", "Organization")],
    "HELD_IN": [("Meeting", "Location")],
    "OCCURRED_IN": [("Event", "Location")],
    "PRODUCED": [("Meeting", "Document")],
    "FOUNDED": [("Meeting", "Organization"), ("Event", "Organization")],
    "REORGANIZED_TO": [("Organization", "Organization")],
    "BELONGS_TO": [("Event", "Period"), ("Meeting", "Period")],
}

# 关系属性：HELD_POSITION.position 必填；REORGANIZED_TO.time_text 可选
RELATION_PROPS = {
    "HELD_POSITION": [_p("position", "职务", True)],
    "REORGANIZED_TO": [_p("time_text", "改编时间", kind="time")],
}

# ---------------------------------------------------------------------------
# 4. 七个历史时期（V3 3.3；start_sort 为自动归属起点，边界年份条目人工校验时逐条确认）
# ---------------------------------------------------------------------------
PERIODS = [
    {"name": "建党初期与大革命时期", "order": 1, "start_year": 1921, "end_year": 1927, "start_sort": "19210701"},
    {"name": "土地革命战争时期", "order": 2, "start_year": 1927, "end_year": 1937, "start_sort": "19270801"},
    {"name": "全民族抗日战争时期", "order": 3, "start_year": 1937, "end_year": 1945, "start_sort": "19370707"},
    {"name": "解放战争时期", "order": 4, "start_year": 1945, "end_year": 1949, "start_sort": "19450903"},
    {"name": "社会主义革命和建设时期", "order": 5, "start_year": 1949, "end_year": 1978, "start_sort": "19491001"},
    {"name": "改革开放和社会主义现代化建设新时期", "order": 6, "start_year": 1978, "end_year": 2012, "start_sort": "19781218"},
    {"name": "中国特色社会主义新时代", "order": 7, "start_year": 2012, "end_year": None, "start_sort": "20121108"},
]
PERIOD_NAMES = [p["name"] for p in PERIODS]


# ---------------------------------------------------------------------------
# 5. 辅助函数（校验与白名单）
# ---------------------------------------------------------------------------
def is_label(label):
    return label in LABELS


def is_relation(rel):
    return rel in RELATIONS


def zh(label_or_rel):
    return LABEL_ZH.get(label_or_rel) or RELATION_ZH.get(label_or_rel) or label_or_rel


def color(label):
    return LABEL_COLOR.get(label, "#999999")


def props_of(label):
    return PROPS.get(label, [])


def form_props(label):
    """表单需渲染的属性（排除派生属性）。"""
    return [p for p in props_of(label) if not p["derived"]]


def required_props(label):
    return [p["name"] for p in props_of(label) if p["required"] and not p["derived"]]


def allowed_relations(head_label):
    """给定头实体类型，返回允许的关系类型列表（三元组表单二级联动）。"""
    return [r for r in RELATIONS if any(h == head_label for h, _ in RELATION_CONSTRAINTS[r])]


def allowed_tails(head_label, rel):
    """给定头类型与关系，返回允许的尾实体类型列表（三元组表单三级联动）。"""
    return [t for h, t in RELATION_CONSTRAINTS.get(rel, []) if h == head_label]


def is_allowed(head_label, rel, tail_label):
    return (head_label, tail_label) in RELATION_CONSTRAINTS.get(rel, [])


def as_export_dict():
    """供 export_ontology.py 生成前端镜像。"""
    return {
        "LABELS": LABELS,
        "LABEL_ZH": LABEL_ZH,
        "LABEL_COLOR": LABEL_COLOR,
        "PROPS": PROPS,
        "SYSTEM_PROPS": SYSTEM_PROPS,
        "RELATIONS": RELATIONS,
        "RELATION_ZH": RELATION_ZH,
        "RELATION_CONSTRAINTS": {r: [list(pair) for pair in pairs] for r, pairs in RELATION_CONSTRAINTS.items()},
        "RELATION_PROPS": RELATION_PROPS,
        "ENUMS": ENUMS,
        "PERIODS": PERIODS,
    }
