# -*- coding: utf-8 -*-
"""
文本清洗与标准化（V3 3.3 / DR-07 / 开发规范 7.3）——采集与整理共用，禁止各处重复实现。

规则：去 HTML 标签残留、全角→半角（数字与标点）、连续空白归一、去零宽字符；
段落切分（滤除 < 30 字）供 F9 语料构建使用。
（繁简转换按 V3 3.3 要求执行；本项目依赖固定 14 个包、不引入 opencc，
 故对权威简体来源不做转换，如遇繁体来源在 Excel 整理阶段人工处理。）
"""
import re

MIN_PARAGRAPH_LEN = 30

_FULL_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_FULL_LETTERS = str.maketrans(
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
# 仅归一化会影响解析的标点；中文引号书名号等保留原貌
_FULL_PUNCT = str.maketrans("（）［］％＋－＝／＼＜＞＃＆＊", "()[]%+-=/\\<>#&*")

_TAG = re.compile(r"<[^>]+>")
_ZERO_WIDTH = re.compile(r"[​-‏﻿ ]")
_SPACE = re.compile(r"[ \t\r\f\v]+")
_NEWLINES = re.compile(r"\n{2,}")


def half_width(text):
    """全角数字 / 字母 / 影响解析的标点 → 半角（DR-02 老页面"１９２１年"）。"""
    if not text:
        return ""
    return str(text).translate(_FULL_DIGITS).translate(_FULL_LETTERS).translate(_FULL_PUNCT)


def strip_tags(text):
    return _TAG.sub(" ", text or "")


def clean_text(text, keep_newline=False):
    """去标签残留 + 全半角归一 + 空白归一。"""
    s = _ZERO_WIDTH.sub("", strip_tags(text))
    s = half_width(s)
    s = _SPACE.sub(" ", s)
    s = _NEWLINES.sub("\n", s) if keep_newline else s.replace("\n", " ")
    return s.strip()


def split_paragraphs(text, min_len=MIN_PARAGRAPH_LEN):
    """按自然段切分并滤除短段（F9 语料构建：paragraphs.csv 的 text 列）。"""
    out = []
    for raw in re.split(r"[\n\r]+", clean_text(text, keep_newline=True)):
        para = raw.strip()
        if len(para) >= min_len:
            out.append(para)
    return out


def normalize_name(name):
    """实体名规范：去空白与外层引号，全半角归一。"""
    return clean_text(name).strip().strip("\"'“”")
