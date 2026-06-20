"""
WebSocket consumers for the chat application.

Architecture:
  - Users connect to rooms and exchange messages in real-time
  - "Script" is a supervisor role that can monitor and interact with users
  - Messages are stored in-memory per room (last 200 messages)

Protocol (Client → Server):
  - {"type": "chat.message", "text": "..."}           普通用户发消息
  - {"type": "script.broadcast", "text": "..."}       脚本广播
  - {"type": "script.list_users"}                     脚本查看用户列表
  - {"type": "script.view_user", "username": "..."}   脚本订阅查看某用户消息
  - {"type": "script.unview_user", "username": "..."} 脚本取消订阅
  - {"type": "script.private", "target": "...", "text": "..."}  脚本私聊某用户
  - {"type": "script.history", "username": "..."}     脚本查看某用户消息历史

Protocol (Server → Client):
  - {"type": "chat.message", "username": "...", "text": "...", "timestamp": "..."}
  - {"type": "script.broadcast", "text": "...", "timestamp": "..."}
  - {"type": "system.info", "text": "..."}
  - {"type": "script.user_list", "users": [...]}
  - {"type": "script.user_message", "username": "...", "text": "...", "timestamp": "..."}
  - {"type": "script.private", "from": "...", "text": "...", "timestamp": "..."}
  - {"type": "script.history", "username": "...", "messages": [...]}
  - {"type": "error", "text": "..."}
"""
import json
from datetime import datetime
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer

# =============================================================================
# In-memory room state
# 生产环境应替换为 Redis，这里为演示使用内存存储
# =============================================================================
# Structure:
# {
#   "room_name": {
#       "users": {channel_name: username},
#       "messages": [{"username": str, "text": str, "timestamp": str}],
#       "scripts": {channel_name},
#       "script_viewing": {script_channel: {username1, ...}},
#   }
# }
# =============================================================================
rooms: dict = {}
# 每个房间最多保留的消息数
MAX_MESSAGES_PER_ROOM = 200


def _get_or_create_room(room_name: str) -> dict:
    """获取或创建房间"""
    if room_name not in rooms:
        rooms[room_name] = {
            "users": {},
            "messages": [],
            "scripts": set(),
            "script_viewing": {},
        }
    return rooms[room_name]


class ChatConsumer(AsyncWebsocketConsumer):
    """处理 WebSocket 连接的核心消费者"""

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]

        # 解析查询参数
        params = parse_qs(self.scope.get("query_string", b"").decode())
        self.is_script = "type" in params and params["type"][0] == "script"

        if self.is_script:
            self.username = "脚本管理员"
        else:
            self.username = params.get("username", [None])[0]
            if not self.username or not self.username.strip():
                await self.close(code=4000)
                return
            self.username = self.username.strip()

        self.room = _get_or_create_room(self.room_name)

        # 加入房间
        if self.is_script:
            self.room["scripts"].add(self.channel_name)
            self.room["script_viewing"][self.channel_name] = set()
        else:
            self.room["users"][self.channel_name] = self.username

        # 加入 Channels group（用于广播）
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        # 通知房间其他成员
        if not self.is_script:
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "system.info",
                    "text": f"✨ {self.username} 加入了房间",
                },
            )

        # 广播更新后的在线用户列表
        await self.broadcast_user_list()

    async def disconnect(self, close_code):
        room = rooms.get(self.room_name)
        if room:
            if self.is_script:
                room["scripts"].discard(self.channel_name)
                room["script_viewing"].pop(self.channel_name, None)
            else:
                username = room["users"].pop(self.channel_name, None)
                if username:
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "system.info",
                            "text": f"👋 {username} 离开了房间",
                        },
                    )

            # 广播更新后的在线用户列表
            await self.broadcast_user_list()

            # 房间空时清理
            if not room["users"] and not room["scripts"]:
                rooms.pop(self.room_name, None)

        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("无效的 JSON 格式")
            return

        msg_type = data.get("type", "")
        if self.is_script:
            await self._handle_script_message(data, msg_type)
        else:
            await self._handle_user_message(data, msg_type)

    # =========================================================================
    # 普通用户消息处理
    # =========================================================================
    async def _handle_user_message(self, data: dict, msg_type: str):
        if msg_type != "chat.message":
            await self._send_error("不支持的消息类型")
            return

        text = data.get("text", "").strip()
        if not text:
            return

        room = rooms.get(self.room_name)
        if not room:
            return

        username = room["users"].get(self.channel_name)
        if not username:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = {"username": username, "text": text, "timestamp": timestamp}

        # 存储消息历史
        room["messages"].append(msg)
        if len(room["messages"]) > MAX_MESSAGES_PER_ROOM:
            room["messages"] = room["messages"][-MAX_MESSAGES_PER_ROOM:]

        # 广播给房间其他用户（不包含发送者，默认不发给脚本）
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "username": username,
                "text": text,
                "timestamp": timestamp,
                "_sender_channel": self.channel_name,
                "_exclude_scripts": True,
            },
        )

        # 检查是否有脚本正在查看该用户，如有则转发
        for script_channel, viewing_set in room["script_viewing"].items():
            if username in viewing_set:
                await self.channel_layer.send(
                    script_channel,
                    {
                        "type": "script.user_message",
                        "username": username,
                        "text": text,
                        "timestamp": timestamp,
                    },
                )

    # =========================================================================
    # 脚本消息处理
    # =========================================================================
    async def _handle_script_message(self, data: dict, msg_type: str):
        room = rooms.get(self.room_name)
        if not room:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        if msg_type == "script.broadcast":
            text = data.get("text", "").strip()
            if not text:
                return

            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "script.broadcast",
                    "text": text,
                    "timestamp": timestamp,
                },
            )

        elif msg_type == "script.list_users":
            users = [
                {"username": uname, "channel_name": ch}
                for ch, uname in room["users"].items()
            ]
            await self.send(text_data=json.dumps({
                "type": "script.user_list",
                "users": users,
            }))

        elif msg_type == "script.view_user":
            username = data.get("username", "").strip()
            if not username:
                return

            # 检查用户是否存在
            user_exists = username in room["users"].values()
            if not user_exists:
                await self._send_error(f"用户 '{username}' 不在房间中")
                return

            viewing_set = room["script_viewing"].setdefault(self.channel_name, set())
            viewing_set.add(username)

            # 发送该用户的历史消息
            user_messages = [
                m for m in room["messages"] if m["username"] == username
            ]
            await self.send(text_data=json.dumps({
                "type": "script.history",
                "username": username,
                "messages": user_messages,
            }))

        elif msg_type == "script.unview_user":
            username = data.get("username", "").strip()
            viewing_set = room["script_viewing"].get(self.channel_name)
            if viewing_set:
                viewing_set.discard(username)

        elif msg_type == "script.private":
            target = data.get("target", "").strip()
            text = data.get("text", "").strip()
            if not target or not text:
                return

            # 找到目标用户的 channel_name
            target_channel = None
            for ch, uname in room["users"].items():
                if uname == target:
                    target_channel = ch
                    break

            if not target_channel:
                await self._send_error(f"用户 '{target}' 不在房间中")
                return

            # 发送私聊消息给目标用户
            await self.channel_layer.send(
                target_channel,
                {
                    "type": "script.private",
                    "from": "脚本管理员",
                    "text": text,
                    "timestamp": timestamp,
                },
            )

            # 也回显给脚本自己（确认发送成功）
            await self.send(text_data=json.dumps({
                "type": "script.private",
                "from": f"→ {target}",
                "text": text,
                "timestamp": timestamp,
            }))

        elif msg_type == "script.history":
            username = data.get("username", "").strip()
            if username:
                user_messages = [
                    m for m in room["messages"] if m["username"] == username
                ]
            else:
                user_messages = room["messages"]

            await self.send(text_data=json.dumps({
                "type": "script.history",
                "username": username or "*",
                "messages": user_messages,
            }))

        else:
            await self._send_error("不支持的脚本消息类型")

    # =========================================================================
    # Channels group 消息处理器
    # 这些方法由 channel_layer.group_send 触发
    # =========================================================================
    async def chat_message(self, event):
        """转发普通用户的消息"""
        # 不转发给消息发送者自己
        if event.get("_sender_channel") == self.channel_name:
            return
        # 如果标记了排除脚本，则脚本不接收
        if event.get("_exclude_scripts") and self.is_script:
            return

        await self.send(text_data=json.dumps({
            "type": "chat.message",
            "username": event["username"],
            "text": event["text"],
            "timestamp": event["timestamp"],
        }))

    async def script_broadcast(self, event):
        """转发脚本的广播消息"""
        await self.send(text_data=json.dumps({
            "type": "script.broadcast",
            "text": event["text"],
            "timestamp": event["timestamp"],
        }))

    async def system_info(self, event):
        """系统通知（加入/离开等）"""
        await self.send(text_data=json.dumps({
            "type": "system.info",
            "text": event["text"],
        }))

    async def script_private(self, event):
        """私聊消息（脚本 ↔ 用户）"""
        await self.send(text_data=json.dumps({
            "type": "script.private",
            "from": event["from"],
            "text": event["text"],
            "timestamp": event["timestamp"],
        }))

    async def user_list(self, event):
        """向客户端发送在线用户列表（广播给所有用户）"""
        await self.send(text_data=json.dumps({
            "type": "script.user_list",
            "users": event["users"],
        }))

    async def script_user_message(self, event):
        """脚本订阅查看的某用户消息"""
        await self.send(text_data=json.dumps({
            "type": "script.user_message",
            "username": event["username"],
            "text": event["text"],
            "timestamp": event["timestamp"],
        }))

    async def script_history(self, event):
        """脚本请求的消息历史"""
        await self.send(text_data=json.dumps({
            "type": "script.history",
            "username": event["username"],
            "messages": event["messages"],
        }))

    # =========================================================================
    # 辅助方法
    # =========================================================================
    async def broadcast_user_list(self):
        """向房间所有用户广播当前在线用户列表"""
        room = rooms.get(self.room_name)
        if not room:
            return

        users = [
            {"username": uname}
            for ch, uname in room["users"].items()
        ]

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "user_list",
                "users": users,
            },
        )

    async def _send_error(self, text: str):
        await self.send(text_data=json.dumps({
            "type": "error",
            "text": text,
        }))
