# -*- coding: utf-8 -*-
"""
核心实体池汇总入口（V3 3.6，checked=1 的 500 实体由此处与 entities.py 共同构成）。

本模块只做汇总与字段口径声明，具体数据在四个分表里：
    core_persons.py   人物
    core_meetings.py  会议（含会议召开地）
    core_refs.py      地点 / 组织 / 文献
    core_promote.py   从 DR-13 自动池提升为核心池的事件与文献名单

「提升」的含义：自动池的事件名是权威编年条目的**整句原文**，时间、正文、来源 URL
均逐字来自留档，本身已满足「对照留档原文核对全部属性」的要求；人工要做的是判断
该条是否属于核心知识。故核心事件不重写一遍，只在 core_promote.py 中列出其主名，
由 db/build_seed.py 把这些行的 checked 置 1。这样做也保证核心事件与自动池同源，
不会出现两份互相矛盾的表述。

校验：eval/core_check.py 对全部 checked=1 实体做机械交叉复核（V3 3.6 交叉复核环节）。
"""
from db.seed_data.core_meetings import CORE_MEETINGS, MEETING_MEANING, MEETING_PLACES
from db.seed_data.core_persons import CORE_PERSONS
from db.seed_data.core_refs import CORE_DOCUMENTS, CORE_LOCATIONS, CORE_ORGANIZATIONS

# 核心池统一溯源：中央党史和文献研究院「党史百年·天天读」栏目及其留档条目
CORE_SOURCE = "https://www.dswxyjy.org.cn/GB/434461/index.html"

# 各表的列顺序。Meeting 的 place 不是本体属性，构建时弹出并转为 HELD_IN 关系
CORE_FIELDS = {
    "Person": ("name", "alias", "birth_year", "death_year", "birthplace", "intro"),
    "Meeting": ("name", "alias", "time_text", "place", "content", "intro"),
    "Location": ("name", "alias", "modern_name"),
    "Organization": ("name", "alias", "found_time_text", "org_type", "intro"),
    "Document": ("name", "alias", "pub_time_text", "doc_type", "intro"),
}

# V3 3.6 规定的核心池构成：人物 120、会议 60、事件 150、组织 40、文献 60、地点 63、时期 7
CORE_TARGET = {"Person": 120, "Meeting": 60, "Event": 150, "Organization": 40,
               "Document": 60, "Location": 63, "Period": 7}

CORE_ENTITIES = {
    "Person": CORE_PERSONS,
    "Meeting": CORE_MEETINGS,
    "Location": list(CORE_LOCATIONS) + list(MEETING_PLACES),
    "Organization": CORE_ORGANIZATIONS,
    "Document": CORE_DOCUMENTS,
}


def rows_of(label):
    """把某类核心记录展开为字典行；死亡年份 0 表示在世或不详，转为空值。"""
    fields = CORE_FIELDS[label]
    out = []
    for record in CORE_ENTITIES.get(label, []):
        row = dict(zip(fields, record))
        for key in ("birth_year", "death_year"):
            if not row.get(key):
                row.pop(key, None)
        if label == "Meeting" and row["name"] in MEETING_MEANING:
            row["meaning"] = MEETING_MEANING[row["name"]]
        row["source"] = CORE_SOURCE
        row["checked"] = 1
        out.append(row)
    return out


def held_in_relations():
    """会议 → 召开地：由 CORE_MEETINGS 的 place 列派生，place 为空的不产出。"""
    index = CORE_FIELDS["Meeting"].index("place")
    return [(record[0], "Meeting", "HELD_IN", record[index], "Location", "", "")
            for record in CORE_MEETINGS if record[index]]


def promoted():
    """从自动池提升为核心池的主名集合，按标签分组；名单文件缺失时按空处理。"""
    try:
        from db.seed_data.core_promote import PROMOTE
    except ImportError:
        return {}
    return {label: set(names) for label, names in PROMOTE.items()}
