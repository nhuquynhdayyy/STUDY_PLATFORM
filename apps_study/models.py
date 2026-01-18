# apps_study/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import random
import string

class User(AbstractUser):
    pass # Để trống để mở rộng sau này

class Subject(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_subjects')
    name = models.CharField(max_length=100)
    # Lưu mã màu để hiển thị giao diện cho đẹp
    color = models.CharField(max_length=7, default="#3b82f6") 
    created_at = models.DateTimeField(auto_now_add=True)

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

    class Meta:
        ordering = ['-start_time']

    @property
    def display_name(self):
        """Trả về tên môn học nếu học solo, hoặc tên phòng nếu học nhóm"""
        if self.session_type == 'solo' and self.subject:
            return self.subject.name
        if self.session_type == 'group' and self.group_room:
            return f"[Group] {self.group_room.name}"
        return "Unknown Session"

    @property
    def get_color(self):
        """Trả về màu của môn học hoặc màu mặc định cho phòng họp nhóm"""
        if self.session_type == 'solo' and self.subject:
            return self.subject.color
        return "#1e293b" # Màu slate-800 cho Group

class RoomMember(models.Model):
    room = models.ForeignKey(GroupRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    join_time = models.DateTimeField(auto_now_add=True)
    leave_time = models.DateTimeField(null=True, blank=True)