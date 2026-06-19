"""
ASGI config for XingXingWebSocket project.

WebSocket 路由集成：
  - 普通用户连接: ws://host:port/ws/chat/<room_name>/?username=<用户名>
  - 脚本连接:     ws://host:port/ws/chat/<room_name>/?type=script
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "XingXingWebSocket.settings")

# 延迟导入，确保 Django 设置已加载
from chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
