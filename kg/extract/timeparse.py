# -*- coding: utf-8 -*-
"""
时间标准化唯一实现（V3 3.3 / 开发规范 7.3）：time_text → (time_sort, time_precision)
采集清洗与后台表单共用。

- time_sort：8 位字符串，取起始日 YYYYMMDD；仅到月补 99（19350199）、仅到年补 9999（19359999），
  保证"仅年/仅月条目排在当年/当月末尾"且字符串比较排序无歧义；禁止存整数或日期类型。
- time_precision：day / month / year。
- 解析失败返回 (None, None)，由调用方给出 422 可读提示。
"""
import re

_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_CN_NUM = {"〇": "0", "零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
           "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}

_YEAR = re.compile(r"(\d{3,4})\s*年")
_MONTH = re.compile(r"(\d{1,2})\s*月")
_DAY = re.compile(r"(\d{1,2})\s*[日号]")
_ISO = re.compile(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?")


def _cn_value(cn):
    """中文数字（1–99，支持"十""十一""二十三"）→ int；无法识别返回 None。"""
    if not cn:
        return None
    if "十" not in cn:
        digits = "".join(_CN_NUM.get(c, "") for c in cn)
        return int(digits) if digits else None
    head, _, tail = cn.partition("十")
    tens = int(_CN_NUM[head]) if head and head in _CN_NUM else 1
    ones = int(_CN_NUM[tail]) if tail and tail in _CN_NUM else 0
    return tens * 10 + ones


def normalize_digits(text):
    """全角数字 → 半角；中文数字年 / 月 / 日（如"一九二一年七月二十三日"）→ 阿拉伯数字。"""
    if not text:
        return ""
    s = str(text).translate(_DIGITS)
    s = re.sub(r"([〇零一二三四五六七八九]{4})年",
               lambda m: "".join(_CN_NUM.get(c, c) for c in m.group(1)) + "年", s)
    for unit in ("月", "日", "号"):
        s = re.sub(r"([〇零一二三四五六七八九十]{1,3})" + unit,
                   lambda m, u=unit: ("%d%s" % (_cn_value(m.group(1)), u)
                                      if _cn_value(m.group(1)) else m.group(0)), s)
    return s


def parse(time_text):
    """返回 (time_sort, time_precision)；无法识别返回 (None, None)。"""
    s = normalize_digits(time_text).strip()
    if not s:
        return None, None

    iso = _ISO.search(s)
    if iso:
        year, month, day = int(iso.group(1)), int(iso.group(2)), iso.group(3)
        if day:
            return "%04d%02d%02d" % (year, month, int(day)), "day"
        return "%04d%02d99" % (year, month), "month"

    ym = _YEAR.search(s)
    if not ym:
        return None, None
    year = int(ym.group(1))
    rest = s[ym.end():]

    mm = _MONTH.search(rest)
    if not mm:
        return "%04d9999" % year, "year"
    month = int(mm.group(1))
    if not (1 <= month <= 12):
        return "%04d9999" % year, "year"

    dm = _DAY.search(rest[mm.end():])
    if not dm:
        return "%04d%02d99" % (year, month), "month"
    day = int(dm.group(1))
    if not (1 <= day <= 31):
        return "%04d%02d99" % (year, month), "month"
    return "%04d%02d%02d" % (year, month, day), "day"
