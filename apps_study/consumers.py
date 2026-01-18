# apps_study/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import GroupRoom, StudySession

class StudyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'study_{self.room_code}'
        self.user = self.scope['user']

        if self.user.is_authenticated:
            # Tạo session học nhóm cho user này
            self.session_id = await self.create_session()
            
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            
            # Thông báo có người mới vào để các bên thiết lập WebRTC
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "user_joined", "user": self.user.username, "channel_name": self.channel_name}
            )

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            # Lưu end_time và tính duration
            await self.end_session()
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Gửi tín hiệu WebRTC (offer, answer, candidate) tới người nhận cụ thể
        target_channel = data.get('target')
        
        await self.channel_layer.send(target_channel, {
            "type": "signal_message",
            "payload": data,
            "sender_channel": self.channel_name,
            "sender_name": self.user.username
        })

    async def signal_message(self, event):
        # Chuyển tiếp tín hiệu WebRTC tới trình duyệt
        await self.send(text_data=json.dumps({
            "payload": event['payload'],
            "sender_channel": event['sender_channel'],
            "sender_name": event['sender_name']
        }))

    async def user_joined(self, event):
        if event['channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps({
                "type": "new_peer",
                "channel_name": event['channel_name'],
                "username": event['user']
            }))

    @database_sync_to_async
    def create_session(self):
        room = GroupRoom.objects.get(room_code=self.room_code)
        session = StudySession.objects.create(
            user=self.user,
            session_type='group',
            group_room=room,
            status='active'
        )
        return session.id

    @database_sync_to_async
    def end_session(self):
        session = StudySession.objects.get(id=self.session_id)
        session.end_time = timezone.now()
        session.duration = int((session.end_time - session.start_time).total_seconds())
        session.status = 'completed'
        session.save()