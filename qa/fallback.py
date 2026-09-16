# -*- coding: utf-8 -*-
"""
F9 权威资料检索兜底（V3 7.9 / 开发规范 6.4）：
服务启动时对 data/corpus/paragraphs.csv（字段 text, chapter, source）构建 TF-IDF 矩阵（jieba 分词，词 1–2 元）常驻内存；
retrieve(question) → top3 且余弦相似度 ≥ 0.05 的段落 [{text, chapter, source, score}]。
原路径展示与 LLM 生成输入共用同一结果。语料文件缺失时为空检索器（返回 []），系统仍可启动。
"""
import csv
import logging
import os

from sklearn.feature_extraction.text import TfidfVectorizer

from backend.config import Config
from qa import tokenizer

log = logging.getLogger(__name__)


class Retriever:
    def __init__(self):
        self.passages = []
        self.vectorizer = None
        self.matrix = None

    def build(self, csv_path):
        self.passages, self.vectorizer, self.matrix = [], None, None
        if not csv_path or not os.path.exists(csv_path):
            log.warning("兜底语料不存在：%s（F9 检索暂不可用）", csv_path)
            return self
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                text = (row.get("text") or "").strip()
                if len(text) < 30:
                    continue
                self.passages.append({
                    "text": text,
                    "chapter": (row.get("chapter") or "").strip(),
                    "source": (row.get("source") or "").strip(),
                })
        if not self.passages:
            log.warning("兜底语料为空：%s", csv_path)
            return self
        self.vectorizer = TfidfVectorizer(tokenizer=tokenizer.cut, token_pattern=None, ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(p["text"] for p in self.passages)
        log.info("兜底语料已加载：%d 段，TF-IDF 词表 %d", len(self.passages), len(self.vectorizer.vocabulary_))
        return self

    def ready(self):
        return self.matrix is not None

    def size(self):
        return len(self.passages)

    def retrieve(self, question, topk=None, threshold=None):
        if not self.ready() or not question:
            return []
        topk = topk or Config.FALLBACK_TOPK
        threshold = Config.FALLBACK_THRESHOLD if threshold is None else threshold
        vec = self.vectorizer.transform([question])
        sims = (self.matrix @ vec.T).toarray().ravel()  # 行向量 L2 归一化，点积即余弦相似度
        order = sims.argsort()[::-1][:topk]
        out = []
        for idx in order:
            score = float(sims[idx])
            if score < threshold:
                continue
            item = dict(self.passages[idx])
            item["score"] = round(score, 4)
            out.append(item)
        return out


_retriever = Retriever()


def build(csv_path=None):
    """启动时构建 TF-IDF 矩阵并常驻内存（规范 6.3 性能项：禁止每请求重建）。"""
    return _retriever.build(csv_path or Config.CORPUS_PATH)


def retrieve(question, topk=None, threshold=None):
    """F9 兜底检索：top3 且余弦相似度 ≥ 0.05；原路径展示与 LLM 生成共用同一结果（规范 6.4）。"""
    return _retriever.retrieve(question, topk, threshold)


def is_ready():
    """语料是否已加载（语料缺失时兜底返回空列表，不报错）。"""
    return _retriever.ready()


def size():
    """已加载的语料段落数（验收线 ≥ 2000 段）。"""
    return _retriever.size()
