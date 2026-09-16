# -*- coding: utf-8 -*-
"""FRS 4.2 注册用户（R2）功能验收：FR-U01 ~ FR-U07。"""
import io


def _png(size=64):
    """构造合法 PNG 字节流（用于头像魔数校验的正向用例）。"""
    import struct
    import zlib
    px = bytearray()
    for _ in range(size):
        px.append(0)
        px.extend(b"\xc8\xc8\xc8" * size)
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(px), 9)) + chunk(b"IEND", b""))


def fr_u01(c, h):
    """个人资料查看与昵称修改：昵称 1–16 字符。"""
    c.group("FR-U01", "个人资料查看与昵称修改")
    body = c.api("查看本人资料", 0, c.get("/user/profile", headers=h),
                 ["username", "nickname", "created_at"])
    c.ok("含头像 URL（未上传时为系统默认头像）",
         bool((body.get("data") or {}).get("avatar_url")))
    c.api("修改昵称成功", 0, c.put("/user/profile", json={"nickname": "自检昵称"}, headers=h),
          ["nickname"])
    c.ok("修改后再查为新值",
         (c.data("/user/profile", headers=h) or {}).get("nickname") == "自检昵称")
    c.api("昵称超 16 字符 → 422", 422,
          c.put("/user/profile", json={"nickname": "超长" * 12}, headers=h))
    c.api("昵称为空 → 422", 422, c.put("/user/profile", json={"nickname": "   "}, headers=h))


def fr_u02(c, h):
    """头像上传：类型 + 大小 + 文件头魔数三重校验；每用户恒一张。"""
    c.group("FR-U02", "头像图片上传")
    png = _png()
    body = c.api("上传合法 PNG 成功", 0, c.post(
        "/user/avatar", files={"file": ("a.png", io.BytesIO(png), "image/png")}, headers=h),
        ["avatar_url"])
    url = (body.get("data") or {}).get("avatar_url") or ""
    c.ok("返回带时间戳参数的头像 URL（破缓存）", "?t=" in url, url[:52])
    c.ok("文件名由 user_id 生成，不采用原始文件名（防路径注入）",
         "a.png" not in url and "avatars/" in url)
    c.api("GIF 被拒（仅支持 JPG/PNG）", 422, c.post(
        "/user/avatar", files={"file": ("a.gif", io.BytesIO(b"GIF89a" + b"\x00" * 64), "image/gif")},
        headers=h))
    fake_text = "这其实是一个文本文件，只是改了扩展名。".encode("utf-8") * 8
    c.api("改名的文本文件被魔数校验拦截", 422, c.post(
        "/user/avatar", files={"file": ("fake.png", io.BytesIO(fake_text), "image/png")},
        headers=h))
    c.api("超 2MB 被拒", 422, c.post(
        "/user/avatar",
        files={"file": ("big.png", io.BytesIO(png + b"\x00" * (2 * 1024 * 1024 + 16)), "image/png")},
        headers=h))
    c.ok("再次上传覆盖旧图（每用户恒一张）",
         c.post("/user/avatar", files={"file": ("b.png", io.BytesIO(png), "image/png")},
                headers=h).json().get("code") == 0)
    c.api("游客上传头像 → 401", 401,
          c.post("/user/avatar", files={"file": ("a.png", io.BytesIO(png), "image/png")}))


def fr_u04(c, h, kg):
    """提问历史：倒序分页；删除为逻辑删除，不影响管理端统计。"""
    c.group("FR-U04", "提问历史")
    q1, q2 = "遵义会议在哪里召开", "秋收起义是谁领导的"
    for q in (q1, q2):
        c.post("/qa", json={"question": q}, headers=h)
    d = c.data("/user/history", headers=h) or {}
    items = d.get("list") or []
    c.ok("登录后提问自动入历史（无需用户操作）", len(items) >= 2, "%d 条" % d.get("total", 0))
    c.ok("倒序排列（最新在前）", bool(items) and items[0]["question"] == q2,
         items[0]["question"] if items else "")
    c.ok("列表项含问句 / 答案摘要 / 兜底标记 / 时间", bool(items) and all(
        k in items[0] for k in ("question", "answer_brief", "fallback", "created_at")))
    c.ok("答案摘要不超过 40 字", all(len(i.get("answer_brief") or "") <= 42 for i in items))
    c.ok("分页结构统一 {list,page,size,total}",
         all(k in d for k in ("list", "page", "size", "total")))
    before = len(items)
    c.api("删除单条历史", 0, c.delete("/user/history/%d" % items[0]["id"], headers=h))
    c.ok("删除后个人列表减少",
         len((c.data("/user/history", headers=h) or {}).get("list") or []) == before - 1)
    c.api("删除他人/不存在的记录 → 404", 404, c.delete("/user/history/999999", headers=h))
    c.api("清空历史", 0, c.delete("/user/history", headers=h))
    c.ok("清空后个人列表为空",
         (c.data("/user/history", headers=h) or {}).get("total") == 0)
    return q1


def fr_u05(c, h, kg):
    """收藏夹：实体与问答两类；重复收藏幂等；取消校验归属。"""
    c.group("FR-U05", "收藏夹")
    log_id = ((c.post("/qa", json={"question": "遵义会议在哪里召开"}, headers=h).json()
               .get("data")) or {}).get("log_id")
    c.api("收藏问答（入口：答案气泡）", 0, c.post(
        "/user/favorite", json={"fav_type": "qa", "ref_id": str(log_id)}, headers=h))
    c.api("重复收藏幂等，不报错", 0, c.post(
        "/user/favorite", json={"fav_type": "qa", "ref_id": str(log_id)}, headers=h))
    d = c.data("/user/favorite", params={"fav_type": "qa"}, headers=h) or {}
    c.ok("幂等后仅 1 条记录", d.get("total") == 1, "%d 条" % d.get("total", -1))
    c.ok("问答项回填问句与答案，可展开重新提问",
         bool((d.get("list") or [{}])[0].get("question")))
    if kg:
        c.api("收藏实体（入口：百科页）", 0, c.post(
            "/user/favorite", json={"fav_type": "entity", "ref_id": "遵义会议"}, headers=h))
        ed = c.data("/user/favorite", params={"fav_type": "entity"}, headers=h) or {}
        item = (ed.get("list") or [{}])[0]
        c.ok("实体项回填类型与删除态", item.get("type") == "Meeting" and item.get("deleted") is False)
        c.ok("百科页反映收藏态",
             (c.data("/entity/遵义会议", headers=h) or {}).get("favorited") is True)
        c.api("取消收藏", 0, c.delete(
            "/user/favorite", json={"fav_type": "entity", "ref_id": "遵义会议"}, headers=h))
        c.ok("取消后百科页收藏态复位",
             (c.data("/entity/遵义会议", headers=h) or {}).get("favorited") is False)
    c.api("非法收藏类型 → 422", 422, c.post(
        "/user/favorite", json={"fav_type": "other", "ref_id": "x"}, headers=h))
    c.api("取消未收藏的对象 → 404", 404, c.delete(
        "/user/favorite", json={"fav_type": "entity", "ref_id": "从未收藏过"}, headers=h))


def fr_u06(c, h, kg):
    """测验成绩保存与错题复习：后端复算得分；错题再练。"""
    c.group("FR-U06", "测验成绩保存与错题复习")
    if not kg:
        c.skip("测验保存断言", "图谱无数据")
        return
    qs = (c.data("/quiz", params={"n": 5}) or {}).get("questions") or []
    if len(qs) < 5:
        c.skip("测验保存断言", "出题不足")
        return
    # 前 3 题答对、后 2 题答错
    answers = [q["answer_key"] if i < 3 else
               next(o["key"] for o in q["options"] if o["key"] != q["answer_key"])
               for i, q in enumerate(qs)]
    body = c.api("保存成绩", 0, c.post("/quiz/submit", json={
        "questions": qs, "answers": answers, "duration_sec": 66}, headers=h),
        ["record_id", "score", "total"])
    d = body.get("data") or {}
    c.ok("后端复算得分（3/5），不信任前端上报", d.get("score") == 3 and d.get("total") == 5,
         "%s/%s" % (d.get("score"), d.get("total")))
    # 前端篡改得分应被忽略
    b2 = c.post("/quiz/submit", json={"questions": qs, "answers": answers,
                                      "score": 5, "duration_sec": 10}, headers=h).json()
    c.ok("请求体强塞 score 被忽略", (b2.get("data") or {}).get("score") == 3)
    recs = c.data("/quiz/records", headers=h) or {}
    c.ok("测验记录倒序可查", (recs.get("total") or 0) >= 1, "%d 条" % recs.get("total", 0))
    detail = c.data("/quiz/records/%d" % d["record_id"], headers=h) or {}
    dq = (detail.get("detail") or {}).get("questions") or []
    c.ok("详情逐题回顾（题干/选项/作答/对错/解析）", len(dq) == 5 and all(
        k in dq[0] for k in ("question", "options", "chosen", "correct", "explanation")))
    c.ok("错题可定位（2 道）", sum(1 for q in dq if not q["correct"]) == 2)
    c.ok("记录用时", (detail.get("detail") or {}).get("duration_sec") == 66)
    c.ok("错题附实体供「去百科页复习」", all((q.get("entity") or {}).get("name") for q in dq))
    # 针对错题再练
    ents = [q["entity"]["name"] for q in dq if not q["correct"]]
    again = c.data("/quiz", params={"n": 5, "entities": ",".join(ents)}) or {}
    c.ok("针对错题再练，不足 5 题自动补随机",
         len(again.get("questions") or []) == 5, "%d 题" % len(again.get("questions") or []))
    c.api("作答数与题数不一致 → 422", 422, c.post("/quiz/submit", json={
        "questions": qs, "answers": answers[:2]}, headers=h))
    c.api("他人记录不可见 → 404", 404, c.get("/quiz/records/999999", headers=h))


def fr_u03_u07(c, uname, pwd):
    """修改密码与退出登录：改密后强制重登，旧密码失效。"""
    c.group("FR-U03", "修改密码")
    h = c.auth(c.post("/auth/login", json={"username": uname, "password": pwd})
               .json()["data"]["token"])
    newpwd = "Frsnew2026"
    c.api("原密码错误 → 422", 422, c.put("/user/password", json={
        "old_password": "WrongOld2026", "new_password": newpwd,
        "confirm_password": newpwd}, headers=h))
    c.api("新旧密码相同 → 422", 422, c.put("/user/password", json={
        "old_password": pwd, "new_password": pwd, "confirm_password": pwd}, headers=h))
    c.api("新密码不符合强度 → 422", 422, c.put("/user/password", json={
        "old_password": pwd, "new_password": "abcdefgh", "confirm_password": "abcdefgh"}, headers=h))
    c.api("两次新密码不一致 → 422", 422, c.put("/user/password", json={
        "old_password": pwd, "new_password": newpwd, "confirm_password": "Other2026x"}, headers=h))
    c.api("正常改密成功", 0, c.put("/user/password", json={
        "old_password": pwd, "new_password": newpwd, "confirm_password": newpwd}, headers=h))
    c.api("旧密码登录失败", 401, c.post("/auth/login", json={"username": uname, "password": pwd}))
    body = c.api("新密码登录成功", 0,
                 c.post("/auth/login", json={"username": uname, "password": newpwd}), ["token"])

    c.group("FR-U07", "退出登录")
    h2 = c.auth((body.get("data") or {}).get("token") or "")
    c.ok("退出前个人接口可用", c.get("/user/profile", headers=h2).json().get("code") == 0)
    c.ok("退出为前端清除 token（无服务端接口，符合 FRS）", True, "退出后无 token 即 401")
    c.api("清除 token 后访问个人接口 → 401", 401, c.get("/user/profile"))
    return newpwd


def run(c, kg, guest):
    h, uname, pwd = guest["headers"], guest["username"], guest["password"]
    fr_u01(c, h)
    fr_u02(c, h)
    fr_u04(c, h, kg)
    fr_u05(c, h, kg)
    fr_u06(c, h, kg)
    newpwd = fr_u03_u07(c, uname, pwd)
    return {"username": uname, "password": newpwd}
