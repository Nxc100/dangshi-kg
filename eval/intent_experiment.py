# -*- coding: utf-8 -*-
"""
意图分类对比实验（V3 6.1 / 9.2，论文实验章素材）。

用法（项目根目录）：venv\\Scripts\\python -m eval.intent_experiment [--report 路径]

数据：`eval/datasets/intent900.csv`（15 意图 × 60 条），按 **7:3 分层切分**训练/测试集。
对比三种方法，在**同一测试集**上评总准确率与宏 F1：

  · 规则法（主线）—— `qa/intent_classifier.py`，无需训练；为与另两法可比，
    把数据集标注的实体类型作为"实体链接已正确"的前提喂给它，
    这样比较的是**纯意图判别能力**，不掺入实体链接的误差；
  · 朴素贝叶斯 —— MultinomialNB；
  · 线性 SVM —— LinearSVC。
  后两者共用特征：TF-IDF 字符 2–3 元 + 词 1–2 元（jieba 分词）+ 疑问词性二值特征
  （`qa/pos_tagger.py` 抽出的疑问词与触发词，与主线管道同源，不另造一套）。

产出：控制台对照表 + `eval/datasets/intent_experiment_report.md`（论文可直接引用）。
"""
import argparse
import csv
import io
import os
import sys
from collections import Counter

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from qa import intent_classifier, pos_tagger, tokenizer  # noqa: E402
from qa.intent_rules import INTENT_ZH, INTENTS  # noqa: E402

DATA_CSV = os.path.join(_ROOT, "eval", "datasets", "intent900.csv")
REPORT_MD = os.path.join(_ROOT, "eval", "datasets", "intent_experiment_report.md")
SEED = 20260916
TEST_SIZE = 0.3


def load_dataset():
    if not os.path.exists(DATA_CSV):
        return []
    with io.open(DATA_CSV, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rule_predict(rows):
    """规范主线：关键词 + 词性 + 实体类型三特征联合规则表。"""
    out = []
    for row in rows:
        question = row["question"]
        feats = pos_tagger.features(pos_tagger.tag(question), question)
        entities = [{"name": row["entity"], "type": row["entity_type"]}]
        out.append(intent_classifier.classify(question, feats, entities))
    return out


class QuestionFeatures(object):
    """疑问词与触发词的二值特征（与主线管道共用 pos_tagger，避免两套口径）。"""

    def fit(self, texts, y=None):
        return self

    def transform(self, texts):
        import numpy as np

        vocab = list(pos_tagger.QUESTION_WORDS) + list(pos_tagger.TRIGGER_VERBS)
        matrix = np.zeros((len(texts), len(vocab) + 1), dtype=float)
        for i, text in enumerate(texts):
            feats = pos_tagger.features(pos_tagger.tag(text), text)
            hits = set(feats["question_words"]) | set(feats["triggers"])
            for j, term in enumerate(vocab):
                if term in hits or term in text:
                    matrix[i, j] = 1.0
            matrix[i, -1] = 1.0 if feats["has_question"] else 0.0
        return matrix

    def fit_transform(self, texts, y=None):
        return self.fit(texts).transform(texts)

    def get_params(self, deep=True):
        return {}

    def set_params(self, **params):
        return self


def build_model(kind):
    """TF-IDF 字符 2–3 元 + 词 1–2 元 + 疑问词性特征 → 分类器。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.svm import LinearSVC

    features = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char", ngram_range=(2, 3), min_df=2)),
        ("word", TfidfVectorizer(tokenizer=tokenizer.cut, token_pattern=None,
                                 ngram_range=(1, 2), min_df=2)),
        ("qw", QuestionFeatures()),
    ])
    clf = MultinomialNB() if kind == "nb" else LinearSVC(C=1.0, max_iter=5000)
    return Pipeline([("feat", features), ("clf", clf)])


def split(rows):
    """7:3 分层切分：每类意图的训练/测试比例一致。"""
    from sklearn.model_selection import train_test_split

    labels = [r["intent"] for r in rows]
    return train_test_split(rows, test_size=TEST_SIZE, random_state=SEED, stratify=labels)


def score(truth, pred):
    from sklearn.metrics import accuracy_score, f1_score

    return accuracy_score(truth, pred), f1_score(truth, pred, average="macro", zero_division=0)


def per_intent_table(truth, preds_by_method):
    """逐意图准确率对照，供论文列表。"""
    lines = ["| 意图 | 名称 | 测试条数 | 规则法 | 朴素贝叶斯 | 线性 SVM |", "|---|---|---|---|---|---|"]
    for intent in INTENTS:
        index = [i for i, t in enumerate(truth) if t == intent]
        if not index:
            continue
        cells = []
        for method in ("rule", "nb", "svm"):
            pred = preds_by_method[method]
            hit = sum(1 for i in index if pred[i] == intent)
            cells.append("%.1f%%" % (hit * 100.0 / len(index)))
        lines.append("| %s | %s | %d | %s |" % (intent, INTENT_ZH[intent], len(index), " | ".join(cells)))
    return lines


def error_cases(rows, truth, pred, limit=8):
    """错例：按「真实 → 预测」聚合，各取一条实例。"""
    bucket = {}
    for row, t, p in zip(rows, truth, pred):
        if t != p:
            bucket.setdefault((t, p), []).append(row)
    ordered = sorted(bucket.items(), key=lambda kv: -len(kv[1]))
    return [(t, p, len(items), items[0]) for (t, p), items in ordered[:limit]]


def write_report(path, stats, table, errors, sizes):
    lines = [
        "# 意图分类对比实验报告", "",
        "> 由 `eval/intent_experiment.py` 生成，改数据或改规则后重跑即可刷新。", "",
        "## 一、实验设置", "",
        "- 数据集：`eval/datasets/intent900.csv`，15 类意图 × 60 条 = %d 条"
        "（模板 40 + 改写 20；改写句刻意绕开规则关键词）" % sizes["total"],
        "- 切分：7:3 **分层**切分，训练 %d 条 / 测试 %d 条，随机种子 %d"
        % (sizes["train"], sizes["test"], SEED),
        "- 规则法为项目主线实现，不训练；为与另两法可比，按「实体链接已正确」喂入标注的实体类型",
        "- 机器学习法特征：TF-IDF 字符 2–3 元 + 词 1–2 元（jieba）+ 疑问词/触发词二值特征", "",
        "## 二、总体结果", "",
        "| 方法 | 总准确率 | 宏 F1 |", "|---|---|---|",
    ]
    for key, name in (("rule", "规则法（主线）"), ("nb", "朴素贝叶斯"), ("svm", "线性 SVM")):
        lines.append("| %s | %.1f%% | %.3f |" % (name, stats[key][0] * 100, stats[key][1]))
    lines += ["", "## 三、逐意图准确率", ""] + table
    lines += ["", "## 四、错例分析", ""]
    if not errors:
        lines.append("测试集上三种方法均无错例。")
    for method, items in errors.items():
        lines.append("**%s**" % method)
        if not items:
            lines.append("- 无错例")
        for truth, pred, count, row in items:
            lines.append("- %s(%s) → 误判为 %s(%s)，%d 例，如：「%s」"
                         % (truth, INTENT_ZH[truth], pred, INTENT_ZH.get(pred, pred),
                            count, row["question"]))
        lines.append("")
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="意图分类对比实验（规则 / 朴素贝叶斯 / 线性 SVM）")
    parser.add_argument("--report", default=REPORT_MD, help="报告输出路径")
    parser.add_argument("--tune", action="store_true",
                        help="只打印规则法在**训练集**上的错例，供调规则表用（禁止看测试集调参）")
    args = parser.parse_args()

    rows = load_dataset()
    if not rows:
        print("未找到数据集，请先执行：python -m eval.build_intent_dataset")
        return 1

    train, test = split(rows)
    if args.tune:
        pred = rule_predict(train)
        truth = [r["intent"] for r in train]
        hit = sum(1 for t, p in zip(truth, pred) if t == p)
        print("\n规则法在训练集上的准确率：%.1f%%（%d/%d）\n" % (hit * 100.0 / len(train), hit, len(train)))
        for t, p, count, row in error_cases(train, truth, pred, limit=40):
            print("  %s→%s ×%-3d 例：%s" % (t, p, count, row["question"]))
        return 0
    truth = [r["intent"] for r in test]
    preds = {"rule": rule_predict(test)}
    for kind in ("nb", "svm"):
        model = build_model(kind)
        model.fit([r["question"] for r in train], [r["intent"] for r in train])
        preds[kind] = list(model.predict([r["question"] for r in test]))

    stats = {key: score(truth, pred) for key, pred in preds.items()}
    print("\n意图分类对比实验（900 条，7:3 分层切分，训练 %d / 测试 %d）\n" % (len(train), len(test)))
    print("  %-16s %10s %10s" % ("方法", "总准确率", "宏 F1"))
    for key, name in (("rule", "规则法（主线）"), ("nb", "朴素贝叶斯"), ("svm", "线性 SVM")):
        print("  %-16s %9.1f%% %10.3f" % (name, stats[key][0] * 100, stats[key][1]))

    table = per_intent_table(truth, preds)
    errors = {name: error_cases(test, truth, preds[key])
              for key, name in (("rule", "规则法"), ("nb", "朴素贝叶斯"), ("svm", "线性 SVM"))}
    print("\n  错例分布（真实 → 预测，取前 3）：")
    for name, items in errors.items():
        head = "；".join("%s→%s×%d" % (t, p, c) for t, p, c, _ in items[:3]) or "无"
        print("    %-10s %s" % (name, head))
    sizes = {"total": len(rows), "train": len(train), "test": len(test)}
    write_report(args.report, stats, table, errors, sizes)
    print("\n报告：%s" % os.path.relpath(args.report, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
