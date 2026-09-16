# -*- coding: utf-8 -*-
"""
种子关系数据（与 entities.py 配套的演示用最小数据集）。

覆盖本体全部 10 类关系；头尾类型组合须符合 backend/common/ontology.py 的
RELATION_CONSTRAINTS，build_seed.py 生成时会逐条校验，不合约束即报错。

BELONGS_TO（属于时期）不在此手填：由 kg/importer/import_all.py 按 time_sort
经 kg/extract/period_assign.py 自动归属，保证与时间三字段口径一致。

出题模板对答案唯一性有要求（见 backend/services/quiz_service.py）：
- 事件→领导人：一个事件有多位领导人时该题被弃用，故保留秋收起义、百团大战等
  单一领导人的事件，供 event_leader 模板出题；
- 文献→作者：每篇文献恰好一位作者。
"""

# (头实体, 头类型, 关系, 尾实体, 尾类型, 关系属性)
RELATION_FIELDS = ("head", "head_type", "rel", "tail", "tail_type", "position", "time_text")

RELATIONS = [
    # ---- LED 领导：Person→Event / Organization→Event ----
    ("毛泽东", "Person", "LED", "秋收起义", "Event", "", ""),
    ("毛泽东", "Person", "LED", "红军长征", "Event", "", ""),
    ("周恩来", "Person", "LED", "南昌起义", "Event", "", ""),
    ("贺龙", "Person", "LED", "南昌起义", "Event", "", ""),
    ("朱德", "Person", "LED", "南昌起义", "Event", "", ""),
    ("彭德怀", "Person", "LED", "百团大战", "Event", "", ""),
    ("朱德", "Person", "LED", "井冈山会师", "Event", "", ""),
    ("八路军", "Organization", "LED", "百团大战", "Event", "", ""),
    ("中国共产党", "Organization", "LED", "改革开放", "Event", "", ""),

    # ---- PARTICIPATED_IN 参加：Person→Meeting ----
    ("毛泽东", "Person", "PARTICIPATED_IN", "中国共产党第一次全国代表大会", "Meeting", "", ""),
    ("董必武", "Person", "PARTICIPATED_IN", "中国共产党第一次全国代表大会", "Meeting", "", ""),
    ("李达", "Person", "PARTICIPATED_IN", "中国共产党第一次全国代表大会", "Meeting", "", ""),
    ("毛泽东", "Person", "PARTICIPATED_IN", "八七会议", "Meeting", "", ""),
    ("毛泽东", "Person", "PARTICIPATED_IN", "古田会议", "Meeting", "", ""),
    ("朱德", "Person", "PARTICIPATED_IN", "古田会议", "Meeting", "", ""),
    ("毛泽东", "Person", "PARTICIPATED_IN", "遵义会议", "Meeting", "", ""),
    ("周恩来", "Person", "PARTICIPATED_IN", "遵义会议", "Meeting", "", ""),
    ("朱德", "Person", "PARTICIPATED_IN", "遵义会议", "Meeting", "", ""),
    ("刘少奇", "Person", "PARTICIPATED_IN", "遵义会议", "Meeting", "", ""),
    ("毛泽东", "Person", "PARTICIPATED_IN", "中国共产党第七次全国代表大会", "Meeting", "", ""),
    ("周恩来", "Person", "PARTICIPATED_IN", "中国共产党第七次全国代表大会", "Meeting", "", ""),
    ("朱德", "Person", "PARTICIPATED_IN", "中国共产党第七次全国代表大会", "Meeting", "", ""),
    ("刘少奇", "Person", "PARTICIPATED_IN", "中国共产党第七次全国代表大会", "Meeting", "", ""),
    ("邓小平", "Person", "PARTICIPATED_IN", "中国共产党第十一届中央委员会第三次全体会议", "Meeting", "", ""),

    # ---- AUTHORED 创作：Person→Document（每篇恰好一位作者）----
    ("毛泽东", "Person", "AUTHORED", "论持久战", "Document", "", ""),
    ("毛泽东", "Person", "AUTHORED", "中国社会各阶级的分析", "Document", "", ""),
    ("毛泽东", "Person", "AUTHORED", "星星之火，可以燎原", "Document", "", ""),
    ("毛泽东", "Person", "AUTHORED", "实践论", "Document", "", ""),
    ("毛泽东", "Person", "AUTHORED", "矛盾论", "Document", "", ""),
    ("毛泽东", "Person", "AUTHORED", "论联合政府", "Document", "", ""),

    # ---- HELD_POSITION 任职：Person→Organization（position 必填）----
    ("毛泽东", "Person", "HELD_POSITION", "中国共产党", "Organization", "中央委员会主席", ""),
    ("陈独秀", "Person", "HELD_POSITION", "中国共产党", "Organization", "中央局书记", ""),
    ("朱德", "Person", "HELD_POSITION", "中国工农红军", "Organization", "总司令", ""),
    ("朱德", "Person", "HELD_POSITION", "八路军", "Organization", "总指挥", ""),
    ("彭德怀", "Person", "HELD_POSITION", "八路军", "Organization", "副总指挥", ""),
    ("陈毅", "Person", "HELD_POSITION", "新四军", "Organization", "代理军长", ""),
    ("朱德", "Person", "HELD_POSITION", "中国人民解放军", "Organization", "总司令", ""),

    # ---- HELD_IN 召开于：Meeting→Location ----
    ("中国共产党第一次全国代表大会", "Meeting", "HELD_IN", "上海", "Location", "", ""),
    ("八七会议", "Meeting", "HELD_IN", "汉口", "Location", "", ""),
    ("古田会议", "Meeting", "HELD_IN", "古田", "Location", "", ""),
    ("遵义会议", "Meeting", "HELD_IN", "遵义", "Location", "", ""),
    ("瓦窑堡会议", "Meeting", "HELD_IN", "瓦窑堡", "Location", "", ""),
    ("洛川会议", "Meeting", "HELD_IN", "洛川", "Location", "", ""),
    ("中国共产党第七次全国代表大会", "Meeting", "HELD_IN", "延安", "Location", "", ""),
    ("中国共产党第十一届中央委员会第三次全体会议", "Meeting", "HELD_IN", "北京", "Location", "", ""),
    ("中国社会主义青年团第一次全国代表大会", "Meeting", "HELD_IN", "广州", "Location", "", ""),

    # ---- OCCURRED_IN 发生于：Event→Location ----
    ("五四运动", "Event", "OCCURRED_IN", "北京", "Location", "", ""),
    ("南昌起义", "Event", "OCCURRED_IN", "南昌", "Location", "", ""),
    ("井冈山会师", "Event", "OCCURRED_IN", "井冈山", "Location", "", ""),
    ("西安事变", "Event", "OCCURRED_IN", "西安", "Location", "", ""),
    ("卢沟桥事变", "Event", "OCCURRED_IN", "北京", "Location", "", ""),
    ("开国大典", "Event", "OCCURRED_IN", "北京", "Location", "", ""),

    # ---- PRODUCED 形成：Meeting→Document ----
    ("中国共产党第一次全国代表大会", "Meeting", "PRODUCED", "中国共产党第一个纲领", "Document", "", ""),
    ("中国共产党第七次全国代表大会", "Meeting", "PRODUCED", "论联合政府", "Document", "", ""),

    # ---- FOUNDED 创建：Meeting→Organization / Event→Organization ----
    ("中国共产党第一次全国代表大会", "Meeting", "FOUNDED", "中国共产党", "Organization", "", ""),
    ("中国社会主义青年团第一次全国代表大会", "Meeting", "FOUNDED", "中国共产主义青年团", "Organization", "", ""),
    ("井冈山会师", "Event", "FOUNDED", "中国工农红军", "Organization", "", ""),

    # ---- REORGANIZED_TO 改编为：Organization→Organization ----
    ("中国工农红军", "Organization", "REORGANIZED_TO", "八路军", "Organization", "", "1937年8月"),
    ("八路军", "Organization", "REORGANIZED_TO", "中国人民解放军", "Organization", "", "1946年"),
    ("新四军", "Organization", "REORGANIZED_TO", "中国人民解放军", "Organization", "", "1946年"),
]
