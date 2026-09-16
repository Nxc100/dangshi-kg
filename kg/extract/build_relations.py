# -*- coding: utf-8 -*-
"""
DR-14 自动关系构建（V3 3.4 第 1 步「规则自动抽取」的关系侧产物）。

扫描对象是 DR-01 大事记与 DR-12 天天读的**编年条目原文**（与 DR-13 同源），
每条关系都由原文中的**显式触发词**支撑，不做共现推断——「同一条目里出现了甲和乙」
不足以断言二者有关系，必须出现「在乙召开」「甲领导」这样的动词/介词结构，
且两端实体名（或其别名）在名录中完整匹配，才产出一条候选关系。

抽取七类；BELONGS_TO 由导入脚本按 time_sort 自动归属，REORGANIZED_TO 语义过强留人工：
  OCCURRED_IN     事件 → 地点    「在<地点>召开 / 举行 / 签署 / 逝世 …」，另认「在京…」简写
  FOUNDED         事件 → 组织    「成立 / 建立 / 组建 <组织>」
  LED             人物/组织 → 事件  事件名以「<人物|组织>领导 / 指挥 / 发动 …」开头
  AUTHORED        人物 → 文献    「<人物>… 发表 / 撰写 / 起草 …《<文献>》」
  HELD_POSITION   人物 → 组织    「<人物>任 / 当选为 <组织><职务>」，职务为必填属性
  PARTICIPATED_IN 人物 → 会议    「<人物>… 出席 / 参加 / 列席 … <会议>」
  PRODUCED        会议 → 文献    「<会议>… 通过 / 制定 / 公布 …《<文献>》」

产出 data/clean/relations_auto.csv，由 db/build_seed.py 按本体头尾约束再校验一遍。

用法（项目根目录）：venv\\Scripts\\python -m kg.extract.build_relations [--sample 8]
"""
import argparse
import csv
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kg.crawler.common import write_csv  # noqa: E402
from kg.extract.build_entities import SENTENCE_END, event_name, load_entries  # noqa: E402

ENTITY_CSV = os.path.join(_ROOT, "data", "clean", "entities_auto.csv")
OUT_CSV = os.path.join(_ROOT, "data", "clean", "relations_auto.csv")
FIELDS = ["head", "head_type", "rel", "tail", "tail_type", "position", "time_text", "source"]

# 「发生于」的触发动词。凡是能说明「这件事在该地做的」的谓语都算，
# 首轮只列了开会类，实测漏掉签署、逝世、考察、发射一类，补齐后覆盖显著提升
OCCUR_VERB = (r"(?:召开|举行|成立|爆发|开幕|闭幕|签订|签署|草签|发生|建成|落成|通车|开工|竣工"
              r"|胜利|会师|登陆|发表|逝世|去世|病逝|牺牲|就义|考察|视察|接见|会见|奠基"
              r"|投产|发射|下水|开播|通水|截流|开学|创刊|开通|运营|试飞|阅兵)")
FOUND_VERB = r"(?:宣告成立|正式成立|成立|建立|组建|设立|创建|创办)"
# 「领导」后跟机构 / 抽象名词时是定语而非谓语（「空军领导机构成立」），须排除
LED_VERB = r"(?:领导|指挥|发动|率领|发起|主持)(?!机构|机关|班子|干部|人员|集体|核心|作用|体制|地位|方式|水平|下)"
WRITE_VERB = r"(?:发表|撰写|起草|写|作|发布|签发)"
PASS_VERB = r"(?:通过|制定|公布|审议通过|批准|颁布|发布)"
JOIN_VERB = r"(?:出席|参加|列席)"
POSITION = (r"(?:总书记|副书记|书记|主席|副主席|委员长|总理|副总理|部长|司令员"
            r"|政治委员|政委|主任|组长|校长|总指挥|总司令)")
HOLD_VERB = r"(?:当选为|当选|被任命为|被选为|兼任|任)"
GAP = 14        # 触发词与实体名之间允许的最大间隔字数
CLAUSE = "[^，。；]"


def load_terms():
    """
    汇集全部已定义实体的主名与别名，返回 {标签: {词条: 主名}}。

    名录 = 种子数据（人工登记，含全部人物）+ DR-11 确认记录 + 核心池 + DR-13 自动实体。
    别名一并纳入匹配，命中后映射回主名，关系表里只出现主名。
    """
    from db.seed_data import entities as E
    from db.seed_data import from_extraction as X
    from qa.dictionary import split_alias

    terms = {label: {} for label in
             ("Person", "Organization", "Event", "Meeting", "Location", "Document")}

    def put(label, name, alias=None):
        if not name:
            return
        terms[label].setdefault(name, name)
        for item in split_alias(alias):
            terms[label].setdefault(item, name)

    for label, (fields, records, _) in E.SEED_ENTITIES.items():
        name_at = fields.index("name")
        alias_at = fields.index("alias") if "alias" in fields else None
        for record in records:
            put(label, record[name_at], record[alias_at] if alias_at is not None else None)
    for record in X.CONGRESSES:
        put("Meeting", record[0], record[1])
    for record in X.EXTRA_LOCATIONS:
        put("Location", record[0], record[1])
    for record in X.EXTRA_ORGANIZATIONS:
        put("Organization", record[0], record[1])
    from db.seed_data import core_pool as C
    for label in C.CORE_ENTITIES:
        alias_at = C.CORE_FIELDS[label].index("alias")
        for record in C.CORE_ENTITIES[label]:
            put(label, record[0], record[alias_at])
    if os.path.exists(ENTITY_CSV):
        with open(ENTITY_CSV, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                put(row["label"], row["name"], row.get("alias"))
    return terms


# 需要编译成交替正则的标签。Event 不在其中：事件名是整句，只作头实体由 event_name 现算，
# 把数千条长名编进正则既无用又会显著拖慢匹配。
MATCH_LABELS = ("Person", "Organization", "Meeting", "Location", "Document")


class Matcher(object):
    """按标签持有「词条交替正则 + 词条→主名」，供各条抽取规则复用。"""

    def __init__(self, terms):
        self.terms = terms
        self.pattern = {}
        for label in MATCH_LABELS:
            mapping = terms.get(label) or {}
            ordered = sorted(mapping, key=len, reverse=True)  # 长词优先，避免匹配到子串
            if ordered:
                self.pattern[label] = "(%s)" % "|".join(re.escape(t) for t in ordered)

    def rule(self, template, **labels):
        """把模板里的 {占位} 换成对应标签的词条正则；缺少任一标签时返回 None。"""
        if any(label not in self.pattern for label in labels.values()):
            return None
        return re.compile(template.format(**{k: self.pattern[v] for k, v in labels.items()}))

    def main_name(self, label, term):
        return self.terms[label].get(term, term)


def build_rules(matcher):
    """编译七条抽取规则，返回 {关系名: 已编译正则}（缺名录的规则为 None）。"""
    return {
        "OCCURRED_IN": matcher.rule(r"在{loc}%s{{0,%d}}?%s" % (CLAUSE, GAP, OCCUR_VERB), loc="Location"),
        # 「在京举行」是编年条目的高频简写，单列一条规则映射到北京（不进词典，以免「京汉铁路」被误链）
        "OCCURRED_IN_JING": re.compile(r"在京%s{0,%d}?%s" % (CLAUSE, GAP, OCCUR_VERB)),
        # 「建立中国共产党领导的统一战线」里的组织名是定语中心语之外的修饰语，排除
        "FOUNDED": matcher.rule(r"%s(?:了)?{org}(?!的|领导|所属|系统)" % FOUND_VERB,
                                org="Organization"),
        "AUTHORED": matcher.rule(r"{per}%s{{0,%d}}?%s%s{{0,6}}《{doc}》"
                                 % (CLAUSE, GAP, WRITE_VERB, CLAUSE), per="Person", doc="Document"),
        "HELD_POSITION": matcher.rule(r"{per}%s{org}(%s)" % (HOLD_VERB, POSITION),
                                      per="Person", org="Organization"),
        "PARTICIPATED_IN": matcher.rule(r"{per}%s{{0,%d}}?%s%s{{0,%d}}?{meet}"
                                        % (CLAUSE, GAP, JOIN_VERB, CLAUSE, GAP),
                                        per="Person", meet="Meeting"),
        "PRODUCED": matcher.rule(r"{meet}%s{{0,20}}?%s%s{{0,8}}《{doc}》"
                                 % (CLAUSE, PASS_VERB, CLAUSE), meet="Meeting", doc="Document"),
        "LED_PERSON": matcher.rule(r"^{per}%s" % LED_VERB, per="Person"),
        "LED_ORG": matcher.rule(r"^{org}%s" % LED_VERB, org="Organization"),
    }


class Collector(object):
    """收集关系行并按 (头, 关系, 尾) 去重。"""

    def __init__(self):
        self.rows, self.seen = [], set()

    def add(self, head, head_type, rel, tail, tail_type, position, entry):
        key = (head, rel, tail)
        if head == tail or not head or not tail or key in self.seen:
            return
        self.seen.add(key)
        self.rows.append({"head": head, "head_type": head_type, "rel": rel, "tail": tail,
                          "tail_type": tail_type, "position": position,
                          "time_text": entry[3], "source": entry[4]})


def extract(entries, matcher):
    """
    逐条编年条目执行七条规则。

    以事件为头的两类关系只在**条目首句**内找证据——事件名正是由首句派生，
    后续句子往往叙述同主题的其他史实（「…衙前村农民大会召开。1922 年 7 月，
    彭湃在广东海丰成立第一个秘密农会。」），跨句取证会张冠李戴。
    """
    rules = build_rules(matcher)
    out = Collector()
    for entry in entries:
        body = entry[2]
        name = event_name(body)
        if name:
            _event_side(name, SENTENCE_END.split(body)[0], rules, matcher, out, entry)
        _person_side(body, rules, matcher, out, entry)
    return out.rows


def _event_side(name, first, rules, matcher, out, entry):
    """以该条目的事件为头实体的三类关系；first 为条目首句。"""
    for rel, label in (("OCCURRED_IN", "Location"), ("FOUNDED", "Organization")):
        if rules[rel]:
            for match in rules[rel].finditer(first):
                out.add(name, "Event", rel, matcher.main_name(label, match.group(1)), label, "", entry)
    if rules["OCCURRED_IN_JING"] and rules["OCCURRED_IN_JING"].search(first):
        out.add(name, "Event", "OCCURRED_IN", "北京", "Location", "", entry)
    for key, head_type, label in (("LED_PERSON", "Person", "Person"),
                                  ("LED_ORG", "Organization", "Organization")):
        match = rules[key].match(name) if rules[key] else None
        if match:
            out.add(matcher.main_name(label, match.group(1)), head_type, "LED", name, "Event", "", entry)
            return


def _person_side(body, rules, matcher, out, entry):
    """以人物或会议为头实体的四类关系。"""
    if rules["AUTHORED"]:
        for match in rules["AUTHORED"].finditer(body):
            out.add(matcher.main_name("Person", match.group(1)), "Person", "AUTHORED",
                    matcher.main_name("Document", match.group(2)), "Document", "", entry)
    if rules["HELD_POSITION"]:
        for match in rules["HELD_POSITION"].finditer(body):
            out.add(matcher.main_name("Person", match.group(1)), "Person", "HELD_POSITION",
                    matcher.main_name("Organization", match.group(2)), "Organization",
                    match.group(3), entry)
    if rules["PARTICIPATED_IN"]:
        for match in rules["PARTICIPATED_IN"].finditer(body):
            out.add(matcher.main_name("Person", match.group(1)), "Person", "PARTICIPATED_IN",
                    matcher.main_name("Meeting", match.group(2)), "Meeting", "", entry)
    if rules["PRODUCED"]:
        for match in rules["PRODUCED"].finditer(body):
            out.add(matcher.main_name("Meeting", match.group(1)), "Meeting", "PRODUCED",
                    matcher.main_name("Document", match.group(2)), "Document", "", entry)


def main():
    parser = argparse.ArgumentParser(description="DR-14 自动关系构建")
    parser.add_argument("--sample", type=int, default=0, help="每类打印 N 条样本")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        print("未找到编年条目，请先执行 kg.extract.parse_events 与 kg.extract.parse_ttd")
        return 1
    matcher = Matcher(load_terms())
    rows = extract(entries, matcher)
    write_csv(OUT_CSV, rows, FIELDS)

    from collections import Counter
    counter = Counter(r["rel"] for r in rows)
    print("\nDR-14 自动关系构建")
    print("  扫描条目 %d，参与匹配的词条 %d 个"
          % (len(entries), sum(len(v) for v in matcher.terms.values())))
    for rel, count in counter.most_common():
        print("  %-18s %5d" % (rel, count))
    print("  合计 %d 条候选关系" % len(rows))
    if args.sample:
        for rel in counter:
            print("\n  %s 样本：" % rel)
            for row in [r for r in rows if r["rel"] == rel][:args.sample]:
                print("    (%s)-[%s%s]->(%s)"
                      % (row["head"][:26], rel, "/" + row["position"] if row["position"] else "",
                         row["tail"][:26]))
    print("\n产出：%s" % os.path.relpath(OUT_CSV, _ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
