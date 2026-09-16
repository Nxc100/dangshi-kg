# -*- coding: utf-8 -*-
"""FRS 4.3 管理员（R3）知识管理验收：FR-A01 ~ FR-A03。

FR-A04~A07（操作日志、用户管理、问答日志、统计看板）见 admin_gov.py。
"""

from eval.frs import admin_gov

SEED_SOURCE = "http://cpc.people.com.cn/GB/64162/64168/index.html"


def login_admin(c, init_pwd, new_pwd):
    """admin 首登须改密（规范决策②）；返回改密后的请求头。"""
    c.group("FR-A01", "后台入口与总览")
    body = c.post("/auth/login", json={"username": "admin", "password": init_pwd}).json()
    if body.get("code") != 0:
        body = c.post("/auth/login", json={"username": "admin", "password": new_pwd}).json()
        if body.get("code") != 0:
            c.ok("admin 登录", False, "初始口令与新口令均不匹配")
            return None
        c.skip("首登强制改密链路", "admin 已改过密码（重置空白库可完整验证）")
        return c.auth(body["data"]["token"])
    h = c.auth(body["data"]["token"])
    c.ok("admin 登录成功", True)
    if body["data"]["user"].get("must_change_pwd") == 1:
        c.api("未改初始密码时后台被拦截 → 422", 422, c.get("/admin/overview", headers=h))
        c.api("未改密仍可访问改密所需的资料接口", 0, c.get("/user/profile", headers=h))
        c.api("修改初始密码", 0, c.put("/user/password", json={
            "old_password": init_pwd, "new_password": new_pwd,
            "confirm_password": new_pwd}, headers=h))
        body = c.post("/auth/login", json={"username": "admin", "password": new_pwd}).json()
        h = c.auth(body["data"]["token"])
        c.ok("改密后 must_change_pwd 清零", body["data"]["user"]["must_change_pwd"] == 0)
    return h


def fr_a01(c, h, user_h):
    """后台总览四个概览数字卡；普通用户越权被拒。"""
    body = c.api("总览四数字卡", 0, c.get("/admin/overview", headers=h),
                 ["entity_count", "relation_count", "user_count", "today_qa_count"])
    d = body.get("data") or {}
    c.ok("四项均为数值", all(isinstance(d.get(k), int) for k in
                         ("entity_count", "relation_count", "user_count", "today_qa_count")))
    for path in ("/admin/overview", "/admin/entity", "/admin/users", "/stats/overview"):
        c.api("普通用户访问 %s → 403" % path, 403, c.get(path, headers=user_h))
    c.api("游客访问后台 → 401", 401, c.get("/admin/overview"))


def fr_a02(c, h, kg):
    """实体管理：检索、新增、编辑、删除（级联提示与高连接度强确认）、op_log 留痕。"""
    c.group("FR-A02", "实体管理（F6）")
    if not kg:
        c.skip("实体管理断言", "图谱无数据")
        return None
    d = c.data("/admin/entity", params={"page": 1, "size": 10}, headers=h) or {}
    items = d.get("list") or []
    c.ok("分页检索返回名称/类型/关系数/核心池/更新时间", bool(items) and all(
        k in items[0] for k in ("name", "type", "degree", "checked", "updated_at")))
    c.ok("按类型筛选生效", all(
        i["type"] == "Person" for i in
        ((c.data("/admin/entity", params={"type": "Person"}, headers=h) or {}).get("list") or [])))
    c.ok("按名称关键词检索生效", all(
        "会议" in i["name"] for i in
        ((c.data("/admin/entity", params={"kw": "会议"}, headers=h) or {}).get("list") or [])))

    name = "自检测试会议"
    props = {"name": name, "time_text": "1949年3月5日", "intro": "FRS 自检用临时实体。",
             "source": SEED_SOURCE}
    # 先清理上次中断可能留下的同名实体，保证用例可重复执行
    c.delete("/admin/entity", json={"type": "Meeting", "name": name, "confirm_name": name}, headers=h)
    c.api("新增实体（按类型动态属性）", 0, c.post(
        "/admin/entity", json={"type": "Meeting", "props": props}, headers=h), ["name", "period"])
    got = c.data("/entity/%s" % name) or {}
    c.ok("新增后前台百科页即时可见（无应用层缓存）", (got.get("entity") or {}).get("name") == name)
    c.ok("新增实体 checked=0，不进测验与推荐池", (got.get("entity") or {}).get("checked") == 0)
    c.ok("Event/Meeting 自动挂时期（规范决策⑦）", any(
        g["relation"] == "BELONGS_TO" for g in (got.get("relations") or [])))
    c.api("重名新增 → 422 并提示前往编辑", 422, c.post(
        "/admin/entity", json={"type": "Meeting", "props": props}, headers=h))
    c.api("缺必填属性 → 422", 422, c.post(
        "/admin/entity", json={"type": "Meeting", "props": {"name": "缺字段会议"}}, headers=h))
    c.api("时间无法解析 → 422 可读提示", 422, c.post("/admin/entity", json={
        "type": "Meeting", "props": dict(props, name="坏时间会议", time_text="很久以前")}, headers=h))

    edited = dict(props, intro="FRS 自检用临时实体（已修改）。")
    c.api("编辑实体", 0, c.put("/admin/entity", json={
        "type": "Meeting", "name": name, "props": edited, "checked": 1}, headers=h))
    got2 = c.data("/entity/%s" % name) or {}
    c.ok("编辑后前台即时生效", "已修改" in (got2.get("intro") or ""))
    c.ok("勾选「已校验」置 checked=1（规范决策⑦）", (got2.get("entity") or {}).get("checked") == 1)
    c.api("编辑时间后时期重算", 0, c.put("/admin/entity", json={
        "type": "Meeting", "name": name, "props": dict(edited, time_text="2013年5月1日")}, headers=h))
    periods = [i["name"] for g in ((c.data("/entity/%s" % name) or {}).get("relations") or [])
               if g["relation"] == "BELONGS_TO" for i in g["items"]]
    c.ok("时期随时间改为「中国特色社会主义新时代」", periods == ["中国特色社会主义新时代"], str(periods))
    return name


def fr_a03(c, h, kg, temp_entity):
    """关系管理：三级联动约束、幂等提示、删除。"""
    c.group("FR-A03", "关系管理（F6）")
    if not kg or not temp_entity:
        c.skip("关系管理断言", "图谱无数据")
        return
    d = c.data("/admin/triple", params={"page": 1, "size": 5}, headers=h) or {}
    items = d.get("list") or []
    c.ok("分页列出头实体/关系/中文名/尾实体", bool(items) and all(
        k in items[0] for k in ("head", "rel", "label", "tail")))
    c.ok("按关系类型筛选生效", all(
        i["rel"] == "HELD_IN" for i in
        ((c.data("/admin/triple", params={"rel": "HELD_IN"}, headers=h) or {}).get("list") or [])))

    triple = {"head": "毛泽东", "head_type": "Person", "rel": "PARTICIPATED_IN",
              "tail": temp_entity, "tail_type": "Meeting"}
    c.api("新增三元组", 0, c.post("/admin/triple", json=triple, headers=h))
    rels = (c.data("/entity/%s" % temp_entity) or {}).get("relations") or []
    c.ok("新增后百科页「出席人物」即时出现", any(
        g["relation"] == "PARTICIPATED_IN" and any(i["name"] == "毛泽东" for i in g["items"])
        for g in rels))
    c.api("重复新增 → 422「该关系已存在」", 422, c.post("/admin/triple", json=triple, headers=h))
    c.api("头尾类型组合不合本体 → 422", 422, c.post("/admin/triple", json={
        "head": "毛泽东", "head_type": "Person", "rel": "HELD_IN",
        "tail": "遵义", "tail_type": "Location"}, headers=h))
    c.api("自指关系 → 422", 422, c.post("/admin/triple", json={
        "head": "八路军", "head_type": "Organization", "rel": "REORGANIZED_TO",
        "tail": "八路军", "tail_type": "Organization"}, headers=h))
    c.api("非白名单关系类型 → 422", 422, c.post("/admin/triple", json=dict(
        triple, rel="DROP_EVERYTHING"), headers=h))
    c.api("头实体不存在 → 422 提示先新增实体", 422, c.post("/admin/triple", json=dict(
        triple, head="查无此人"), headers=h))
    c.api("HELD_POSITION 缺 position → 422", 422, c.post("/admin/triple", json={
        "head": "毛泽东", "head_type": "Person", "rel": "HELD_POSITION",
        "tail": "八路军", "tail_type": "Organization"}, headers=h))
    c.api("删除三元组", 0, c.delete("/admin/triple", json=triple, headers=h))
    rels2 = (c.data("/entity/%s" % temp_entity) or {}).get("relations") or []
    c.ok("删除后百科页对应分组消失", not any(
        g["relation"] == "PARTICIPATED_IN" for g in rels2))
    c.api("删除不存在的关系 → 404", 404, c.delete("/admin/triple", json=triple, headers=h))


def fr_a02_delete(c, h, kg, name):
    """实体删除：级联计数实时查询、高连接度强确认。"""
    if not kg or not name:
        return
    c.group("FR-A02", "实体删除与级联提示")
    body = c.api("删除实体", 0, c.delete("/admin/entity", json={
        "type": "Meeting", "name": name}, headers=h), ["cascade_relations"])
    c.ok("返回级联删除的关系数（实时查询）",
         isinstance((body.get("data") or {}).get("cascade_relations"), int))
    c.api("删除后百科页 404", 404, c.get("/entity/%s" % name))
    c.api("删除不存在的实体 → 404", 404, c.delete("/admin/entity", json={
        "type": "Meeting", "name": name}, headers=h))
    fr_a02_high_degree(c, h)


def fr_a02_high_degree(c, h):
    """
    高连接度实体删除强确认（FR-A02：关系数 ≥ 20 须输入实体名确认）。

    种子数据最高仅 15 条关系，故由用例自建一个高连接度实体：挂满会议与文献关系
    直到越过阈值，验证拦截与放行两条路径后原样删除，不污染图谱。
    """
    c.group("FR-A02", "高连接度实体删除强确认")
    name = "自检高连接度人物"
    # 同样先清理残留，避免上次中断影响本次计数
    c.delete("/admin/entity", json={"type": "Person", "name": name, "confirm_name": name}, headers=h)
    created = c.post("/admin/entity", json={"type": "Person", "props": {
        "name": name, "intro": "FRS 自检用临时人物，用例结束即删除。",
        "source": SEED_SOURCE}}, headers=h).json()
    if created.get("code") != 0:
        c.skip("高连接度实体强确认", "临时实体创建失败：%s" % created.get("msg"))
        return
    # 挂关系直到越过阈值：参加全部会议 + 创作全部文献
    # 会议 12 + 文献 7 = 19 条，不足阈值，故再挂 LED→Event 补足
    targets = [("PARTICIPATED_IN", "Meeting"), ("AUTHORED", "Document"), ("LED", "Event")]
    linked = 0
    for rel, label in targets:
        for item in ((c.data("/admin/entity", params={"type": label, "size": 50},
                             headers=h) or {}).get("list") or []):
            if c.post("/admin/triple", json={
                    "head": name, "head_type": "Person", "rel": rel,
                    "tail": item["name"], "tail_type": label}, headers=h).json().get("code") == 0:
                linked += 1
            if linked >= 21:
                break
        if linked >= 21:
            break

    degree = next((i["degree"] for i in
                   ((c.data("/admin/entity", params={"kw": name, "size": 50}, headers=h) or {})
                    .get("list") or []) if i["name"] == name), 0)
    c.ok("已构造关系数 ≥ 20 的实体", degree >= 20, "%d 条关系" % degree)
    if degree < 20:
        c.delete("/admin/entity", json={"type": "Person", "name": name, "confirm_name": name}, headers=h)
        return
    c.api("未输入名称确认 → 422", 422,
          c.delete("/admin/entity", json={"type": "Person", "name": name}, headers=h))
    c.ok("被拦下后实体仍在",
         (c.data("/entity/%s" % name) or {}).get("entity") is not None)
    c.api("确认名称不匹配 → 422", 422, c.delete("/admin/entity", json={
        "type": "Person", "name": name, "confirm_name": "输错的名字"}, headers=h))
    body = c.api("输入正确名称后删除成功", 0, c.delete("/admin/entity", json={
        "type": "Person", "name": name, "confirm_name": name}, headers=h), ["cascade_relations"])
    c.ok("级联删除计数与实际关系数一致",
         (body.get("data") or {}).get("cascade_relations") == degree,
         "%s vs %d" % ((body.get("data") or {}).get("cascade_relations"), degree))
    c.api("删除后百科页 404", 404, c.get("/entity/%s" % name))


def run(c, kg, init_pwd, new_pwd, user_h, user_name):
    """依次执行 FR-A01~A07；返回管理员请求头供第五章闭环复用。"""
    h = login_admin(c, init_pwd, new_pwd)
    if not h:
        return None
    fr_a01(c, h, user_h)
    temp = fr_a02(c, h, kg)
    fr_a03(c, h, kg, temp)
    fr_a02_delete(c, h, kg, temp)
    admin_gov.fr_a04(c, h)
    admin_gov.fr_a05(c, h, user_name)
    admin_gov.fr_a06(c, h)
    admin_gov.fr_a07(c, h)
    return h
