# -*- coding: utf-8 -*-
"""
DR-11 候选实体与三元组抽取（V3 3.4「规则自动抽取 + Excel 半自动整理」的自动部分）。

输入 data/clean/events_raw.csv（DR-08 产出的 1043 条编年条目），
输出两份候选表供 Excel 人工整理：
  data/clean/candidate_entities.csv   候选实体（类型、名称、首次出现年份、出现次数、置信度、证据）
  data/clean/candidate_triples.csv    候选三元组（头、关系、尾、置信度、证据）

置信度分档（V3 3.4 要求候选三元组「置信度分列」）：
  high   —— 专名模式严格命中且非泛称，如「中国共产党第七次全国代表大会」「南昌起义」
  medium —— 模式命中但需人工确认边界，如以「会议」结尾的短名
  low    —— 命中泛称黑名单或长度可疑，默认不入库

抽取只产出候选，不直接入图。入图前须经 Excel 人工确认（V3 3.4 第 2 步）与
核心池校验（V3 3.6），以守住「核心知识零差错」红线。

用法（项目根目录）：python -m kg.extract.extract_triples [--min-count 1]
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import write_csv  # noqa: E402

EVENTS_CSV = os.path.join(_ROOT, "data", "clean", "events_raw.csv")
ENT_CSV = os.path.join(_ROOT, "data", "clean", "candidate_entities.csv")
TRI_CSV = os.path.join(_ROOT, "data", "clean", "candidate_triples.csv")

ENT_FIELDS = ["实体类型", "候选名称", "首次出现年份", "出现次数", "置信度", "证据条目"]
TRI_FIELDS = ["头实体", "头类型", "关系", "尾实体", "尾类型", "年份", "置信度", "证据条目"]

# 泛称与非党史实体：命中即降为 low，不进高置信度候选
STOPWORDS = {
    "会议", "全会", "大会", "全体会议", "代表大会", "常务会议", "工作会议", "座谈会",
    "中央政治局会议", "中央政治局扩大会议", "国务院常务会议", "中央书记处会议",
    "中国政府", "中央军", "政府", "国务院", "委员会", "中央委员会", "党中央",
    "人民日报", "新华社", "联合国", "解放军报", "求是",
}
# 明显不属于党史领域的国别/机构关键词
FOREIGN = re.compile(r"(新加坡|美国|日本|苏联|俄罗斯|法国|英国|德国|朝鲜|越南|联合国|世界贸易)")

# 专名模式：命名越完整置信度越高
MEETING_STRICT = re.compile(
    r"(中国共产党第[一二三四五六七八九十]+次全国代表大会"
    r"|中国共产党第[一二三四五六七八九十]+届中央委员会第[一二三四五六七八九十]+次全体会议"
    r"|[一-龥]{2,6}会议)")
EVENT_STRICT = re.compile(r"([一-龥]{2,8}(?:起义|战役|事变|会师|大典))")
EVENT_LOOSE = re.compile(r"([一-龥]{2,8}(?:运动|战争|长征|谈判))")
ORG_STRICT = re.compile(
    r"(中国共产党|中国工农红军|中国人民解放军|八路军|新四军|中国共产主义青年团"
    r"|中华全国总工会|中国人民志愿军|中华苏维埃共和国)")
DOC_PAT = re.compile(r"《([^》]{2,30})》")
PLACE_PAT = re.compile(r"在([一-龥]{2,6}?)(?:召开|举行|成立|爆发|签订)")
# 人物：条目中「姓名 + 动词」的常见表述
PERSON_PAT = re.compile(
    r"(毛泽东|周恩来|刘少奇|朱德|邓小平|陈云|李大钊|陈独秀|彭德怀|贺龙|陈毅|董必武"
    r"|任弼时|张闻天|王稼祥|叶剑英|林伯渠|李富春|聂荣臻|徐向前|罗荣桓|刘伯承|粟裕)")
LED_VERB = re.compile(r"(领导|发动|指挥|率领)")


# 残段特征：正则从句子中间起截会产出「央政治局扩大会议」「国共产党领导工人运」这类名称。
# 以动词/连词/助词开头，或以已知专名的非首字开头，均判为截断残段。
BAD_HEAD = re.compile(
    r"^(是|在|的|了|和|与|为|由|把|被|对|向|从|到|并|又|再|这|那|其|该|以|使|即|等|上|下|后|前"
    r"|领导|发动|指挥|率领|举行|召开|成立|通过|决定|提出|开展|进行|推进|标志|成为|实现|建立)")
# 常见专名的非首字（如「国共产党」缺「中」、「央政治局」缺「中」）
BAD_FRAGMENT = re.compile(r"^(国共产党|央政治|央军委|央委员|华人民|民共和|产党|华全国)")


# 专名内部不应出现的动词与虚词：出现即说明截取跨越了词边界，
# 如「中共中央根据会师」「周恩来任起义」「先后领导发动武装起义」
INNER_VERB = re.compile(
    r"(根据|任职|担任|先后|领导|发动|指挥|率领|举行|召开|成立|通过|决定|提出|开展|进行"
    r"|主持|出席|参加|发表|批准|同意|要求|指出|强调|宣布|标志|成为|实现|建立|完成|取得)")


def is_truncated(name, body):
    """
    判断候选名是否为截断残段。三重判据，任一命中即弃用：
      1) 以动词 / 虚词开头，或以已知专名的非首字开头；
      2) 名称内部含动词（专名不会包含「根据」「任」这类词）；
      3) 名称在原文中被前一个汉字粘连，说明左边界落在词中。
    这是「核心知识零差错」的第一道闸门——残缺名一旦入库即为错误知识。
    """
    if BAD_HEAD.match(name) or BAD_FRAGMENT.match(name):
        return True
    if INNER_VERB.search(name):
        return True
    idx = body.find(name)
    if idx < 0:
        return False
    before = body[idx - 1] if idx > 0 else ""
    return bool(before) and "一" <= before <= "龥"


def confidence(kind, name):
    """按名称完整度与黑名单给出置信度档位。"""
    if name in STOPWORDS or FOREIGN.search(name):
        return "low"
    if len(name) < 3:
        return "low"
    if kind == "会议":
        return "high" if ("全国代表大会" in name or "全体会议" in name) else "medium"
    if kind == "事件":
        return "high" if EVENT_STRICT.fullmatch(name) else "medium"
    if kind == "组织":
        return "high" if ORG_STRICT.fullmatch(name) else "medium"
    if kind == "文献":
        return "medium"
    if kind == "地点":
        return "medium" if 2 <= len(name) <= 4 else "low"
    return "medium"


def extract(rows):
    """返回 (候选实体字典, 候选三元组列表)。"""
    ents = defaultdict(lambda: {"count": 0, "first_year": None, "evidence": ""})
    triples = []
    patterns = [("会议", MEETING_STRICT), ("事件", EVENT_STRICT), ("事件", EVENT_LOOSE),
                ("组织", ORG_STRICT), ("地点", PLACE_PAT)]

    for row in rows:
        body, year = row["条目正文"], row["年份"]
        found = defaultdict(set)
        for kind, pat in patterns:
            for m in pat.findall(body):
                name = (m if isinstance(m, str) else m[0]).strip()
                if 2 <= len(name) <= 30 and not is_truncated(name, body):
                    found[kind].add(name)
        # 书名号内的文献名有明确边界，无需截断校验
        for name in DOC_PAT.findall(body):
            if 2 <= len(name) <= 30:
                found["文献"].add(name.strip())

        for kind, names in found.items():
            for name in names:
                item = ents[(kind, name)]
                item["count"] += 1
                if item["first_year"] is None:
                    item["first_year"] = year
                    item["evidence"] = body[:60]

        # 候选三元组：人物 + 领导类触发词 + 同句事件
        persons = set(PERSON_PAT.findall(body))
        if persons and LED_VERB.search(body):
            for ev in found.get("事件", ()):
                if confidence("事件", ev) == "low":
                    continue
                for person in persons:
                    triples.append({
                        "头实体": person, "头类型": "Person", "关系": "LED",
                        "尾实体": ev, "尾类型": "Event", "年份": year,
                        "置信度": "medium",  # 同句共现≠领导关系，一律交人工确认
                        "证据条目": body[:60],
                    })
        # 候选三元组：事件/会议 + 地点
        for place in found.get("地点", ()):
            for kind in ("会议", "事件"):
                for name in found.get(kind, ()):
                    if confidence(kind, name) == "low":
                        continue
                    triples.append({
                        "头实体": name, "头类型": "Meeting" if kind == "会议" else "Event",
                        "关系": "HELD_IN" if kind == "会议" else "OCCURRED_IN",
                        "尾实体": place, "尾类型": "Location", "年份": year,
                        "置信度": "medium", "证据条目": body[:60],
                    })
    return ents, triples


def to_rows(ents, min_count):
    out = []
    for (kind, name), item in ents.items():
        if item["count"] < min_count:
            continue
        out.append({
            "实体类型": kind, "候选名称": name, "首次出现年份": item["first_year"],
            "出现次数": item["count"], "置信度": confidence(kind, name),
            "证据条目": item["evidence"],
        })
    out.sort(key=lambda r: (r["实体类型"], -r["出现次数"], r["候选名称"]))
    return out


def summarize(ent_rows, tri_rows):
    from collections import Counter

    print("\n候选实体：%d 个" % len(ent_rows))
    by_kind = Counter(r["实体类型"] for r in ent_rows)
    by_conf = Counter(r["置信度"] for r in ent_rows)
    for kind, n in by_kind.most_common():
        highs = sum(1 for r in ent_rows if r["实体类型"] == kind and r["置信度"] == "high")
        print("  %-4s %5d 个（high %d）" % (kind, n, highs))
    print("  置信度分布：%s" % dict(by_conf))
    print("候选三元组：%d 条（按关系：%s）"
          % (len(tri_rows), dict(Counter(r["关系"] for r in tri_rows))))
    print("\n注意：候选仅供 Excel 人工整理，high 档也需逐条核对后方可入库（V3 3.4 / 3.6）。")


def main():
    parser = argparse.ArgumentParser(description="DR-11 候选实体与三元组抽取")
    parser.add_argument("--min-count", type=int, default=1, help="候选实体最少出现次数")
    args = parser.parse_args()

    if not os.path.exists(EVENTS_CSV):
        print("未找到 %s，请先执行 python -m kg.extract.parse_events" % EVENTS_CSV)
        return 1
    with open(EVENTS_CSV, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    ents, triples = extract(rows)
    ent_rows = to_rows(ents, args.min_count)
    # 三元组按「头-关系-尾」去重，保留首次证据
    seen, tri_rows = set(), []
    for t in triples:
        key = (t["头实体"], t["关系"], t["尾实体"])
        if key in seen:
            continue
        seen.add(key)
        tri_rows.append(t)

    write_csv(ENT_CSV, ent_rows, ENT_FIELDS)
    write_csv(TRI_CSV, tri_rows, TRI_FIELDS)
    summarize(ent_rows, tri_rows)
    print("\n产出：%s" % os.path.relpath(ENT_CSV, _ROOT).replace("\\", "/"))
    print("      %s" % os.path.relpath(TRI_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
