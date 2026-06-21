# XingXing WebSocket 聊天室

基于 Django Channels + Daphne 的 WebSocket 实时聊天应用。支持普通用户聊天、脚本管理员广播/查看/私聊等功能。

---

## 目录

- [快速启动](#快速启动)
- [页面导航](#页面导航)
- [核心功能](#核心功能)
- [WebSocket 协议参考](#websocket-协议参考)
- [前端页面详解](#前端页面详解)
- [项目架构](#项目架构)
- [常见问题](#常见问题)

---

## 快速启动

### 1. 启动服务

项目使用 **Daphne**（ASGI 服务器）而非 Django 自带的 runserver，因为 runserver 不支持 WebSocket。

```bash
# 在项目根目录下执行
.venv\Scripts\daphne -b 0.0.0.0 -p 8000 XingXingWebSocket.asgi:application
```

参数说明：
- `-b 0.0.0.0` — 监听所有网络接口（局域网其他设备可访问）
- `-p 8000` — 端口号
- `XingXingWebSocket.asgi:application` — ASGI 应用入口

启动成功日志：
```
INFO     Starting server at tcp:port=8000:interface=0.0.0.0
INFO     Listening on TCP address 0.0.0.0:8000
```

### 2. 打开首页

浏览器访问：**http://localhost:8000/xiaoying/admin/**

> 根域名 `/` 仅显示简单提示页，聊天入口必须通过 `/xiaoying/admin/` 访问。

---

## 页面导航

| 页面 | URL | 说明 |
|---|---|---|
| 首页（入口） | `/xiaoying/admin/` | 选择房间和身份 |
| 用户聊天室 | `/xiaoying/admin/room/<房间名>/?username=<用户名>` | 普通用户聊天 |
| 脚本管理面板 | `/xiaoying/admin/script/<房间名>/` | 脚本管理员后台 |
| Django 管理后台 | `/admin/` | Django 原生后台 (需创建管理员) |

---

## 核心功能

### 场景说明

整个系统基于 **房间（Room）** 的概念。同一房间内的用户才能互相通信。脚本（Script）是一种特殊角色，拥有管理权限。

### 普通用户功能

1. **加入房间** — 在首页输入房间名和用户名，或直接访问 URL
2. **发送消息** — 输入框输入消息，按 Enter 或点击"发送"
3. **实时接收** — 房间内其他用户的消息会实时显示
4. **在线用户** — 右侧显示当前房间的在线用户列表

> 用户发送的消息**默认不会**被脚本收到，确保用户之间的聊天隐私。

### 脚本管理员功能

脚本面板是三栏布局：

1. **左栏 — 在线用户列表**
   - 显示房间所有在线用户
   - 点击用户旁的 **"查看"** 按钮，订阅该用户的所有实时消息
   - 点击 **"私聊"** 按钮，进入与该用户的一对一私聊
   - 点击 **"刷新"** 按钮，刷新用户列表

2. **中栏 — 用户消息面板**
   - 选择一个用户"查看"后，会显示该用户的消息历史
   - 该用户后续发送的新消息会**实时推送**到这里
   - 下方可输入**广播消息**，发送给房间所有用户

3. **右栏 — 私聊面板**
   - 在用户列表中点击"私聊"选择对象
   - 输入消息后发送，对方会实时收到
   - 脚本自己也能看到发送回执

---

## WebSocket 协议参考

> 适用于需要编写脚本或自动化工具的开发者。

### 连接地址

```
ws://<host>:<port>/ws/chat/<room_name>/?username=<用户名>          # 普通用户
ws://<host>:<port>/ws/chat/<room_name>/?type=script                # 脚本管理员
```

### 客户端 → 服务端消息

#### 普通用户

```json
// 发送聊天消息
{
  "type": "chat.message",
  "text": "大家好！"
}
```

#### 脚本管理员

```json
// 1. 广播消息给房间所有用户
{
  "type": "script.broadcast",
  "text": "系统公告：即将维护"
}

// 2. 查看用户列表
{
  "type": "script.list_users"
}

// 3. 订阅查看某个用户的消息（实时推送）
{
  "type": "script.view_user",
  "username": "小明"
}

// 4. 取消订阅查看
{
  "type": "script.unview_user",
  "username": "小明"
}

// 5. 私聊某个用户
{
  "type": "script.private",
  "target": "小明",
  "text": "你好，我是管理员"
}

// 6. 查看某个用户的消息历史
{
  "type": "script.history",
  "username": "小明"    // 不传 username 则返回全部消息历史
}
```

### 服务端 → 客户端消息

```json
// 1. 聊天消息（用户 → 用户）
{
  "type": "chat.message",
  "username": "小明",
  "text": "大家好！",
  "timestamp": "14:30:25"
}

// 2. 脚本广播
{
  "type": "script.broadcast",
  "text": "系统公告：即将维护",
  "timestamp": "14:30:25"
}

// 3. 系统通知（加入/离开）
{
  "type": "system.info",
  "text": "✨ 小明 加入了房间"
}

// 4. 用户列表（脚本专用）
{
  "type": "script.user_list",
  "users": [
    {"username": "小明", "channel_name": "..."},
    {"username": "小红", "channel_name": "..."}
  ]
}

// 5. 订阅的用户消息推送（脚本专用）
{
  "type": "script.user_message",
  "username": "小明",
  "text": "有人在吗？",
  "timestamp": "14:30:25"
}

// 6. 私聊消息
{
  "type": "script.private",
  "from": "脚本管理员",     // 发给用户
  "text": "你好，我是管理员",
  "timestamp": "14:30:25"
}
// 或
{
  "type": "script.private",
  "from": "→ 小明",         // 回显给脚本自己
  "text": "你好，我是管理员",
  "timestamp": "14:30:25"
}

// 7. 消息历史（脚本专用）
{
  "type": "script.history",
  "username": "小明",
  "messages": [
    {"username": "小明", "text": "大家好", "timestamp": "14:00:01"},
    {"username": "小明", "text": "有人在吗", "timestamp": "14:00:05"}
  ]
}

// 8. 错误消息
{
  "type": "error",
  "text": "用户 'xxx' 不在房间中"
}
```

---

## 前端页面详解

### 首页 (`/xiaoying/admin/`)

- **左侧"用户登录"**：输入房间名和用户名，点击进入聊天室
- **右侧"脚本管理"**：输入房间名，点击进入管理面板
- **底部"功能说明"**：列出了用户和脚本各自的能力说明

### 用户聊天室 (`/xiaoying/admin/room/<name>/`)

- **消息区域**：显示聊天消息，不同样式区分：
  - 蓝色气泡（左） — 其他人的消息
  - 绿色气泡（右） — 自己的消息
  - 紫色居中 — 系统通知（用户加入/离开）
  - 紫色带边框 — 脚本广播
  - 黄色边框 — 脚本私聊消息
- **输入框**：输入消息后按 Enter 或点击"发送"
- **连接状态**：右上角显示连接/断开/重连状态
- **断线重连**：连接断开后自动重连（3秒间隔）

### 脚本管理面板 (`/xiaoying/admin/script/<name>/`)

- **左栏**：
  - 在线用户列表，每个用户有"查看"和"私聊"按钮
  - 当前正在查看的用户列表，可"取消查看"
- **中栏**：
  - 被查看用户的消息历史和实时推送
  - 广播消息输入框
- **右栏**：
  - 私聊消息记录
  - 私聊输入框

---

## 项目架构

```
XingXingWebSocket/
├── chat/                              # Django APP - 聊天应用
│   ├── consumers.py                   # WebSocket 核心业务逻辑
│   ├── routing.py                     # WebSocket 路由配置
│   ├── views.py                       # HTTP 页面视图
│   ├── urls.py                        # HTTP URL 路由
│   └── templates/chat/                # 前端模板
│       ├── base.html                  # 母版页（全局样式/布局/导航）
│       ├── index.html                 # 首页
│       ├── room.html                  # 用户聊天室
│       └── script.html                # 脚本管理面板
├── XingXingWebSocket/                 # Django 项目配置
│   ├── asgi.py                        # ASGI 入口（集成 WebSocket 路由）
│   ├── settings.py                    # 项目配置
│   ├── urls.py                        # 根 URL 路由
│   └── wsgi.py                        # WSGI 入口
├── manage.py                          # Django 管理脚本
├── .env                               # 环境变量
└── requirements.txt                   # Python 依赖
```

### 核心设计

| 组件 | 作用 |
|---|---|
| `ChatConsumer` | 处理 WebSocket 连接/断开/消息，管理房间状态 |
| `InMemoryChannelLayer` | Channels 的通信层（开发环境用内存，生产建议换 Redis） |
| `_get_or_create_room()` | 惰性创建房间，自动清理空房间 |
| `script_viewing` | 管理脚本对用户的订阅关系 |

### 数据流

```
用户A 发消息
  → ChatConsumer._handle_user_message()
    → 存到 room["messages"] 历史缓冲
    → group_send("chat.message") 给房间其他用户（排除脚本）
    → 遍历 script_viewing，如果有脚本在查看该用户，单独转发

脚本 广播消息
  → ChatConsumer._handle_script_message("script.broadcast")
    → group_send("script.broadcast") 给房间所有用户

脚本 私聊用户
  → ChatConsumer._handle_script_message("script.private")
    → channel_layer.send() 直接发给目标用户 channel
    → 同时回显给脚本自己
```

---

## 宝塔面板部署指南（Ubuntu）

> 如果你是第一次接触服务器，别担心。下面每一步都写得非常详细，跟着做就行。

---

### 基础概念通俗解释

**反向代理是什么？**
> 你的网站跑在服务器上，直接让用户访问不安全。Nginx 就像前台保安——用户访问保安，保安把请求转给你程序。好处：保安可以处理 SSL 证书（HTTPS）、防攻击、做缓存。**WebSocket 也需要保安特殊处理**，否则连接不上。

**Redis 是什么？**
> 一个高性能的内存数据库。你的聊天项目用 `InMemoryChannelLayer`，数据存在 Python 进程内存里。如果部署多个 Daphne 进程（为了性能），用户A连到进程1，用户B连到进程2，消息就传不过去了。Redis 作为**中转站**，让所有进程共享消息。**如果你只开一个进程，InMemory 也够用。**

---

### 准备工作

在宝塔面板中安装好以下软件（宝塔后台 → 软件商店 → 一键安装）：

| 软件 | 用途 | 是否必须 |
|---|---|---|
| **Nginx** | 反向代理 + HTTPS | ✅ 必须 |
| **Python 项目部署**（项目管理器） | 管理 Python 应用 | ✅ 必须 |
| **Redis** | 消息中转（可选，推荐） | ⬜ 可选 |

---

### 第一步：上传项目到服务器

**方式一：宝塔面板上传（推荐新手）**

1. 在宝塔后台 → 文件 → 进入 `/www/wwwroot/` 目录
2. 创建一个文件夹，例如 `websocket_chat`
3. 把你本地项目里的文件全部上传进去（或者压缩成 zip 上传后解压）
4. 上传后不需要 `.venv` 文件夹（本地虚拟环境），删掉它

> 需要上传的文件清单：
> ```
> chat/
> XingXingWebSocket/
> manage.py
> requirements.txt
> .env
> ```

**方式二：Git 拉取（如果你会用 Git）**

```bash
cd /www/wwwroot/
git clone <你的仓库地址> websocket_chat
```

---

### 第二步：配置 `.env` 文件

在宝塔文件管理中找到 `.env`，编辑修改：

```
SECRET_KEY=把这里替换成一个随机字符串
DEBUG=False
ALLOWED_HOSTS=你的域名.com,www.你的域名.com
CSRF_TRUSTED_ORIGINS=https://你的域名.com,https://www.你的域名.com
```

**如何生成 SECRET_KEY？**

在服务器 SSH 终端执行：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

把输出的字符串复制粘贴到 `.env` 的 `SECRET_KEY=` 后面。

---

### 第三步：创建 Python 虚拟环境 + 安装依赖

打开宝塔的 **SSH 终端**（或使用 XShell、Putty 等），执行以下命令：

```bash
# 1. 进入项目目录
cd /www/wwwroot/websocket_chat

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 升级 pip（可选，避免警告）
pip install --upgrade pip

# 5. 安装依赖
pip install -r requirements.txt

# 6. 如果打算用 Redis（推荐），安装 channels_redis
pip install channels_redis

# 7. 收集静态文件（把 CSS/JS 集中到 staticfiles 目录）
python manage.py collectstatic --noinput

# 8. 执行数据库迁移
python manage.py migrate
```

> ⚠️ 注意：这里是 `venv` 不是 `.venv`（宝塔的 Python 项目管理器默认用 `venv`）。如果你后面用宝塔的"Python 项目管理器"来自动创建环境，可以跳过第2-5步。

---

### 第四步：配置 Supervisor 守护进程

Supervisor 的作用：**如果 Daphne 进程突然挂了，它会自动重启。**

**方法一：用宝塔的 Supervisor（推荐）**

1. 宝塔后台 → 软件商店 → 搜索 `Supervisor` → 安装
2. 安装后进入 Supervisor 管理页面 → 添加守护进程

   | 设置项 | 填写内容 |
   |---|---|
   | 名称 | `websocket_chat` |
   | 启动用户 | `root` |
   | 运行目录 | `/www/wwwroot/websocket_chat` |
   | 启动命令 | `/www/wwwroot/websocket_chat/venv/bin/daphne -b 127.0.0.1 -p 8000 XingXingWebSocket.asgi:application` |
   | 进程数 | `1` |

   > `-b 127.0.0.1` 表示只监听本地，不对外开放端口（由 Nginx 转发给用户的请求）。

3. 点击"提交"→ 状态变成 **Running** 即成功

**方法二：手动配置（如果宝塔没装 Supervisor）**

SSH 执行：

```bash
# 安装 supervisor
apt install supervisor -y

# 创建配置文件
cat > /etc/supervisor/conf.d/websocket_chat.conf << 'EOF'
[program:websocket_chat]
command=/www/wwwroot/websocket_chat/venv/bin/daphne -b 127.0.0.1 -p 8000 XingXingWebSocket.asgi:application
directory=/www/wwwroot/websocket_chat
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/www/wwwroot/websocket_chat/logs/daphne.log
stderr_logfile=/www/wwwroot/websocket_chat/logs/daphne_err.log
EOF

# 创建日志目录
mkdir -p /www/wwwroot/websocket_chat/logs

# 重新加载配置并启动
supervisorctl reread
supervisorctl update
supervisorctl start websocket_chat

# 查看运行状态（看到 RUNNING 则成功）
supervisorctl status websocket_chat
```

---

### 第五步：配置 Nginx 反向代理（关键！）

这一步是**最容易出错的地方**，请仔细核对。

**用宝塔建站点：**

1. 宝塔后台 → 网站 → 添加站点
2. 填入你的域名，PHP 版本选"纯静态"，提交
3. 进入站点设置 → **反向代理** → 添加反向代理

   | 设置项 | 填写内容 |
   |---|---|
   | 代理名称 | `websocket` |
   | 目标 URL | `http://127.0.0.1:8000` |
   | 是否缓存 | 否 |

4. 进入站点设置 → **配置文件**（不是反向代理的配置文件，是站点本身的）

   **在 `location ~ .*\.(gif|jpg|jpeg|png|bmp|swf)$` 这一行之前**，添加以下内容：

   ```nginx
   # WebSocket 反向代理（关键配置！）
   location /ws/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 86400s;
   }

   # 静态文件直接由 Nginx 提供服务（提高性能）
   location /static/ {
       alias /www/wwwroot/websocket_chat/staticfiles/;
       expires 30d;
       access_log off;
   }
   ```

5. 点击"保存"，然后点击"重载配置"

> 🔑 **关键要点：**
> - `location /ws/` 这个路径必须和项目里 `routing.py` 定义的路径前缀一致
> - `proxy_read_timeout 86400s` 是 WebSocket 长连接的超时时间，设长一点（24小时）
> - 别忘了 `Upgrade` 和 `Connection` 头，否则 WebSocket 连接不上

**完整的 Nginx 配置示例（如果你懂可以对照着看）：**

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    # 静态文件（含 CORS 跨域支持）
    location /static/ {
        alias /www/wwwroot/websocket_chat/staticfiles/;
        expires 30d;
        add_header Access-Control-Allow-Origin "https://noah-admin.site" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
    }
    
    # WebSocket（关键！）
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }
    
    # 聊天应用（入口受保护路径）
    location /xiaoying/admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 根域名提示页（防止陌生人直接访问聊天）
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 第六步：开启 HTTPS（强烈推荐）

1. 宝塔后台 → 网站 → 选择你的站点 → SSL
2. 选择"Let's Encrypt" → 勾选域名 → 申请
3. 申请成功后，开启"强制 HTTPS"
4. 更新 `.env` 中的 `CSRF_TRUSTED_ORIGINS`，把 `http://` 改为 `https://`

---

### 第七步：配置 Redis（可选，但推荐）

**Redis 是干什么的？**
> 你的聊天项目有房间、用户列表、消息历史，目前存在 Python 内存里。如果部署多个 Daphne 进程（比如为了应对更多人同时在线），消息就传不通了。Redis 作为中央存储，让所有进程共享数据。

**配置步骤：**

1. 宝塔后台 → 软件商店 → 找到 Redis → 安装
2. 修改 `settings.py` 中的 `CHANNEL_LAYERS`：

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

3. 重启 Supervisor（宝塔后台 → Supervisor → 找到 `websocket_chat` → 重启）

---

### 验证部署是否成功

**1. 检查 Daphne 是否运行**

```bash
supervisorctl status websocket_chat
# 应该显示 RUNNING
```

**2. 检查端口监听**

```bash
netstat -tlnp | grep 8000
# 应该看到 daphne 在 127.0.0.1:8000 监听
```

**3. 访问首页**

浏览器打开 `https://你的域名.com/xiaoying/admin/`，应该能看到聊天室首页。

**4. 测试 WebSocket 连接**

打开浏览器开发者工具（F12）→ Console，输入：

```javascript
// 普通用户测试连接
let ws = new WebSocket('wss://你的域名.com/ws/chat/lobby/?username=测试用户');
ws.onopen = () => console.log('WebSocket 连接成功 ✅');
ws.onerror = (e) => console.log('连接失败 ❌', e);
```

如果 Console 显示 "连接成功 ✅"，说明 WebSocket 也正常工作了。

---

### 常见部署问题

#### Q: 访问页面 502 Bad Gateway

原因：Daphne 没有启动，或者 Nginx 找不到 Daphne。

排查：
```bash
supervisorctl status websocket_chat   # 检查 Daphne 是否运行
cat /www/wwwroot/websocket_chat/logs/daphne_err.log  # 查看错误日志
```

#### Q: WebSocket 连接报 400/404

原因：Nginx 配置缺少 WebSocket 升级头，或者路径不匹配。

检查 Nginx 配置中是否有：
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

#### Q: WebSocket 连接后很快就断开

原因：`proxy_read_timeout` 设置太短。

解决：在 WebSocket 的 location 块中设置 `proxy_read_timeout 86400s;`

#### Q: 页面能打开，但 WebSocket 连不上

可能原因：HTTPS 页面不能连接非安全的 WebSocket（`ws://`），必须用 `wss://`。

如果你用 HTTPS，前端代码会自动使用 `wss://`。如果不确定，打开浏览器 F12 → Console 看错误信息。

#### Q: 多人聊天消息互相收不到

原因：用 InMemoryChannelLayer 但启动了多个 Daphne 进程。

解决方案：
1. 在 Supervisor 配置中把进程数改为 `1`
2. 或者安装 Redis，改用 `channels_redis`（推荐）

---

### 日常维护命令

```bash
# 查看 Daphne 运行状态
supervisorctl status websocket_chat

# 重启 Daphne（修改代码后需要重启）
supervisorctl restart websocket_chat

# 查看 Daphne 日志
tail -f /www/wwwroot/websocket_chat/logs/daphne.log

# 进入项目目录
cd /www/wwwroot/websocket_chat

# 激活虚拟环境
source venv/bin/activate

# 查看端口占用
netstat -tlnp | grep 8000

# 查看 Nginx 错误日志
tail -f /www/wwwroot/websocket_chat/logs/nginx_error.log
```

---


