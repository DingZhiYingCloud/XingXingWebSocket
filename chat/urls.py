from django.urls import path

from chat import views

app_name = "chat"

urlpatterns = [
    path("", views.index, name="index"),
    path("room/<str:room_name>/", views.room, name="room"),
    path("script/<str:room_name>/", views.script_panel, name="script_panel"),
]
