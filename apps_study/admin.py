# apps_study/admin.py
from django.contrib import admin
from .models import User, Subject, StudySession, GroupRoom

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'start_time', 'status', 'duration')
    list_filter = ('status', 'user')