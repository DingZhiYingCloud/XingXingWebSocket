import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render

from chat.consumers import rooms

# =============================================================================
# 管理员面板密码保护
# =============================================================================
ADMIN_PASSWORD = "dzyDZY12@"
MAX_ATTEMPTS = 3
# IP 封禁记录：{ip_address: attempt_count}
_admin_ip_attempts = {}


def _get_client_ip(request):
    """获取客户端真实 IP"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _check_ip_blocked(ip):
    """检查 IP 是否已被永久封禁（达到最大尝试次数）"""
    count = _admin_ip_attempts.get(ip, 0)
    return count >= MAX_ATTEMPTS


def index(request):
    """管理面板首页：密码验证 + 公告栏"""
    client_ip = _get_client_ip(request)

    # 检查 IP 是否被封禁
    if _check_ip_blocked(client_ip):
        return HttpResponseForbidden(
            "<h1>403 Forbidden</h1>"
            "<p>您已被永久禁止访问管理面板（密码错误次数过多）。</p>"
            "<hr><p style='color:#666;font-size:12px'>XingXing WebSocket</p>"
        )

    authenticated = request.session.get("admin_authenticated", False)

    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        if password == ADMIN_PASSWORD:
            request.session["admin_authenticated"] = True
            authenticated = True
            # 清除该 IP 的失败记录
            _admin_ip_attempts.pop(client_ip, None)
        else:
            # 记录失败次数
            current = _admin_ip_attempts.get(client_ip, 0) + 1
            _admin_ip_attempts[client_ip] = current
            remaining = MAX_ATTEMPTS - current
            if remaining <= 0:
                return HttpResponseForbidden(
                    "<h1>403 Forbidden</h1>"
                    "<p>您已被永久禁止访问管理面板（密码错误次数过多）。</p>"
                    "<hr><p style='color:#666;font-size:12px'>XingXing WebSocket</p>"
                )
            return render(request, "chat/index.html", {
                "authenticated": False,
                "error": f"密码错误！剩余尝试次数：{remaining}",
                "remaining": remaining,
                "room_list": _get_active_rooms(),
            })

    # 获取活跃房间列表
    active_rooms = _get_active_rooms()

    return render(request, "chat/index.html", {
        "authenticated": authenticated,
        "error": "",
        "room_list": active_rooms,
    })


def _get_active_rooms():
    """从 consumers 的 rooms 字典获取当前所有活跃房间"""
    return [
        {
            "name": room_name,
            "user_count": len(data.get("users", {})),
            "script_count": len(data.get("scripts", {})),
        }
        for room_name, data in rooms.items()
    ]


def room(request, room_name):
    """普通用户聊天室页面"""
    return render(request, "chat/room.html", {
        "room_name": room_name,
    })


def script_panel(request, room_name):
    """脚本管理面板页面"""
    return render(request, "chat/script.html", {
        "room_name": room_name,
    })


def download_config(request):
    """提供客户端配置文件（支持跨域访问）"""
    config_path = Path(settings.BASE_DIR) / "chat" / "static" / "chat" / "download_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JsonResponse(data)
    except FileNotFoundError:
        return JsonResponse({"error": "Config file not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid config file"}, status=500)
