# -*- coding: utf-8 -*-
"""
时期归属唯一实现（V3 3.3 / 开发规范 7.3）：time_sort → 七个历史时期之一。
采集清洗、导入脚本与后台新增事件 / 会议共用；边界年份条目在人工校验时逐条确认。
"""
from backend.common.ontology import PERIODS

_ORDERED = sorted(PERIODS, key=lambda p: p["start_sort"])


def assign(time_sort):
    """返回时期名；time_sort 不合法或早于建党返回 None。"""
    s = str(time_sort or "")
    if len(s) != 8 or not s.isdigit():
        return None
    current = None
    for period in _ORDERED:
        if s >= period["start_sort"]:
            current = period["name"]
        else:
            break
    return current
