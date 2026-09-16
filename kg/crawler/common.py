# -*- coding: utf-8 -*-
"""
采集公共工具（V3 3.1 / FRS 3.1 采集纪律 / 开发规范 7.3）——五个采集脚本共用。

纪律（无例外）：
- 只采 DR-01~DR-05 权威官方公开静态页；不安装 Playwright / Selenium；
- 请求间隔 ≥ 2 秒、常规浏览器 UA；
- 原始 HTML 全量留档 data/raw/（解析可离线重跑，不二次抓取）；
- 断点续爬 done.txt；每条入库知识记 source（来源 URL）；
- 人民网系页面显式 GBK 解码，全文统一 UTF-8 落盘。
"""
import hashlib
import logging
import os
import time
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW_DIR = os.path.join(_ROOT, "data", "raw")
DONE_FILE = os.path.join(RAW_DIR, "done.txt")

MIN_INTERVAL = 2.0  # 请求间隔 ≥ 2 秒
TIMEOUT = 20
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
# 人民网系页面为 GB2312/GBK 编码，须显式指定，否则乱码
GBK_HOSTS = ("people.com.cn", "cpc.people.com.cn", "dangshi.people.com.cn")

_last_request_at = 0.0


def _sleep_gap():
    global _last_request_at
    gap = MIN_INTERVAL - (time.time() - _last_request_at)
    if gap > 0:
        time.sleep(gap)
    _last_request_at = time.time()


def encoding_for(url, default="utf-8"):
    host = (urlparse(url).hostname or "").lower()
    return "gbk" if any(host.endswith(h) for h in GBK_HOSTS) else default


def raw_path(url, subdir=""):
    """留档文件名：域名 + URL 短哈希，避免路径过长与非法字符。"""
    host = (urlparse(url).hostname or "unknown").replace(".", "_")
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    folder = os.path.join(RAW_DIR, subdir) if subdir else RAW_DIR
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "%s_%s.html" % (host, digest))


def load_done():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def mark_done(url):
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def fetch(url, subdir="", encoding=None, force=False):
    """
    抓取并留档，返回 HTML 文本（UTF-8 str）。
    已留档且未 force 时直接读本地文件（解析可离线重跑，不二次抓取）。
    """
    path = raw_path(url, subdir)
    if os.path.exists(path) and not force:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    _sleep_gap()
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.encoding = encoding or encoding_for(url)
    html = resp.text
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    mark_done(url)
    log.info("已抓取并留档：%s -> %s", url, os.path.basename(path))
    return html


def soup(html):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "lxml")


def write_csv(path, rows, fieldnames):
    """清洗产物统一 utf-8-sig 落盘，Excel 直接打开无乱码。"""
    import csv

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    log.info("已写出 %d 行 -> %s", len(rows), path)
    return len(rows)
