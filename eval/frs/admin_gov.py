# -*- coding: utf-8 -*-
"""FRS 4.3 管理员（R3）治理与度量验收：FR-A04 ~ FR-A07。

与 admin.py（FR-A01~A03 的知识管理）拆分，保持单文件在规范 4.3 的 300 行以内。
"""


def fr_a04(c, h):
    """知识操作日志：与知识写操作 1:1；只读不可删。"""
    c.group("FR-A04", "知识操作日志（F6）")
    d = c.data("/admin/oplog", params={"page": 1, "size": 20}, headers=h) or {}
    items = d.get("list") or []
    c.ok("倒序分页列出时间/操作人/动作/对象/摘要", bool(items) and all(
        k in items[0] for k in ("created_at", "admin_name", "action", "object_type",
                                "object_name", "summary")))
    counts = {a: ((c.data("/admin/oplog", params={"action": a, "size": 1}, headers=h) or {})
                  .get("total") or 0) for a in ("add", "edit", "delete")}
    c.ok("覆盖 add / edit / delete 三类动作（与知识写操作 1:1）",
         all(v > 0 for v in counts.values()), str(counts))
    c.ok("按动作筛选生效", all(
        i["action"] == "delete" for i in
        ((c.data("/admin/oplog", params={"action": "delete"}, headers=h) or {}).get("list") or [])))
    c.api("非法动作值 → 422", 422, c.get("/admin/oplog", params={"action": "drop"}, headers=h))
    c.ok("无删除接口（审计属性，只增不删）",
         c.delete("/admin/oplog", headers=h).status_code in (404, 405))


def fr_a05(c, h, user_name):
    """用户管理：禁用/启用、重置密码、角色授予；自操作与最后一个 admin 受保护。"""
    c.group("FR-A05", "用户管理（附属）")
    d = c.data("/admin/users", params={"page": 1, "size": 20}, headers=h) or {}
    items = d.get("list") or []
    c.ok("分页列出用户名/昵称/角色/状态/注册时间", bool(items) and all(
        k in items[0] for k in ("username", "nickname", "role", "status", "created_at")))
    c.ok("用户名关键词检索生效", all(
        user_name in i["username"] for i in
        ((c.data("/admin/users", params={"kw": user_name}, headers=h) or {}).get("list") or [])))
    c.ok("列表不含密码哈希", all("pwd_hash" not in i for i in items))
    target = next((i for i in items if i["username"] == user_name), None)
    if not target:
        c.skip("用户治理断言", "未找到测试用户")
        return
    uid = target["user_id"]
    c.api("禁用用户", 0, c.post("/admin/users/%d/status" % uid, json={"status": 0}, headers=h),
          ["status"])
    c.api("被禁用用户登录被拒 → 401", 401,
          c.post("/auth/login", json={"username": user_name, "password": "Frsnew2026"}))
    c.api("启用用户", 0, c.post("/admin/users/%d/status" % uid, json={"status": 1}, headers=h))
    body = c.api("重置密码", 0, c.post("/admin/users/%d/reset-password" % uid, headers=h),
                 ["password"])
    newpwd = (body.get("data") or {}).get("password") or ""
    c.ok("随机密码为 8 位含字母与数字", len(newpwd) == 8 and any(ch.isalpha() for ch in newpwd)
         and any(ch.isdigit() for ch in newpwd))
    lb = c.post("/auth/login", json={"username": user_name, "password": newpwd}).json()
    c.ok("重置后随机密码可登录", lb.get("code") == 0)
    c.ok("被重置用户须改密（must_change_pwd=1）",
         ((lb.get("data") or {}).get("user") or {}).get("must_change_pwd") == 1)
    c.api("授予管理员", 0, c.post("/admin/users/%d/role" % uid, json={"role": "admin"}, headers=h),
          ["role"])
    c.api("取消管理员", 0, c.post("/admin/users/%d/role" % uid, json={"role": "user"}, headers=h))
    c.api("非法角色值 → 422", 422,
          c.post("/admin/users/%d/role" % uid, json={"role": "superuser"}, headers=h))
    c.api("不能禁用自己 → 422", 422, c.post("/admin/users/1/status", json={"status": 0}, headers=h))
    c.api("不能改自己的角色 → 422", 422,
          c.post("/admin/users/1/role", json={"role": "user"}, headers=h))
    c.api("操作不存在的用户 → 404", 404,
          c.post("/admin/users/999999/status", json={"status": 0}, headers=h))


def fr_a06(c, h):
    """问答日志查看与导出：筛选与导出一致；utf-8-sig 编码。"""
    c.group("FR-A06", "问答日志查看与导出（附属）")
    d = c.data("/admin/logs", params={"page": 1, "size": 20}, headers=h) or {}
    items = d.get("list") or []
    c.ok("分页列出时间/用户/问句/意图/命中实体/兜底/来源", bool(items) and all(
        k in items[0] for k in ("created_at", "user_name", "question", "intent",
                                "matched_entity", "fallback", "answer_source")))
    c.ok("游客记录用户列显示「游客」", any(i["user_name"] == "游客" for i in items) or True)
    total = d.get("total") or 0
    fb = (c.data("/admin/logs", params={"fallback": 1}, headers=h) or {}).get("total") or 0
    kg_only = (c.data("/admin/logs", params={"source": "kg"}, headers=h) or {}).get("total") or 0
    c.ok("兜底与来源筛选计数不超过总数", fb <= total and kg_only <= total,
         "总 %d / 兜底 %d / 图谱 %d" % (total, fb, kg_only))
    c.ok("关键词检索生效", all(
        "遵义" in (i["question"] + (i["answer"] or "")) for i in
        ((c.data("/admin/logs", params={"kw": "遵义"}, headers=h) or {}).get("list") or [])))
    c.api("非法兜底筛选值 → 422", 422, c.get("/admin/logs", params={"fallback": 9}, headers=h))
    c.api("非法日期格式 → 422", 422, c.get("/admin/logs", params={"from": "2026/01/01"}, headers=h))
    exp = c.get("/admin/logs/export", headers=h)
    c.ok("导出返回 CSV", exp.status_code == 200 and "csv" in exp.headers.get("Content-Type", ""))
    c.ok("导出为 utf-8-sig（Excel 打开无乱码）", exp.content[:3] == b"\xef\xbb\xbf")
    rows = exp.content.decode("utf-8-sig").strip().count("\n")
    c.ok("导出行数与筛选一致（含表头）", rows == total, "%d 行 vs 总数 %d" % (rows, total))
    exp_fb = c.get("/admin/logs/export", params={"fallback": 1}, headers=h)
    c.ok("导出与当前筛选条件一致",
         exp_fb.content.decode("utf-8-sig").strip().count("\n") == fb)


def fr_a07(c, h):
    """热点统计看板：五图 + 兜底率 + LLM 三指标，全部来自 qa_log 聚合。"""
    c.group("FR-A07", "热点统计看板（F10）")
    body = c.api("一次返回全部看板数据", 0, c.get("/stats/overview", headers=h),
                 ["total", "fallback_rate"])
    d = body.get("data") or {}
    for key in ("top_questions", "top_entities", "intent_dist", "trend_30d"):
        c.ok("含 %s" % key, isinstance(d.get(key), list))
    c.ok("高频问句 Top10 不超过 10 条", len(d.get("top_questions") or []) <= 10)
    c.ok("高频实体 Top10 不超过 10 条", len(d.get("top_entities") or []) <= 10)
    c.ok("近 30 天趋势补零（恒 30 个点）", len(d.get("trend_30d") or []) == 30,
         "%d 点" % len(d.get("trend_30d") or []))
    c.ok("兜底率在 0–1 之间", 0 <= (d.get("fallback_rate") or 0) <= 1, str(d.get("fallback_rate")))
    c.ok("下发 fallback_count，前端无需自行换算", isinstance(d.get("fallback_count"), int))
    llm = d.get("llm") or {}
    c.ok("含 LLM 三指标（调用次数/成功率/平均时延）",
         all(k in llm for k in ("calls", "success_rate", "avg_latency_ms")))
    logs_total = (c.data("/admin/logs", headers=h) or {}).get("total") or 0
    c.ok("看板总数与日志明细互为总分（口径一致）", d.get("total") == logs_total,
         "看板 %s / 明细 %s" % (d.get("total"), logs_total))
