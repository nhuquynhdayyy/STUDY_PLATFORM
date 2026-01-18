from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/study/(?P<room_code>\w+)/$', consumers.StudyConsumer.as_asgi()),
]