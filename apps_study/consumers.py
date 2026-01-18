# apps_study/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import GroupRoom, StudySession, RoomMember

class StudyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'study_{self.room_code}'
        self.user = self.scope['user']

        if self.user.is_authenticated:
            # 1. Cập nhật trạng thái vào phòng (RoomMember)
            await self.update_room_membership(status='join')
            
            # 2. Tạo session học tập (Code cũ của bạn)
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
            # 3. Cập nhật trạng thái rời phòng (RoomMember) - QUAN TRỌNG NHẤT
            await self.update_room_membership(status='leave')
            
            # 4. Lưu session học tập (Code cũ của bạn)
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
    def update_room_membership(self, status):
        """Cập nhật bảng RoomMember để đếm số người Online chính xác"""
        room = GroupRoom.objects.get(room_code=self.room_code)
        
        if status == 'join':
            # Nếu đã có bản ghi chưa rời đi (do lỗi mạng trước đó), đóng nó lại
            RoomMember.objects.filter(room=room, user=self.user, leave_time__isnull=True).update(leave_time=timezone.now())
            # Tạo bản ghi mới khi vào phòng
            RoomMember.objects.create(room=room, user=self.user)
        
        elif status == 'leave':
            # Đánh dấu thời gian rời đi khi ngắt kết nối WebSocket (tắt tab/trình duyệt)
            RoomMember.objects.filter(room=room, user=self.user, leave_time__isnull=True).update(leave_time=timezone.now())

    @database_sync_to_async
    def create_session(self):
        room = GroupRoom.objects.get(room_code=self.room_code)
        session = StudySession.objects.create(
            user=self.user,
            session_type='group',
            group_room=room,
            name_snapshot=room.name,      # LƯU TÊN PHÒNG LẠI
            color_snapshot="#1e293b",     # MÀU MẶC ĐỊNH CỦA GROUP
            status='active'
        )
        return session.id

    @database_sync_to_async
    def end_session(self):
        try:
            session = StudySession.objects.get(id=self.session_id)
            session.end_time = timezone.now()
            session.duration = int((session.end_time - session.start_time).total_seconds())
            session.status = 'completed'
            session.save()
        except Exception:
            pass