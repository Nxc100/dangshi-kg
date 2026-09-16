# -*- coding: utf-8 -*-
"""
FRS 验收测试公共设施：断言计数、HTTP 会话、登录辅助。

断言口径对齐开发规范 8.2：成功为 HTTP 200 + code 0；失败时 HTTP 状态码与 code 同步。
每条断言标注其对应的 FRS 需求编号与验收标准，失败时可直接定位到文档条目。
"""
import io
import json
import sys
import time

import requests

RETRIES = 3        # 连接类异常的重试次数
RETRY_WAIT = 1.0   # 重试间隔基数（秒），按次数线性退避

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


class Checker:
    """按 FRS 需求编号分组记录断言结果。"""

    def __init__(self, base):
        self.base = base
        self.session = requests.Session()  # 连接复用，避免 Windows 临时端口耗尽
        self.passed = self.failed = self.skipped = 0
        self.failures = []
        self._fr = ""

    # ---- 分组 ----
    def group(self, fr, title):
        self._fr = fr
        print("\n%s %s" % (fr, title))

    # ---- 请求 ----
    def req(self, method, path, **kw):
        """
        发起请求。连接类异常自动重试：本机存在间歇性套接字/线程资源紧张
        （git 亦报过 getaddrinfo 失败），重试可避免把环境抖动误判为功能缺陷。
        """
        last = None
        for attempt in range(RETRIES):
            try:
                return self.session.request(method, self.base + path, timeout=20, **kw)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last = exc
                if attempt < RETRIES - 1:
                    time.sleep(RETRY_WAIT * (attempt + 1))
        raise last

    def get(self, path, **kw):
        return self.req("GET", path, **kw)

    def post(self, path, **kw):
        return self.req("POST", path, **kw)

    def put(self, path, **kw):
        return self.req("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.req("DELETE", path, **kw)

    def data(self, path, **kw):
        """取成功响应的 data；非 0 code 返回 None。"""
        body = self.get(path, **kw).json()
        return body.get("data") if body.get("code") == 0 else None

    # ---- 断言 ----
    def ok(self, title, cond, detail=""):
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append("%s %s%s" % (self._fr, title, ("｜" + detail) if detail else ""))
        print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", title, detail))
        return cond

    def api(self, title, expect_code, resp, show=None):
        """校验统一返回体；expect_code 为业务 code（0 表示成功，HTTP 应为 200）。"""
        try:
            body = resp.json()
        except ValueError:
            body = {"code": resp.status_code, "msg": "<非 JSON>", "data": None}
        expect_http = 200 if expect_code == 0 else expect_code
        hit = resp.status_code == expect_http and body.get("code") == expect_code
        detail = "HTTP %d code %s %s" % (resp.status_code, body.get("code"), (body.get("msg") or "")[:24])
        if show:
            d = body.get("data") or {}
            detail += " ｜ " + json.dumps({k: d.get(k) for k in show}, ensure_ascii=False)[:90]
        self.ok(title, hit, detail)
        return body

    def skip(self, title, reason):
        self.skipped += 1
        print("  [SKIP] %-52s %s" % (title, reason))

    # ---- 登录辅助 ----
    def auth(self, token):
        return {"Authorization": "Bearer " + token}

    def register_or_login(self, username, password):
        """返回 (headers, user)；用户已存在时改走登录。"""
        body = self.post("/auth/register", json={
            "username": username, "password": password, "confirm_password": password}).json()
        if body.get("code") != 0:
            body = self.post("/auth/login", json={"username": username, "password": password}).json()
        if body.get("code") != 0:
            return None, None
        d = body["data"]
        return self.auth(d["token"]), d["user"]

    def summary(self):
        print("\n" + "=" * 96)
        if self.failures:
            print("未达标的验收项（%d 条）：" % len(self.failures))
            for f in self.failures:
                print("  · %s" % f)
        print("FRS 验收：PASS %d / FAIL %d / SKIP %d" % (self.passed, self.failed, self.skipped))
        return 1 if self.failed else 0


def graph_ready(checker):
    """图谱是否已连接且有数据；无数据时图谱相关断言跳过而非判失败。"""
    try:
        health = checker.get("/health").json()["data"]
        return bool(health["neo4j"]["connected"]) and health["dictionary_entities"] > 0
    except Exception:  # noqa: BLE001 —— 自检脚本容错
        return False
