# -*- coding: utf-8 -*-
"""
接口回归自检（开发规范 3 节"最少回归清单"、9.1 安全与越权用例的可执行版）。

覆盖：统一返回体与状态码同步、游客接口、问答管道边界（纯符号 / 超长 / 注入）、鉴权三档、
注册登录与首登强制改密、幂等收藏、用户治理闭环、日志导出编码、本体约束拦截。
图谱相关断言在 Neo4j 未连接时自动跳过并计入 SKIP，不判为失败。

前置：后端已启动（python -m backend.app）；建议先重置为空白库（删除 backend/app.db 后 python -m backend.init_db）。
用法（项目根目录）：python -m eval.selfcheck_api [管理员初始密码]
  管理员初始密码缺省取 backend/.env 的 ADMIN_INIT_PASSWORD。
退出码 0 表示全部通过。
"""
import io
import json
import os
import sys

import requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from backend.config import Config  # noqa: E402

BASE = os.environ.get("API_BASE") or "http://127.0.0.1:%d/api" % Config.PORT
TEST_USER = {"username": "selfcheck01", "password": "Selfcheck2026", "confirm_password": "Selfcheck2026"}
NEW_ADMIN_PWD = "Selfcheck2026"
INJECTION = "遵义会议'}) DETACH DELETE (n) //"

session = requests.Session()  # 连接复用，避免 Windows 临时端口耗尽


class Checker:
    def __init__(self):
        self.passed = self.failed = self.skipped = 0

    def check(self, title, expect_code, resp, show=None):
        """expect_code 为业务 code；规范 8.2 要求 HTTP 状态码与 code 同步（成功为 HTTP 200 + code 0）。"""
        try:
            body = resp.json()
        except ValueError:
            body = {"code": resp.status_code, "msg": "<非 JSON 响应>", "data": None}
        expect_http = 200 if expect_code == 0 else expect_code
        hit = resp.status_code == expect_http and body.get("code") == expect_code
        if hit:
            self.passed += 1
        else:
            self.failed += 1
        detail = ""
        if show:
            data = body.get("data") or {}
            detail = " | " + json.dumps({k: data.get(k) for k in show}, ensure_ascii=False)[:150]
        print("[%s] %-44s HTTP %-3d code %-3s %s%s"
              % ("PASS" if hit else "FAIL", title, resp.status_code, body.get("code"),
                 (body.get("msg") or "")[:30], detail))
        return body

    def skip(self, title, reason):
        self.skipped += 1
        print("[SKIP] %-44s %s" % (title, reason))


def graph_ready():
    try:
        return session.get(BASE + "/health", timeout=5).json()["data"]["neo4j"]["connected"]
    except Exception:  # noqa: BLE001 —— 自检脚本容错
        return False


def guest_section(c, kg):
    print("一、游客可用接口（规范 6.1 鉴权第一档）")
    c.check("GET /config 只返回 llm_available", 0, session.get(BASE + "/config"), ["llm_available"])
    c.check("GET /daily", 0, session.get(BASE + "/daily"), ["recommend", "today_events"])
    body = c.check("GET /timeline 无参返回时期列表", 0, session.get(BASE + "/timeline"), ["period"])
    periods = (body.get("data") or {}).get("periods") or []
    c.check("时间轴七个历史时期齐备", 0 if len(periods) == 7 else 500,
            _fake(200 if len(periods) == 7 else 500), None)
    c.check("GET /graph/search", 0, session.get(BASE + "/graph/search", params={"kw": "会议"}))
    c.check("GET /graph/search 空关键词 → 422", 422, session.get(BASE + "/graph/search", params={"kw": ""}))
    if not kg:
        c.skip("GET /entity/<name>", "Neo4j 未连接")


class _fake:
    """把纯断言包装成 check 可识别的响应对象。"""

    def __init__(self, status):
        self.status_code = status

    def json(self):
        return {"code": 0 if self.status_code == 200 else 500, "msg": "断言", "data": None}


def qa_section(c):
    print("\n二、问答管道与三类边界（规范 6.3，边界均为 code=0 业务响应）")
    c.check("POST /qa 正常问句", 0, session.post(BASE + "/qa", json={"question": "遵义会议在哪里召开"}),
            ["intent", "fallback", "answer_source", "log_id"])
    c.check("POST /qa 纯符号 → 422", 422, session.post(BASE + "/qa", json={"question": "？？？"}))
    c.check("POST /qa 空白 → 422", 422, session.post(BASE + "/qa", json={"question": "   "}))
    c.check("POST /qa 超 100 字 → 422", 422, session.post(BASE + "/qa", json={"question": "党" * 101}))
    c.check("POST /qa Cypher 注入样例无破坏", 0, session.post(BASE + "/qa", json={"question": INJECTION}),
            ["intent", "fallback"])


def auth_section(c):
    print("\n三、鉴权三档与账号生命周期（规范 6.1 / 6.2）")
    for path in ("/user/profile", "/stats/overview", "/admin/overview"):
        c.check("游客访问 %s → 401" % path, 401, session.get(BASE + path))

    r = session.post(BASE + "/auth/register", json=TEST_USER)
    if r.status_code == 422:
        r = session.post(BASE + "/auth/login",
                         json={"username": TEST_USER["username"], "password": TEST_USER["password"]})
    body = c.check("注册（或登录）普通用户并自动登录", 0, r, ["token"])
    headers = {"Authorization": "Bearer " + body["data"]["token"]}

    c.check("用户名唯一性预检", 0, session.get(BASE + "/auth/check",
                                        params={"username": TEST_USER["username"]}), ["available"])
    c.check("弱密码注册 → 422", 422, session.post(BASE + "/auth/register", json={
        "username": "weakpwd01", "password": "abcdefgh", "confirm_password": "abcdefgh"}))
    c.check("两次密码不一致 → 422", 422, session.post(BASE + "/auth/register", json={
        "username": "mismatch01", "password": "Test12345", "confirm_password": "Test99999"}))
    c.check("错误密码登录 → 401", 401, session.post(BASE + "/auth/login", json={
        "username": TEST_USER["username"], "password": "WrongPwd123"}))
    c.check("GET /user/profile 已登录", 0, session.get(BASE + "/user/profile", headers=headers),
            ["username", "role", "avatar_url"])
    c.check("PUT /user/profile 改昵称", 0,
            session.put(BASE + "/user/profile", json={"nickname": "自检用户"}, headers=headers), ["nickname"])
    c.check("昵称超长 → 422", 422,
            session.put(BASE + "/user/profile", json={"nickname": "长" * 20}, headers=headers))
    c.check("收藏实体", 0, session.post(BASE + "/user/favorite",
                                    json={"fav_type": "entity", "ref_id": "遵义会议"}, headers=headers))
    c.check("重复收藏幂等（规范 7.2）", 0, session.post(BASE + "/user/favorite",
                                              json={"fav_type": "entity", "ref_id": "遵义会议"}, headers=headers))
    fav = session.get(BASE + "/user/favorite", params={"fav_type": "entity"}, headers=headers).json()
    total = (fav.get("data") or {}).get("total")
    c.check("幂等后收藏仅 1 条", 0 if total == 1 else 500, _fake(200 if total == 1 else 500))
    c.check("取消收藏", 0, session.delete(BASE + "/user/favorite",
                                      json={"fav_type": "entity", "ref_id": "遵义会议"}, headers=headers))
    for path in ("/admin/overview", "/stats/overview"):
        c.check("普通用户访问 %s → 403" % path, 403, session.get(BASE + path, headers=headers))
    return headers


def admin_section(c, admin_pwd):
    print("\n四、管理员：首登强制改密与后台接口（规范 6.1 / 6.2 / 6.7 / 6.8）")
    r = session.post(BASE + "/auth/login", json={"username": "admin", "password": admin_pwd})
    if r.status_code != 200:
        c.check("admin 登录", 0, r)
        print("      admin 密码不匹配，跳过后台断言（请传入正确的初始密码）")
        return None
    body = c.check("admin 登录", 0, r, ["token"])
    headers = {"Authorization": "Bearer " + body["data"]["token"]}
    must_change = body["data"]["user"]["must_change_pwd"]

    if must_change:
        c.check("未改密访问后台 → 422 拦截", 422, session.get(BASE + "/admin/overview", headers=headers))
        c.check("未改密仍可访问改密页数据", 0, session.get(BASE + "/user/profile", headers=headers))
        c.check("修改初始密码", 0, session.put(BASE + "/user/password", json={
            "old_password": admin_pwd, "new_password": NEW_ADMIN_PWD,
            "confirm_password": NEW_ADMIN_PWD}, headers=headers))
        body = c.check("新密码登录", 0, session.post(BASE + "/auth/login", json={
            "username": "admin", "password": NEW_ADMIN_PWD}), ["token"])
        headers = {"Authorization": "Bearer " + body["data"]["token"]}
        c.check("旧密码登录 → 401", 401, session.post(BASE + "/auth/login", json={
            "username": "admin", "password": admin_pwd}))
    else:
        c.skip("首登强制改密链路", "admin 已改过密码（重置空白库后可完整验证）")

    c.check("GET /admin/overview", 0, session.get(BASE + "/admin/overview", headers=headers),
            ["entity_count", "relation_count", "user_count", "today_qa_count"])
    c.check("GET /stats/overview", 0, session.get(BASE + "/stats/overview", headers=headers),
            ["total", "fallback_rate", "llm"])
    c.check("GET /admin/users", 0, session.get(BASE + "/admin/users", headers=headers), ["total"])
    c.check("GET /admin/logs", 0, session.get(BASE + "/admin/logs", headers=headers), ["total"])
    c.check("GET /admin/oplog", 0, session.get(BASE + "/admin/oplog", headers=headers), ["total"])

    export = session.get(BASE + "/admin/logs/export", headers=headers)
    bom = export.content[:3] == b"\xef\xbb\xbf"
    c.check("导出 CSV 为 utf-8-sig（Excel 无乱码）", 0 if (export.status_code == 200 and bom) else 500,
            _fake(200 if (export.status_code == 200 and bom) else 500))

    print("\n五、本体约束与用户治理拦截（规范 6.7 / 6.1）")
    c.check("非法实体类型 → 422", 422, session.post(BASE + "/admin/entity", json={
        "type": "NotALabel", "props": {"name": "x"}}, headers=headers))
    c.check("非法头尾组合 → 422", 422, session.post(BASE + "/admin/triple", json={
        "head": "毛泽东", "head_type": "Person", "rel": "HELD_IN",
        "tail": "遵义", "tail_type": "Location"}, headers=headers))
    c.check("自指关系 → 422", 422, session.post(BASE + "/admin/triple", json={
        "head": "八路军", "head_type": "Organization", "rel": "REORGANIZED_TO",
        "tail": "八路军", "tail_type": "Organization"}, headers=headers))
    c.check("非白名单关系类型 → 422", 422, session.post(BASE + "/admin/triple", json={
        "head": "毛泽东", "head_type": "Person", "rel": "DROP_ALL",
        "tail": "遵义会议", "tail_type": "Meeting"}, headers=headers))
    c.check("admin 不能禁用自己 → 422", 422,
            session.post(BASE + "/admin/users/1/status", json={"status": 0}, headers=headers))
    c.check("admin 不能改自己的角色 → 422", 422,
            session.post(BASE + "/admin/users/1/role", json={"role": "user"}, headers=headers))
    return headers


def quiz_section(c, kg):
    print("\n六、测验（规范 6.6）")
    c.check("GET /quiz?n=7 → 422", 422, session.get(BASE + "/quiz", params={"n": 7}))
    c.check("POST /quiz/submit 游客 → 401", 401,
            session.post(BASE + "/quiz/submit", json={"questions": [], "answers": []}))
    if kg:
        c.check("GET /quiz 出题", 0, session.get(BASE + "/quiz", params={"n": 5}), ["questions"])
    else:
        c.skip("GET /quiz 出题", "Neo4j 未连接，核心池不可用")


def main():
    admin_pwd = sys.argv[1] if len(sys.argv) > 1 else (Config.ADMIN_INIT_PASSWORD or "")
    try:
        session.get(BASE + "/health", timeout=5)
    except requests.RequestException:
        print("后端未启动：%s 不可达。请先运行 python -m backend.app" % BASE)
        return 2

    kg = graph_ready()
    print("=" * 100)
    print("接口回归自检  目标 %s  图数据库 %s" % (BASE, "已连接" if kg else "未连接（图谱相关断言跳过）"))
    print("=" * 100)
    c = Checker()
    guest_section(c, kg)
    qa_section(c)
    auth_section(c)
    admin_section(c, admin_pwd)
    quiz_section(c, kg)
    print("=" * 100)
    print("汇总：PASS %d / FAIL %d / SKIP %d" % (c.passed, c.failed, c.skipped))
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
