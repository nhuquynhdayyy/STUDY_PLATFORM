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

class StudySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0) # Tính bằng giây
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('completed', 'Completed')], default='active')

    class Meta:
        # Đảm bảo 1 user chỉ có 1 session active ở tầng DB
        constraints = [
            models.UniqueConstraint(fields=['user'], condition=models.Q(status='active'), name='one_active_session_per_user')
        ]

class GroupRoom(models.Model):
    name = models.CharField(max_length=200)
    room_code = models.CharField(max_length=10, unique=True, db_index=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_room_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class RoomMember(models.Model):
    room = models.ForeignKey(GroupRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    join_time = models.DateTimeField(auto_now_add=True)
    leave_time = models.DateTimeField(null=True, blank=True)