from django.shortcuts import render


def index(request):
    """首页：房间选择和身份选择"""
    return render(request, "chat/index.html")


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
