# -*- coding: utf-8 -*-
"""① 分词：jieba 加载自定义词典 userdict.txt（由 dictionary.py 生成），确保专名不被切碎。"""
import logging
import os

import jieba

jieba.setLogLevel(logging.WARNING)

RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
USERDICT_PATH = os.path.join(RESOURCE_DIR, "userdict.txt")


def load_userdict(path=USERDICT_PATH):
    """加载自定义词典（文件不存在时跳过；重复加载安全）。"""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        jieba.load_userdict(path)
        return True
    return False


def cut(text):
    """精确模式分词，去除空白 token。"""
    return [t for t in jieba.lcut(text or "") if t.strip()]
