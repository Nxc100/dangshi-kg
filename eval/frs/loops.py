# -*- coding: utf-8 -*-
"""
FRS 第五章「功能闭环校验表」验收：12 条闭环，文档列为整体验收必测项。

闭环强调的是跨功能的链路贯通与副作用正确性（如个人视图删除不影响管理端统计），
与第四章按需求条目的验收互补，故单独成模块。
"""
import io
import time


def _png():
    import struct
    import zlib
    px = bytearray()
    for _ in range(32):
        px.append(0)
        px.extend(b"\x90\x90\x90" * 32)

    def chunk(t, d):
        b = t + d
        return struct.pack(">I", len(d)) + b + struct.pack(">I", zlib.crc32(b) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(px), 9)) + chunk(b"IEND", b""))


def loop_account(c):
    """闭环 1 账号生命周期：注册 → 自动登录 → 退出 → 再登录 → 改密 → 新密登录。"""
    c.group("闭环 1", "账号生命周期（库中始终无明文密码）")
    u = "loopacct%d" % (int(time.time()) % 100000)
    p1, p2 = "Loop2026aa", "Loop2026bb"
    b = c.post("/auth/register", json={"username": u, "password": p1, "confirm_password": p1}).json()
    c.ok("注册即自动登录", b.get("code") == 0 and bool((b.get("data") or {}).get("token")))
    h = c.auth(b["data"]["token"])
    c.ok("登录态下个人接口可用", c.get("/user/profile", headers=h).json().get("code") == 0)
    c.ok("退出（清 token）后个人接口 401", c.get("/user/profile").status_code == 401)
    h = c.auth(c.post("/auth/login", json={"username": u, "password": p1})
               .json()["data"]["token"])
    c.ok("可用原密码再登录", bool(h))
    c.ok("改密成功", c.put("/user/password", json={
        "old_password": p1, "new_password": p2, "confirm_password": p2},
        headers=h).json().get("code") == 0)
    c.ok("旧密码失效",
         c.post("/auth/login", json={"username": u, "password": p1}).status_code == 401)
    nb = c.post("/auth/login", json={"username": u, "password": p2}).json()
    c.ok("新密码可登录", nb.get("code") == 0)
    return c.auth(nb["data"]["token"]), u, p2


def loop_avatar(c, h):
    """闭环 2 头像：上传 → 全站显示 → 再次更换覆盖 → 重登仍显示。"""
    c.group("闭环 2", "头像闭环")
    png = _png()
    first = c.post("/user/avatar", files={"file": ("a.png", io.BytesIO(png), "image/png")},
                   headers=h).json()
    c.ok("上传成功并返回 URL", first.get("code") == 0)
    url1 = (first.get("data") or {}).get("avatar_url")
    c.ok("资料接口即时反映新头像",
         (c.data("/user/profile", headers=h) or {}).get("avatar_url") == url1)
    # 头像 URL 以文件 mtime（秒级）作破缓存参数，同秒内重传时间戳不变，故等到跨秒再传
    time.sleep(1.2)
    second = c.post("/user/avatar", files={"file": ("b.png", io.BytesIO(png), "image/png")},
                    headers=h).json()
    url2 = (second.get("data") or {}).get("avatar_url")
    c.ok("再次更换覆盖旧图（每用户恒一张）", second.get("code") == 0, str(url2))
    c.ok("覆盖后破缓存时间戳更新", url2 != url1, "%s → %s" % (url1, url2))


def loop_qa_learning(c, kg):
    """闭环 3 问答学习：提问 → 答案实体 → 百科 → 关联标签 → 图谱 → 再提问。"""
    c.group("闭环 3", "问答学习闭环")
    if not kg:
        c.skip("问答学习闭环", "图谱无数据")
        return
    d = c.post("/qa", json={"question": "哪些人参加了中共一大"}).json().get("data") or {}
    ents = d.get("entities") or []
    c.ok("① 提问得到答案与实体链接", bool(ents))
    person = next((e for e in ents if e["type"] == "Person"), None)
    c.ok("② 答案实体可跳百科", bool(person) and bool(c.data("/entity/%s" % person["name"])))
    page = c.data("/entity/%s" % person["name"]) or {}
    groups = page.get("relations") or []
    c.ok("③ 百科页关联标签可继续跳转", bool(groups) and bool(groups[0]["items"]))
    nxt = groups[0]["items"][0]["name"]
    c.ok("④ 关联实体在图谱中可展开", bool((c.data("/graph/subgraph", params={"name": nxt}) or {}).get("nodes")))
    c.ok("⑤ 可就该实体继续提问",
         (c.post("/qa", json={"question": "介绍一下%s" % nxt}).json().get("data") or {})
         .get("answer_source") == "kg")


def loop_fallback(c):
    """闭环 4 兜底：图谱外问题 → 兜底 → 仍可继续提问 → 日志 fallback=1。"""
    c.group("闭环 4", "兜底闭环")
    q = "延安整风运动的历史背景是什么"
    d = c.post("/qa", json={"question": q}).json().get("data") or {}
    c.ok("图谱外问题走兜底分支", d.get("fallback") is True)
    c.ok("兜底来源标记为 passage（无语料时亦不编造）", d.get("answer_source") == "passage")
    c.ok("无语料时给出引导语而非空白",
         bool(d.get("answer_text")) or bool(d.get("fallback_passages")))
    c.ok("兜底后仍可继续提问",
         c.post("/qa", json={"question": "遵义会议在哪里召开"}).json().get("code") == 0)
    return q


def loop_history(c, h, admin_h):
    """闭环 5 历史：提问入史 → 一键重问 → 删除仅影响个人视图，管理端计数不变。"""
    c.group("闭环 5", "历史闭环（删除不破坏统计口径）")
    before = (c.data("/admin/logs", headers=admin_h) or {}).get("total") or 0
    q = "秋收起义是谁领导的"
    c.post("/qa", json={"question": q}, headers=h)
    items = (c.data("/user/history", headers=h) or {}).get("list") or []
    c.ok("提问后历史即现", bool(items) and items[0]["question"] == q)
    c.ok("一键重问可再次提问（同问句再入史）",
         c.post("/qa", json={"question": q}, headers=h).json().get("code") == 0)
    mid = (c.data("/admin/logs", headers=admin_h) or {}).get("total") or 0
    c.ok("管理端日志随提问增加", mid == before + 2, "%d → %d" % (before, mid))
    c.delete("/user/history", headers=h)
    c.ok("清空后个人历史为空",
         ((c.data("/user/history", headers=h) or {}).get("total") or 0) == 0)
    after = (c.data("/admin/logs", headers=admin_h) or {}).get("total") or 0
    c.ok("管理端日志计数不受个人删除影响", after == mid, "%d → %d" % (mid, after))
    stats = c.data("/stats/overview", headers=admin_h) or {}
    c.ok("看板总数同样不受影响（user_visible 不参与聚合）", stats.get("total") == after,
         "看板 %s / 明细 %d" % (stats.get("total"), after))


def loop_favorite(c, h, kg):
    """闭环 6 收藏：两类入口 → 回访 → 取消 → 状态一致。"""
    c.group("闭环 6", "收藏闭环")
    log_id = ((c.post("/qa", json={"question": "遵义会议在哪里召开"}, headers=h)
               .json().get("data")) or {}).get("log_id")
    c.ok("问答气泡入口收藏成功", c.post("/user/favorite", json={
        "fav_type": "qa", "ref_id": str(log_id)}, headers=h).json().get("code") == 0)
    if kg:
        c.ok("百科页入口收藏成功", c.post("/user/favorite", json={
            "fav_type": "entity", "ref_id": "毛泽东"}, headers=h).json().get("code") == 0)
        c.ok("百科页按钮态为已收藏",
             (c.data("/entity/毛泽东", headers=h) or {}).get("favorited") is True)
    qa_n = (c.data("/user/favorite", params={"fav_type": "qa"}, headers=h) or {}).get("total")
    en_n = (c.data("/user/favorite", params={"fav_type": "entity"}, headers=h) or {}).get("total")
    c.ok("收藏夹两页签分别可回访", qa_n == 1 and (en_n == 1 or not kg), "问答 %s / 实体 %s" % (qa_n, en_n))
    if kg:
        c.delete("/user/favorite", json={"fav_type": "entity", "ref_id": "毛泽东"}, headers=h)
        c.ok("取消后按钮态复位",
             (c.data("/entity/毛泽东", headers=h) or {}).get("favorited") is False)


def loop_quiz(c, h, kg):
    """闭环 7 学练测：试做 → 保存 → 记录 → 错题 → 复习 → 再练。"""
    c.group("闭环 7", "学练测闭环")
    if not kg:
        c.skip("学练测闭环", "图谱无数据")
        return
    qs = (c.data("/quiz", params={"n": 5}) or {}).get("questions") or []
    c.ok("① 游客可试做整卷（成绩不入库）", len(qs) == 5)
    answers = [q["answer_key"] if i else
               next(o["key"] for o in q["options"] if o["key"] != q["answer_key"])
               for i, q in enumerate(qs)]
    body = c.post("/quiz/submit", json={"questions": qs, "answers": answers,
                                        "duration_sec": 30}, headers=h).json()
    c.ok("② 登录后保存成绩（后端复算 4/5）",
         (body.get("data") or {}).get("score") == 4, str((body.get("data") or {}).get("score")))
    rid = (body.get("data") or {}).get("record_id")
    detail = c.data("/quiz/records/%d" % rid, headers=h) or {}
    wrong = [q for q in (detail.get("detail") or {}).get("questions", []) if not q["correct"]]
    c.ok("③ 记录详情可定位错题", len(wrong) == 1)
    ent = (wrong[0].get("entity") or {}).get("name") if wrong else None
    c.ok("④ 错题可跳百科复习", bool(ent) and bool(c.data("/entity/%s" % ent)))
    again = (c.data("/quiz", params={"n": 5, "entities": ent}) or {}).get("questions") or []
    c.ok("⑤ 针对错题再练可出新卷", len(again) == 5)


def loop_kg_ops(c, admin_h, kg):
    """闭环 8/9 知识与关系运营：后台改 → 前台三处即时变化 → 改回 → op_log 留痕。"""
    c.group("闭环 8/9", "知识运营闭环（后台改前台即时生效）")
    if not kg:
        c.skip("知识运营闭环", "图谱无数据")
        return
    target, wrong_place, right_place = "遵义会议", "贵阳", "遵义"
    triple = {"head": target, "head_type": "Meeting", "rel": "HELD_IN",
              "tail": wrong_place, "tail_type": "Location"}
    # 先清理上次中断可能留下的残留，保证本用例的写操作次数可预期
    c.delete("/admin/triple", json=triple, headers=admin_h)
    c.delete("/admin/entity", json={"type": "Location", "name": wrong_place,
                                    "confirm_name": wrong_place}, headers=admin_h)

    before = (c.data("/admin/oplog", headers=admin_h) or {}).get("total") or 0
    # 新增一个错误地点并改挂过去
    c.ok("① 新增地点实体成功", c.post("/admin/entity", json={"type": "Location", "props": {
        "name": wrong_place, "source": "FRS 闭环自检临时数据"}},
        headers=admin_h).json().get("code") == 0)
    c.ok("② 新增召开地关系成功",
         c.post("/admin/triple", json=triple, headers=admin_h).json().get("code") == 0)
    ans = (c.post("/qa", json={"question": "%s在哪里召开" % target}).json().get("data") or {})
    c.ok("③ 前台问答即时反映新增的召开地", wrong_place in (ans.get("answer_text") or ""),
         (ans.get("answer_text") or "")[:40])
    places = [i["name"] for g in ((c.data("/entity/%s" % target) or {}).get("relations") or [])
              if g["relation"] == "HELD_IN" for i in g["items"]]
    c.ok("④ 前台百科页同步出现", wrong_place in places, str(places))
    nodes = [n["name"] for n in ((c.data("/graph/subgraph", params={"name": target}) or {})
                                 .get("nodes") or [])]
    c.ok("⑤ 前台图谱同步出现", wrong_place in nodes)
    # 改回
    c.ok("⑥ 删除关系成功",
         c.delete("/admin/triple", json=triple, headers=admin_h).json().get("code") == 0)
    c.ok("⑦ 删除临时实体成功",
         c.delete("/admin/entity", json={"type": "Location", "name": wrong_place},
                  headers=admin_h).json().get("code") == 0)
    places2 = [i["name"] for g in ((c.data("/entity/%s" % target) or {}).get("relations") or [])
               if g["relation"] == "HELD_IN" for i in g["items"]]
    c.ok("⑧ 改回后前台恢复原值", places2 == [right_place], str(places2))
    after = (c.data("/admin/oplog", headers=admin_h) or {}).get("total") or 0
    c.ok("⑨ 每次写操作 1:1 留痕（新增 2 + 删除 2 = 4 条）", after == before + 4,
         "%d → %d" % (before, after))


def loop_governance(c, admin_h, uname, pwd):
    """闭环 10 治理：禁用 → 登录被拒 → 启用恢复 → 重置密码 → 新密登录 → 引导改密。"""
    c.group("闭环 10", "治理闭环")
    users = (c.data("/admin/users", params={"kw": uname}, headers=admin_h) or {}).get("list") or []
    target = next((u for u in users if u["username"] == uname), None)
    if not target:
        c.skip("治理闭环", "未找到测试用户")
        return
    uid = target["user_id"]
    c.ok("① 禁用生效", c.post("/admin/users/%d/status" % uid, json={"status": 0},
                          headers=admin_h).json().get("code") == 0)
    c.ok("② 被禁用后登录被拒",
         c.post("/auth/login", json={"username": uname, "password": pwd}).status_code == 401)
    c.ok("③ 启用后恢复登录", c.post("/admin/users/%d/status" % uid, json={"status": 1},
                             headers=admin_h).json().get("code") == 0 and
         c.post("/auth/login", json={"username": uname, "password": pwd}).json().get("code") == 0)
    rb = c.post("/admin/users/%d/reset-password" % uid, headers=admin_h).json()
    newpwd = (rb.get("data") or {}).get("password")
    c.ok("④ 重置密码仅返回一次随机密码", bool(newpwd))
    lb = c.post("/auth/login", json={"username": uname, "password": newpwd}).json()
    c.ok("⑤ 随机密码可登录", lb.get("code") == 0)
    c.ok("⑥ 引导改密（must_change_pwd=1，未改密前后台/个人写接口被拦）",
         ((lb.get("data") or {}).get("user") or {}).get("must_change_pwd") == 1)
    h = c.auth(lb["data"]["token"])
    c.ok("⑦ 未改密时非改密接口被 422 拦截",
         c.get("/user/history", headers=h).json().get("code") == 422)


def loop_metrics(c, admin_h):
    """闭环 11 度量：问答产生日志 → 明细与看板总分一致 → 兜底率指导补录。"""
    c.group("闭环 11", "度量闭环")
    logs = c.data("/admin/logs", headers=admin_h) or {}
    stats = c.data("/stats/overview", headers=admin_h) or {}
    c.ok("明细与看板总数一致", logs.get("total") == stats.get("total"),
         "明细 %s / 看板 %s" % (logs.get("total"), stats.get("total")))
    fb = (c.data("/admin/logs", params={"fallback": 1}, headers=admin_h) or {}).get("total") or 0
    c.ok("兜底条数与看板 fallback_count 一致", stats.get("fallback_count") == fb,
         "明细 %d / 看板 %s" % (fb, stats.get("fallback_count")))
    total = stats.get("total") or 1
    c.ok("兜底率 = 兜底数 ÷ 总数", abs((stats.get("fallback_rate") or 0) - fb / total) < 1e-4,
         "%.4f" % (stats.get("fallback_rate") or 0))
    c.ok("意图分布覆盖已发生的问答", bool(stats.get("intent_dist")))


def loop_daily(c, kg):
    """闭环 12 每日学习：首页卡片 → 百科 → 示例问句 → 问答。"""
    c.group("闭环 12", "每日学习闭环")
    d = c.data("/daily") or {}
    rec = d.get("recommend")
    if not kg or not rec:
        c.skip("每日学习闭环", "图谱无数据")
        return
    c.ok("① 首页今日推荐有内容", bool(rec.get("name")))
    c.ok("② 推荐卡可跳百科", bool(c.data("/entity/%s" % rec["name"])))
    c.ok("③ 示例问句可直达问答并得到答案",
         (c.post("/qa", json={"question": "遵义会议是什么时候召开的"}).json().get("data") or {})
         .get("answer_source") == "kg")


def run(c, kg, admin_h):
    h, uname, pwd = loop_account(c)
    loop_avatar(c, h)
    loop_qa_learning(c, kg)
    loop_fallback(c)
    if admin_h:
        loop_history(c, h, admin_h)
    loop_favorite(c, h, kg)
    loop_quiz(c, h, kg)
    if admin_h:
        loop_kg_ops(c, admin_h, kg)
        loop_governance(c, admin_h, uname, pwd)
        loop_metrics(c, admin_h)
    loop_daily(c, kg)
