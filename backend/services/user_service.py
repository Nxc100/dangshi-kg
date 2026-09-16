# -*- coding: utf-8 -*-
"""
个人资料 / 头像 / 改密（开发规范 6.2 / 7.1）—— 操作对象一律是当前登录人（禁止从请求取 user_id）。

头像：前端 canvas 裁剪压缩后上传，后端二次校验（扩展名白名单 + 文件头魔数 + 大小 ≤ 2MB），
存 backend/static/avatars/{user_id}.jpg（同名覆盖，每用户恒一张）。
"""
import os

from werkzeug.security import check_password_hash, generate_password_hash

from backend.common.errors import BadRequest
from backend.config import Config
from backend.extensions import db_session

MAX_AVATAR_BYTES = 2 * 1024 * 1024
_ALLOWED_EXT = (".jpg", ".jpeg", ".png")
_MAGIC = ((b"\xff\xd8\xff", "JPEG"), (b"\x89PNG", "PNG"))


def profile(user):
    """当前登录人的资料（FR-U01）。"""
    return user.to_dict()


def update_nickname(user, nickname):
    """修改本人昵称，全站显示位置随之同步（FR-U01）。"""
    user.nickname = nickname
    db_session.commit()
    return user.to_dict()


def change_password(user, old_password, new_password, confirm_password):
    """改密：校验原密码、新旧不同、两次一致；成功后清 must_change_pwd，前端强制重登（FR-U03）。"""
    if not check_password_hash(user.pwd_hash, old_password):
        raise BadRequest("原密码不正确", errors={"old_password": "原密码不正确"})
    if new_password != confirm_password:
        raise BadRequest("两次输入的密码不一致", errors={"confirm_password": "两次输入的密码不一致"})
    if old_password == new_password:
        raise BadRequest("新密码不能与原密码相同", errors={"new_password": "新密码不能与原密码相同"})
    user.pwd_hash = generate_password_hash(new_password)
    user.must_change_pwd = 0
    db_session.commit()
    return True


def _check_upload(filename, content):
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        raise BadRequest("仅支持 JPG/PNG 格式", errors={"file": "仅支持 JPG/PNG 格式"})
    if len(content) > MAX_AVATAR_BYTES:
        raise BadRequest("图片不能超过 2MB", errors={"file": "图片不能超过 2MB"})
    if not any(content.startswith(magic) for magic, _ in _MAGIC):
        raise BadRequest("文件格式校验未通过，仅支持 JPG/PNG 图片", errors={"file": "文件不是有效的 JPG/PNG 图片"})


def save_avatar(user, file_storage):
    """文件名不采用用户原始文件名（防路径注入），统一由 user_id 生成。"""
    if file_storage is None:
        raise BadRequest("请选择图片", errors={"file": "请选择图片"})
    content = file_storage.read()
    _check_upload(file_storage.filename, content)
    os.makedirs(Config.AVATAR_DIR, exist_ok=True)
    path = os.path.join(Config.AVATAR_DIR, "%d.jpg" % user.id)
    with open(path, "wb") as f:
        f.write(content)
    user.avatar_path = "static/avatars/%d.jpg" % user.id
    db_session.commit()
    return {"avatar_url": user.avatar_url()}
