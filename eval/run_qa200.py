# -*- coding: utf-8 -*-
"""
200 条端到端问答评测（V3 9.1 核心实验，目标总准确率 ≥ 80%）。

用法（项目根目录）：venv\\Scripts\\python -m eval.run_qa200 [--report 路径] [--list 20]

判定口径（V3 9.1，三条同时满足才记正确）：
  ① 意图判定正确；② 实体链接正确（干扰样本须纠回正确实体）；③ 答案内容与图谱事实一致。
第 ③ 条不靠人眼：按冻结的「意图 + 实体」标注**在评测时现向图谱要一次正确答案**，再核对答案是否含它。
不用 CSV 里 `expect_contains` 那一列的原因——它是建集时的快照，回补数据后不会变，
沿用它会让「按 V3 要求回补知识缺失」永远反映不到分数上。冻结的是题目与标注，不是答案快照。

错误归因（V3 9.1 三类 + 一类细分）：
  实体未识别 —— 第 ③ 步没链到标注实体（同音干扰纠错失败多归此类）；
  意图误判   —— 实体对了但意图错；
  图谱知识缺失 —— 意图与实体都对，但图谱本就没有该属性/关系（建集时 expect 为空）；
  答案不符   —— 三者都对而答案未含期望内容（模板或查询问题，属真 bug）。

归因结果直接构成论文"结果分析"；**知识缺失项按 V3 的要求回补数据，不得改题**。
产出：控制台结果 + `eval/datasets/qa200_report.md`。
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

from eval.build_qa_dataset import expected_answer  # noqa: E402
from eval.dataset_templates import QA_CATEGORIES  # noqa: E402

DATA_CSV = os.path.join(_ROOT, "eval", "datasets", "qa200.csv")
REPORT_MD = os.path.join(_ROOT, "eval", "datasets", "qa200_report.md")
TARGET = 0.80
MISS_HINT = ("暂未收录", "未收录", "没有找到", "暂未找到")
REASONS = ("实体未识别", "意图误判", "图谱知识缺失", "答案不符")


def load_dataset():
    if not os.path.exists(DATA_CSV):
        return []
    with io.open(DATA_CSV, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def judge(row, resp, expect):
    """返回 (是否正确, 归因)；正确时归因为空串。expect 为评测时现取的图谱答案。"""
    linked = set(resp.get("_meta", {}).get("linked_entities") or [])
    if not linked:
        linked = {e.get("name") for e in resp.get("entities") or []}
    if row["entity"] not in linked:
        return False, "实体未识别"
    if resp.get("intent") != row["intent"]:
        return False, "意图误判"
    expect = (expect or "").strip()
    if not expect:
        return False, "图谱知识缺失"
    answer = resp.get("answer_text") or ""
    if expect[:24] in answer or expect in answer:
        return True, ""
    if any(hint in answer for hint in MISS_HINT):
        return False, "图谱知识缺失"
    return False, "答案不符"


def run(rows, run_read):
    from qa import pipeline

    results = []
    for row in rows:
        expect = expected_answer(row["intent"], row["entity"], row["entity_type"], run_read)
        try:
            resp = pipeline.answer(row["question"], {"use_llm": False, "user_id": None})
        except Exception as exc:  # noqa: BLE001 —— 单条异常不终止整轮评测
            results.append((row, {"answer_text": "", "intent": "ERROR", "_meta": {}},
                            False, "答案不符", str(exc)[:60]))
            continue
        ok, reason = judge(row, resp, expect)
        results.append((row, resp, ok, reason, ""))
    return results


def tables(results):
    """分类准确率表 + 归因统计（V3 9.1 两张论文用表）。"""
    by_cat = {}
    for row, _, ok, _, _ in results:
        stat = by_cat.setdefault(row["category"], [0, 0])
        stat[0] += 1
        stat[1] += 1 if ok else 0
    cat_lines = ["| 类别 | 条数 | 正确 | 准确率 |", "|---|---|---|---|"]
    for category, _ in QA_CATEGORIES:
        total, hit = by_cat.get(category, [0, 0])
        if total:
            cat_lines.append("| %s | %d | %d | %.1f%% |" % (category, total, hit, hit * 100.0 / total))

    reasons = Counter(r for _, _, ok, r, _ in results if not ok)
    total_bad = sum(reasons.values()) or 1
    reason_lines = ["| 错误归因 | 条数 | 占错误比 |", "|---|---|---|"]
    for reason in REASONS:
        if reasons.get(reason):
            reason_lines.append("| %s | %d | %.1f%% |"
                                % (reason, reasons[reason], reasons[reason] * 100.0 / total_bad))
    return cat_lines, reason_lines, by_cat, reasons


def write_report(path, results, cat_lines, reason_lines, accuracy):
    perturbed = [(row, ok) for row, _, ok, _, _ in results if row["perturbed"] == "1"]
    hit_perturb = sum(1 for _, ok in perturbed if ok)
    lines = [
        "# 200 条端到端问答评测报告", "",
        "> 由 `eval/run_qa200.py` 生成；数据集 `eval/datasets/qa200.csv` 已冻结，"
        "只回补数据、不改题目。", "",
        "## 一、总体结果", "",
        "- 评测条数：%d，**总准确率 %.1f%%**（V3 9.1 目标 ≥ %.0f%%，%s）"
        % (len(results), accuracy * 100, TARGET * 100, "达标" if accuracy >= TARGET else "未达标"),
        "- 判定口径：意图正确 ∧ 实体链接正确 ∧ 答案内容与图谱事实一致，三条同时满足才记正确",
        "- 同音干扰样本 %d 条，其中答对 %d 条（考察三级实体链接的纠错能力）"
        % (len(perturbed), hit_perturb), "",
        "## 二、分类准确率", "",
    ] + cat_lines + ["", "## 三、错误归因", ""] + reason_lines + ["", "## 四、错例（每类归因取 3 条）", ""]
    for reason in REASONS:
        picked = [(row, resp) for row, resp, ok, r, _ in results if not ok and r == reason][:3]
        if not picked:
            continue
        lines.append("**%s**" % reason)
        for row, resp in picked:
            lines.append("- 「%s」→ 意图 %s（应为 %s），答案：%s"
                         % (row["question"], resp.get("intent"), row["intent"],
                            (resp.get("answer_text") or "（空）")[:50]))
        lines.append("")
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="200 条端到端问答评测")
    parser.add_argument("--report", default=REPORT_MD, help="报告输出路径")
    parser.add_argument("--list", type=int, default=0, help="打印前 N 条错例")
    args = parser.parse_args()

    rows = load_dataset()
    if not rows:
        print("未找到评测集，请先执行：python -m eval.build_qa_dataset")
        return 1

    from backend.app import create_app
    from backend.extensions import neo4j_available, neo4j_status, run_read

    app = create_app(load_resources=True)
    with app.app_context():
        if not neo4j_available():
            print("Neo4j 未连接：%s" % neo4j_status()["error"])
            return 1
        results = run(rows, run_read)

    hit = sum(1 for _, _, ok, _, _ in results if ok)
    accuracy = hit * 100.0 / len(results) / 100
    cat_lines, reason_lines, by_cat, reasons = tables(results)

    print("\n200 条端到端问答评测（V3 9.1）\n")
    print("  总准确率 %.1f%%（%d/%d），目标 ≥ %.0f%% —— %s"
          % (accuracy * 100, hit, len(results), TARGET * 100,
             "达标" if accuracy >= TARGET else "未达标"))
    print("\n  分类准确率：")
    for category, _ in QA_CATEGORIES:
        total, ok = by_cat.get(category, [0, 0])
        if total:
            print("    %-10s %3d 条  正确 %3d  %.1f%%" % (category, total, ok, ok * 100.0 / total))
    print("\n  错误归因：")
    for reason in REASONS:
        if reasons.get(reason):
            print("    %-12s %3d 条" % (reason, reasons[reason]))
    if args.list:
        print("\n  错例：")
        for row, resp, ok, reason, note in results:
            if ok or args.list <= 0:
                continue
            print("    [%s] %s → %s" % (reason, row["question"][:38],
                                        (resp.get("answer_text") or note or "（空）")[:36]))
            args.list -= 1

    write_report(args.report, results, cat_lines, reason_lines, accuracy)
    print("\n报告：%s" % os.path.relpath(args.report, _ROOT).replace("\\", "/"))
    return 0 if accuracy >= TARGET else 1


if __name__ == "__main__":
    sys.exit(main())
