# apps_study/services.py
from django.db import transaction
from django.utils import timezone
from .models import StudySession, GroupRoom, RoomMember, Subject
from django.core.exceptions import ValidationError

class StudyService:
    @staticmethod
    @transaction.atomic
    def start_session(user, subject_id):
        active_session = StudySession.objects.select_for_update().filter(user=user, status='active').exists()
        if active_session:
            raise ValidationError("Bạn đã có một phiên học đang diễn ra.")
        subject = Subject.objects.get(id=subject_id, user=user)
        return StudySession.objects.create(user=user, subject=subject)

    @staticmethod
    @transaction.atomic
    def end_session(user):
        session = StudySession.objects.select_for_update().filter(user=user, status='active').first()
        if not session:
            return None # Hoặc raise ValidationError
        
        session.end_time = timezone.now()
        delta = session.end_time - session.start_time
        session.duration = int(delta.total_seconds())
        session.status = 'completed'
        session.save()
        return session
    
class RoomService:
    @staticmethod
    def create_room(host, name):
        code = GroupRoom.generate_room_code()
        room = GroupRoom.objects.create(host=host, name=name, room_code=code)
        # Tự động join host vào phòng
        RoomMember.objects.create(room=room, user=host)
        return room

    @staticmethod
    def join_room(user, room_code):
        try:
            room = GroupRoom.objects.get(room_code=room_code, is_active=True)
            return RoomMember.objects.get_or_create(room=room, user=user, leave_time__isnull=True)
        except GroupRoom.DoesNotExist:
            raise ValidationError("Mã phòng không tồn tại hoặc đã đóng.")