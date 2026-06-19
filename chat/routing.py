"""
WebSocket URL routing for the chat application.

用法:
  - 普通用户: ws://host:port/ws/chat/<room_name>/?username=<用户名>
  - 脚本:     ws://host:port/ws/chat/<room_name>/?type=script
"""
from django.urls import re_path

from chat import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
