"""
URL configuration for XingXingWebSocket project.

URL 路径说明：
  /xiaoying/admin/              → 聊天室首页（入口，需登录验证）
  /xiaoying/admin/room/<name>/  → 普通用户聊天室
  /xiaoying/admin/script/<name>/→ 脚本管理面板
  /admin/                       → Django 后台管理
  /                             → 简单提示页（防陌生人直接访问）
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def landing(request):
    """根域名提示页，防止未经授权直接访问聊天功能"""
    return HttpResponse(
        "<h1>XingXing WebSocket</h1>"
        # "<p>欢迎访问，请通过正确的入口登录。</p>"
        # "<hr><p style='color:#666;font-size:12px'>"
        # "<a href='/xiaoying/admin/'>进入管理后台</a></p>",
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("xiaoying/admin/", include("chat.urls")),
    path("", landing, name="landing"),
]
