# apps_study/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import random
import string

class User(AbstractUser):
    # Mục tiêu giờ học mỗi tuần (mặc định 20 giờ)
    weekly_goal = models.PositiveIntegerField(default=20) 

class Subject(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_subjects')
    name = models.CharField(max_length=100)
    # Lưu mã màu để hiển thị giao diện cho đẹp
    color = models.CharField(max_length=7, default="#3b82f6") 
    created_at = models.DateTimeField(auto_now_add=True)
    # Thêm trường tiến độ học tập (0-100%)
    progress = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class GroupRoom(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=10, unique=True, db_index=True)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StudySession(models.Model):
    SESSION_TYPE = [('solo', 'Solo'), ('group', 'Group')]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE, default='solo')
    
    # Nếu là solo thì có subject, nếu là group thì có room
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True)
    group_room = models.ForeignKey(GroupRoom, on_delete=models.SET_NULL, null=True, blank=True)
    
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0) # Tính theo giây
    status = models.CharField(max_length=10, default='active') # active/completed

    name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    color_snapshot = models.CharField(max_length=7, null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    @property
    def display_name(self):
        # Ưu tiên lấy từ snapshot nếu có (để giữ tên khi subject/room bị xóa)
        if self.name_snapshot:
            if self.session_type == 'group':
                return f"[Group] {self.name_snapshot}"
            return self.name_snapshot
        
        # Fallback cho dữ liệu cũ chưa có snapshot
        if self.session_type == 'solo' and self.subject:
            return self.subject.name
        if self.session_type == 'group' and self.group_room:
            return f"[Group] {self.group_room.name}"
        return "Unknown Session"

    @property
    def get_color(self):
        # Ưu tiên lấy màu từ snapshot
        if self.color_snapshot:
            return self.color_snapshot
        
        # Fallback
        if self.session_type == 'solo' and self.subject:
            return self.subject.color
        return "#1e293b" # Màu mặc định cho Group
    
    @property
    def formatted_duration(self):
        """Chuyển đổi giây sang định dạng hh : mm : ss"""
        total_seconds = self.duration
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            # Định dạng: 01h 02m 05s
            return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
        else:
            # Định dạng: 05m 02s (Nếu dưới 1 tiếng thì không hiện 00h)
            return f"{minutes:02d}m {seconds:02d}s"

class RoomMember(models.Model):
    room = models.ForeignKey(GroupRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    join_time = models.DateTimeField(auto_now_add=True)
    leave_time = models.DateTimeField(null=True, blank=True)