# apps_study/views.py
from django.views.generic import TemplateView, View, ListView, CreateView
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .services import StudyService, RoomService
from .models import Subject, StudySession, GroupRoom
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import UserRegisterForm, SubjectForm

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        subjects = Subject.objects.filter(user=request.user)
        active_session = StudySession.objects.filter(user=request.user, status='active').first()
        
        # Lấy 5 phiên gần nhất để hiện ở Dashboard (Recent Activity)
        recent_history = StudySession.objects.filter(
            user=request.user, status='completed'
        ).order_by('-end_time')[:5]
        
        context = {
            'subjects': subjects,
            'active_session': active_session,
            'recent_history': recent_history,
        }
        return render(request, 'dashboard.html', context)

class HistoryListView(LoginRequiredMixin, ListView):
    model = StudySession
    template_name = 'history.html'
    context_object_name = 'history'

    def get_queryset(self):
        return StudySession.objects.filter(
            user=self.request.user, status='completed'
        ).order_by('-end_time')

class StartStudyAction(LoginRequiredMixin, View):
    def post(self, request):
        subject_id = request.POST.get('subject_id')
        subject = Subject.objects.get(id=subject_id, user=request.user)
        
        with transaction.atomic():
            # Kiểm tra tránh tạo trùng (Race condition)
            if not StudySession.objects.filter(user=request.user, status='active').exists():
                StudySession.objects.create(user=request.user, subject=subject)
        
        return redirect('dashboard')

class StopStudyAction(LoginRequiredMixin, View):
    def post(self, request):
        with transaction.atomic():
            session = StudySession.objects.select_for_update().filter(user=request.user, status='active').first()
            if session:
                session.end_time = timezone.now()
                delta = session.end_time - session.start_time
                session.duration = int(delta.total_seconds())
                session.status = 'completed'
                session.save()
        
        return redirect('dashboard')
    
class StudyStatsAPI(LoginRequiredMixin, View):
    def get(self, request):
        data = StudySession.objects.filter(user=request.user, status='completed') \
            .values('subject__name') \
            .annotate(total_duration=Sum('duration'))
        
        labels = [item['subject__name'] for item in data]
        durations = [item['total_duration'] / 60 for item in data] # Đổi sang phút
        
        return JsonResponse({'labels': labels, 'data': durations})
    
class CreateSubjectView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        if name:
            # Tạo môn học mới gắn với user đang đăng nhập
            Subject.objects.create(user=request.user, name=name)
        return redirect('dashboard')

def group_room_detail(request, room_code):
    room = get_object_or_404(GroupRoom, room_code=room_code)
    return render(request, 'group_room.html', {'room': room})

class RegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        # Sau khi lưu user thành công, tự động đăng nhập luôn
        valid = super().form_valid(form)
        login(self.request, self.object)
        return valid
    
class SubjectListView(LoginRequiredMixin, ListView):
    model = Subject
    template_name = 'subjects.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        # Chỉ lấy môn học của chính người đang đăng nhập
        return Subject.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Gửi thêm form tạo mới vào trang danh sách
        context['form'] = SubjectForm()
        return context

class SubjectCreateView(LoginRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    success_url = reverse_lazy('subject_list')

    def form_valid(self, form):
        # Gán user hiện tại vào môn học trước khi lưu
        form.instance.user = self.request.user
        return super().form_valid(form)