# -*- coding: utf-8 -*-
"""
实体词典（全项目唯一词典，开发规范 4.3 / 6.3）。

从 Neo4j 全量加载七类标签的 name 与 alias → {词条: (主名, 类型)}；生成 jieba 词典 userdict.txt；
reload() 以"构建新表 → 原子替换引用"方式热刷新（读方无锁）。
实体链接、图谱搜索联想、测验干扰项排除、后台联想、忠实度校验五处复用本模块，禁止各处自建词表。
别名一对多歧义（同一别名指向不同主名）在加载时拒绝并记录。
Neo4j 不可用时保持空词典（空白项目 / 图谱未导入阶段仍可启动）。
"""
import logging
import os
import re
import threading

from pypinyin import lazy_pinyin

from backend.common.ontology import LABELS
from qa import tokenizer

log = logging.getLogger(__name__)

LOAD_CYPHER = (
    "MATCH (n) WHERE size(labels(n)) > 0 AND labels(n)[0] IN $labels "
    "RETURN labels(n)[0] AS label, n.name AS name, n.alias AS alias"
)
_ALIAS_SPLIT = re.compile(r"[/、,，;；|\s]+")
_USERDICT_FREQ = 1000


class EntityDict:
    def __init__(self):
        self.term_map = {}  # 词条（主名或别名）-> (主名, 类型)
        self.type_by_name = {}  # 主名 -> 类型
        self.names_by_type = {label: [] for label in LABELS}
        self.aliases_by_name = {}  # 主名 -> [别名]
        self._ambiguous = set()
        self._terms = []
        self._terms_by_len = {}
        self._pinyin_index = None

    # ---- 构建 ----
    def add_entity(self, name, label, alias_text=None):
        name = (name or "").strip()
        if not name or label not in LABELS:
            return
        if name in self.type_by_name:
            log.warning("实体主名跨标签重复：%s（%s / %s）", name, self.type_by_name[name], label)
            return
        self.type_by_name[name] = label
        self.names_by_type[label].append(name)
        self.term_map[name] = (name, label)
        self.aliases_by_name.setdefault(name, [])
        for alias in _split_alias(alias_text):
            self.add_alias(alias, name, label)

    def add_alias(self, alias, name, label):
        alias = alias.strip()
        if not alias or alias == name:
            return
        existing = self.term_map.get(alias)
        if existing is not None and existing[0] != name:
            if alias in self.type_by_name:
                return  # 别名与另一实体主名同名：主名优先
            self._ambiguous.add(alias)
            log.warning("别名歧义已拒绝：%s -> %s / %s", alias, existing[0], name)
            return
        self.term_map[alias] = (name, label)
        self.aliases_by_name.setdefault(name, []).append(alias)

    def finalize(self):
        for alias in self._ambiguous:
            if alias in self.term_map and alias not in self.type_by_name:
                owner = self.term_map.pop(alias)[0]
                self.aliases_by_name[owner] = [a for a in self.aliases_by_name.get(owner, []) if a != alias]
        self._terms = sorted(self.term_map.keys(), key=len)
        self._terms_by_len = {}
        for term in self._terms:
            self._terms_by_len.setdefault(len(term), []).append(term)
        self._pinyin_index = None
        return self

    # ---- 查询 ----
    def lookup(self, term):
        return self.term_map.get(term)

    def terms(self):
        return self._terms

    def terms_by_len(self, length):
        return self._terms_by_len.get(length, [])

    def term_lengths(self):
        return sorted(self._terms_by_len.keys())

    def aliases_of(self, name):
        return list(self.aliases_by_name.get(name, []))

    def size(self):
        return len(self.type_by_name)

    def pinyin_index(self):
        """{拼音串: [词条]}，懒构建。"""
        if self._pinyin_index is None:
            index = {}
            for term in self._terms:
                index.setdefault(to_pinyin(term), []).append(term)
            self._pinyin_index = index
        return self._pinyin_index


def split_alias(text):
    """别名字段切分口径（全项目唯一实现）：支持 / 、 , ; | 与空白分隔。"""
    if not text:
        return []
    if isinstance(text, (list, tuple)):
        return [str(a) for a in text if str(a).strip()]
    return [a for a in _ALIAS_SPLIT.split(str(text)) if a.strip()]


_split_alias = split_alias  # 兼容内部旧调用


def to_pinyin(text):
    """转无声调拼音串，供实体链接第三级同音纠错比对。"""
    return "".join(lazy_pinyin(text))


# ---------------------------------------------------------------------------
# 模块级单例与热刷新
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_current = EntityDict().finalize()
_loaded_from_graph = False


def _fetch_rows():
    from backend.extensions import Neo4jUnavailable, run_read

    try:
        return run_read(LOAD_CYPHER, labels=LABELS)
    except Neo4jUnavailable as exc:
        log.warning("实体词典未从图谱加载（%s），使用空词典", exc.msg)
    except Exception as exc:  # noqa: BLE001 —— 启动期容错
        log.warning("实体词典加载失败：%s，使用空词典", exc)
    return None


def load():
    """从 Neo4j 加载并原子替换当前词典；返回统计信息。"""
    global _current, _loaded_from_graph
    with _lock:
        new = EntityDict()
        rows = _fetch_rows()
        for row in rows or []:
            new.add_entity(row.get("name"), row.get("label"), row.get("alias"))
        new.finalize()
        write_userdict(new)
        tokenizer.load_userdict()
        _current = new
        _loaded_from_graph = rows is not None
    stats = {"entities": new.size(), "terms": len(new.terms()), "from_graph": _loaded_from_graph}
    log.info("实体词典已加载：%s", stats)
    return stats


def reload():
    """后台实体新增 / 改名 / 改别名 / 删除后调用。"""
    return load()


def get():
    """当前生效的实体词典（reload 采用原子替换，读方无锁）。"""
    return _current


def write_userdict(entity_dict, path=tokenizer.USERDICT_PATH):
    """生成 jieba 自定义词典：每行 `词条 频次 nz`（生成文件，不手改）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for term in entity_dict.terms():
            f.write("%s %d nz\n" % (term, _USERDICT_FREQ))
