# -*- coding: utf-8 -*-
"""
业务异常类 + 全局错误处理（开发规范 8.2 / 8.3）。

- 业务规则冲突一律 422 + 可读中文 msg；需要前端分支的场景用 data 补充结构化信息
  （如 data.errors={字段: 提示}、data.exists_type、data.reason='disabled' / 'must_change_pwd'）。
- 未捕获异常统一 500 "服务暂时不可用，请稍后重试"，并记录堆栈。
"""
import logging

from werkzeug.exceptions import HTTPException

from backend.common.response import fail

log = logging.getLogger(__name__)


class ApiError(Exception):
    code = 500

    def __init__(self, msg, code=None, data=None):
        super().__init__(msg)
        self.msg = msg
        if code is not None:
            self.code = code
        self.data = data


class BadRequest(ApiError):
    """422：参数校验失败或业务规则不允许。errors={字段: 中文提示} 供逐字段红字显示。"""

    code = 422

    def __init__(self, msg, errors=None, data=None):
        payload = dict(data or {})
        if errors:
            payload["errors"] = errors
        super().__init__(msg, data=payload or None)


class Unauthorized(ApiError):
    code = 401


class Forbidden(ApiError):
    code = 403

    def __init__(self, msg="无权限访问", data=None):
        super().__init__(msg, data=data)


class NotFound(ApiError):
    code = 404

    def __init__(self, msg="资源不存在", data=None):
        super().__init__(msg, data=data)


class ServiceError(ApiError):
    code = 500


class NotImplementedYet(ServiceError):
    """空白项目阶段占位：功能条目尚未实现（写接口使用；读接口返回空结构）。"""

    def __init__(self, feature):
        super().__init__("功能尚未实现：%s" % feature)


_HTTP_MSG = {
    400: (422, "请求参数格式错误"),
    401: (401, "未登录，请先登录"),
    403: (403, "无权限访问"),
    404: (404, "资源不存在"),
    405: (404, "请求方法不允许"),
    413: (422, "上传文件过大"),
    415: (422, "不支持的请求类型"),
}


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _handle_api_error(exc):
        return fail(exc.code, exc.msg, exc.data)

    @app.errorhandler(HTTPException)
    def _handle_http(exc):
        code, msg = _HTTP_MSG.get(exc.code, (500, "服务暂时不可用，请稍后重试"))
        if code == 500:
            log.error("HTTP %s: %s", exc.code, exc)
        return fail(code, msg)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):
        log.exception("未捕获异常：%s", exc)
        return fail(500, "服务暂时不可用，请稍后重试")
