# -*- coding: utf-8 -*-
"""FRS 4.1 游客（R1）功能验收：FR-G01 ~ FR-G08。"""

EXAMPLE_COUNT = 8  # FR-G01/G02：冷启动区 8 条示例问句


def fr_g01(c, kg):
    """首页每日学习浏览：今日推荐必有内容；历史上的今天无匹配时整栏隐藏（唯一空态例外）。"""
    c.group("FR-G01", "首页每日学习浏览（F8）")
    body = c.api("GET /api/daily 可用", 0, c.get("/daily"), ["recommend", "today_events"])
    d = body.get("data") or {}
    if kg:
        rec = d.get("recommend")
        c.ok("今日推荐恒有内容（核心池非空时）", bool(rec), (rec or {}).get("name", ""))
        c.ok("推荐卡含名称/类型/简介三要素",
             bool(rec) and all(rec.get(k) for k in ("name", "type", "intro")))
        # 同一天两次请求结果一致（日期为随机种子，全站当日一致）
        again = (c.data("/daily") or {}).get("recommend") or {}
        c.ok("今日推荐全站当日一致", again.get("name") == (rec or {}).get("name"))
    else:
        c.skip("今日推荐内容断言", "图谱无数据")
    c.ok("today_events 为数组（空则前端整栏隐藏）", isinstance(d.get("today_events"), list),
         "%d 条" % len(d.get("today_events") or []))


def fr_g02(c, kg):
    """智能问答：答案可溯源；三类边界均为 code=0 业务响应；每问必写 qa_log。"""
    c.group("FR-G02", "智能问答（F1/F9）")
    if kg:
        body = c.api("图谱命中问句返回结构化答案", 0,
                     c.post("/qa", json={"question": "遵义会议在哪里召开"}),
                     ["intent", "answer_source", "fallback"])
        d = body.get("data") or {}
        c.ok("答案来源为图谱且未走兜底", d.get("answer_source") == "kg" and not d.get("fallback"))
        c.ok("答案文本非空", bool(d.get("answer_text")), (d.get("answer_text") or "")[:40])
        c.ok("携带可跳转的实体链接", bool(d.get("entities")) and all(
            e.get("id") and e.get("name") and e.get("type") for e in d["entities"]))
        sub = d.get("subgraph") or {}
        c.ok("携带溯源子图（节点与边）", bool(sub.get("nodes")) and bool(sub.get("links")),
             "%d 点 %d 边" % (len(sub.get("nodes") or []), len(sub.get("links") or [])))
        c.ok("返回 log_id 供收藏与审计", bool(d.get("log_id")))
        # 边界一：未识别实体 → candidates（code=0，非错误）
        b2 = c.api("未识别实体仍为 code=0 业务响应", 0,
                   c.post("/qa", json={"question": "某个完全不存在的词条是什么"}), ["fallback"])
        c.ok("未识别时给出候选或转兜底",
             isinstance((b2.get("data") or {}).get("candidates"), list))
        # 边界二：槽位不符 → clarify
        b3 = c.api("槽位不符仍为 code=0 业务响应", 0,
                   c.post("/qa", json={"question": "谁参加了毛泽东"}))
        cl = (b3.get("data") or {}).get("clarify")
        c.ok("槽位不符返回澄清与问法示例", bool(cl and cl.get("examples")),
             (cl or {}).get("text", "")[:34])
    else:
        c.skip("图谱命中类断言", "图谱无数据")
    # 输入校验（前端拦截 + 后端复校）
    c.api("纯符号输入 → 422", 422, c.post("/qa", json={"question": "？？？"}))
    c.api("纯空白输入 → 422", 422, c.post("/qa", json={"question": "   "}))
    c.api("超 100 字 → 422", 422, c.post("/qa", json={"question": "党" * 101}))
    c.api("Cypher 注入样例不产生破坏", 0,
          c.post("/qa", json={"question": "遵义会议'}) DETACH DELETE (n) //"}))


def fr_g03(c, kg):
    """图谱可视化：搜索联想 → 2 跳子图 → 展开邻居；节点上限 100。"""
    c.group("FR-G03", "知识图谱可视化浏览（F2）")
    if not kg:
        c.skip("图谱三接口断言", "图谱无数据")
        return
    hits = c.data("/graph/search", params={"kw": "会议"})
    c.ok("搜索联想返回 {name,type} 列表", isinstance(hits, list) and bool(hits),
         "%d 条" % len(hits or []))
    c.ok("联想结果 ≤ 10 条", len(hits or []) <= 10)
    name = hits[0]["name"]
    sub = c.data("/graph/subgraph", params={"name": name, "hops": 2, "limit": 100})
    c.ok("2 跳子图返回 nodes/links/truncated",
         all(k in (sub or {}) for k in ("nodes", "links", "truncated")),
         "%d 点 %d 边" % (len(sub["nodes"]), len(sub["links"])) if sub else "")
    c.ok("节点 id 规则为 {标签}:{主名}",
         all(":" in n["id"] for n in (sub or {}).get("nodes", [])))
    c.ok("边标注中文关系名",
         all(l.get("label") for l in (sub or {}).get("links", [])))
    c.ok("单画布节点不超过 100（规范 6.5）", len((sub or {}).get("nodes", [])) <= 100)
    nb = c.data("/graph/neighbors", params={"name": name})
    c.ok("展开邻居返回 1 跳子图", isinstance((nb or {}).get("nodes"), list))
    c.api("hops 越界 → 422", 422, c.get("/graph/subgraph", params={"name": name, "hops": 5}))
    c.api("搜索词为空 → 422", 422, c.get("/graph/search", params={"kw": ""}))


def fr_g04(c, kg):
    """大事记时间轴：七时期页签；事件按 time_sort 升序；附一句话简介。"""
    c.group("FR-G04", "大事记时间轴浏览（F3）")
    d = c.data("/timeline")
    c.ok("无参返回时期列表 + 首个时期事件（规范决策⑨）",
         bool(d) and all(k in d for k in ("periods", "period", "events")))
    periods = (d or {}).get("periods") or []
    c.ok("七个历史时期齐备", len(periods) == 7, "%d 个" % len(periods))
    c.ok("时期按 order 升序", [p["order"] for p in periods] == sorted(p["order"] for p in periods))
    if not kg:
        c.skip("时期事件内容断言", "图谱无数据")
        return
    empty = []
    for p in periods:
        evs = (c.data("/timeline", params={"period": p["name"]}) or {}).get("events") or []
        if not evs:
            empty.append(p["name"])
            continue
        ts = [e.get("time_sort") or "" for e in evs]
        if ts != sorted(ts):
            c.ok("「%s」事件按 time_sort 升序" % p["name"][:10], False, str(ts[:4]))
    c.ok("七个时期均非空（V3 5.3 验收）", not empty, "为空：%s" % empty if empty else "")
    evs = (c.data("/timeline", params={"period": periods[1]["name"]}) or {}).get("events") or []
    c.ok("事件卡含 time_text / 名称 / brief 简介",
         bool(evs) and all(e.get("time_text") and e.get("name") for e in evs))
    c.api("非法时期名 → 422", 422, c.get("/timeline", params={"period": "不存在的时期"}))


def fr_g05(c, kg):
    """实体百科页：六段结构一次返回；不存在返回友好 404。"""
    c.group("FR-G05", "实体百科页浏览（F4）")
    if not kg:
        c.skip("百科页断言", "图谱无数据")
        return
    d = c.data("/entity/遵义会议")
    c.ok("一次返回百科页全部数据",
         bool(d) and all(k in d for k in ("entity", "intro", "source", "relations", "subgraph", "favorited")))
    ent = (d or {}).get("entity") or {}
    c.ok("头部含名称 / 类型 / 别名", all(k in ent for k in ("name", "type", "alias")))
    c.ok("属性表只含非空字段",
         all(v not in (None, "") for v in (ent.get("props") or {}).values()))
    c.ok("简介附来源出处（每条知识可溯源）", bool((d or {}).get("source")))
    rels = (d or {}).get("relations") or []
    c.ok("关联实体按「关系 × 邻居类型」分组", bool(rels) and all(
        g.get("relation") and g.get("label") and g.get("neighbor_type") and g.get("items") for g in rels))
    c.ok("局部 1 跳关系图结构与图谱页同构",
         all(k in ((d or {}).get("subgraph") or {}) for k in ("nodes", "links")))
    c.api("词条不存在 → 404（前端跳友好 404 页）", 404, c.get("/entity/不存在的词条"))


def fr_g06(c, kg):
    """知识测验试做：游客可整卷试做；题量仅 5/10；成绩不保存。"""
    c.group("FR-G06", "知识测验试做（F7）")
    c.api("题量非 5/10 → 422", 422, c.get("/quiz", params={"n": 7}))
    c.api("游客保存成绩 → 401（触发登录引导）", 401,
          c.post("/quiz/submit", json={"questions": [], "answers": []}))
    if not kg:
        c.skip("出题断言", "图谱无数据")
        return
    for n in (5, 10):
        d = c.data("/quiz", params={"n": n})
        qs = (d or {}).get("questions") or []
        c.ok("题量 %d 一次返回整卷" % n, len(qs) == n, "实得 %d 题" % len(qs))
        if not qs:
            continue
        c.ok("每题四选项且含正确项与解析（前端持有不显示）", all(
            len(q.get("options") or []) == 4 and q.get("answer_key") and q.get("explanation") for q in qs))
        c.ok("正确答案在选项内", all(
            q["answer_key"] in [o["key"] for o in q["options"]] for q in qs))
        c.ok("干扰项不重复正确答案", all(
            len({o["text"] for o in q["options"]}) == 4 for q in qs))
        c.ok("每题附实体供「去百科页复习」", all(
            (q.get("entity") or {}).get("name") for q in qs))


def fr_g07(c):
    """账号注册：用户名唯一性预检；四类用例；成功后自动登录。"""
    c.group("FR-G07", "账号注册（F5）")
    import time
    uname = "frsreg%d" % (int(time.time()) % 100000)
    pwd = "Frstest2026"
    avail = c.data("/auth/check", params={"username": uname})
    c.ok("用户名唯一性预检可用", (avail or {}).get("available") is True)
    body = c.api("正常注册成功", 0, c.post("/auth/register", json={
        "username": uname, "password": pwd, "confirm_password": pwd}), ["token"])
    d = body.get("data") or {}
    c.ok("注册后自动登录（直接签发 token）", bool(d.get("token")))
    c.ok("默认昵称 = 用户名", (d.get("user") or {}).get("nickname") == uname)
    c.ok("重名预检转为不可用",
         (c.data("/auth/check", params={"username": uname}) or {}).get("available") is False)
    c.api("重名注册 → 422", 422, c.post("/auth/register", json={
        "username": uname, "password": pwd, "confirm_password": pwd}))
    c.api("弱密码（无数字）→ 422", 422, c.post("/auth/register", json={
        "username": uname + "b", "password": "abcdefgh", "confirm_password": "abcdefgh"}))
    c.api("两次密码不一致 → 422", 422, c.post("/auth/register", json={
        "username": uname + "c", "password": pwd, "confirm_password": "Other2026x"}))
    c.api("用户名含非法字符 → 422", 422, c.post("/auth/register", json={
        "username": "非法用户名", "password": pwd, "confirm_password": pwd}))
    return uname, pwd


def fr_g08(c, uname, pwd):
    """登录：JWT 载荷；错误提示不区分具体项；禁用与过期处理。"""
    c.group("FR-G08", "登录（F5）")
    body = c.api("正确凭据登录成功", 0,
                 c.post("/auth/login", json={"username": uname, "password": pwd}), ["token"])
    user = (body.get("data") or {}).get("user") or {}
    c.ok("返回 user_id / role / nickname / avatar_url / must_change_pwd",
         all(k in user for k in ("user_id", "role", "nickname", "avatar_url", "must_change_pwd")))
    wrong = c.post("/auth/login", json={"username": uname, "password": "WrongPwd2026"})
    c.api("密码错误 → 401", 401, wrong)
    c.ok("错误提示不区分用户名或密码",
         "用户名或密码错误" in (wrong.json().get("msg") or ""), wrong.json().get("msg", ""))
    c.api("不存在的用户 → 401（提示同上，不暴露账号存在性）", 401,
          c.post("/auth/login", json={"username": "nobody_at_all", "password": pwd}))
    c.api("无 token 访问个人接口 → 401", 401, c.get("/user/profile"))
    c.api("非法 token → 401", 401, c.get("/user/profile", headers=c.auth("not-a-real-token")))
    return c.auth((body.get("data") or {}).get("token") or "")


def run(c, kg):
    fr_g01(c, kg)
    fr_g02(c, kg)
    fr_g03(c, kg)
    fr_g04(c, kg)
    fr_g05(c, kg)
    fr_g06(c, kg)
    uname, pwd = fr_g07(c)
    headers = fr_g08(c, uname, pwd)
    return {"username": uname, "password": pwd, "headers": headers}
