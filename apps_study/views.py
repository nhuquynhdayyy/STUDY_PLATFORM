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
from django.http import JsonResponse
from datetime import timedelta
from django.db import models
from django.views import View
import random
import string

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        subjects = Subject.objects.filter(user=request.user)
        active_session = StudySession.objects.filter(user=request.user, status='active').first()
        
        # BỔ SUNG select_related('group_room')
        recent_history = StudySession.objects.filter(
            user=request.user, status='completed'
        ).select_related('subject', 'group_room').order_by('-end_time')[:5]
        
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
        ).select_related('subject', 'group_room').order_by('-end_time')

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
    
class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = 'statistics.html'

# class StudyStatsAPI(LoginRequiredMixin, View):
#     def get(self, request):
#         preset = request.GET.get('preset', '1week')
#         start_date_str = request.GET.get('start_date')
#         end_date_str = request.GET.get('end_date')

#         now = timezone.now()
#         # Đảm bảo dùng đúng filter như trang History
#         query_filter = models.Q(user=request.user, status='completed')

#         # Xử lý filter thời gian
#         if preset == '1day':
#             query_filter &= models.Q(end_time__gte=now - timedelta(days=1))
#         elif preset == '1week':
#             query_filter &= models.Q(end_time__gte=now - timedelta(days=7))
#         elif preset == '1month':
#             query_filter &= models.Q(end_time__gte=now - timedelta(days=30))
#         elif preset == 'custom' and start_date_str and end_date_str:
#             query_filter &= models.Q(end_time__date__range=[start_date_str, end_date_str])

#         # Aggregation
#         stats = StudySession.objects.filter(query_filter) \
#             .values('subject__name', 'subject__color') \
#             .annotate(total_sec=Sum('duration')) \
#             .order_by('-total_sec')

#         labels = []
#         chart_data = []
#         colors = []
#         table_data = []

#         for item in stats:
#             name = item['subject__name']
#             total_sec = item['total_sec'] or 0
            
#             # Tính toán hiển thị
#             minutes = round(total_sec / 60, 2)
#             hours = round(total_sec / 3600, 2)
            
#             labels.append(name)
#             # Nếu tổng thời gian quá ngắn, dùng Phút để vẽ biểu đồ cho rõ
#             chart_data.append(minutes if hours < 1 else hours)
#             colors.append(item['subject__color'] or "#3b82f6")
            
#             table_data.append({
#                 'subject': name,
#                 'display_time': f"{int(total_sec//60)}m {total_sec%60}s",
#                 'raw_minutes': minutes
#             })

#         return JsonResponse({
#             'labels': labels,
#             'unit': 'Minutes' if max(chart_data or [0]) < 60 else 'Hours',
#             'datasets': [{'data': chart_data, 'backgroundColor': colors}],
#             'table': table_data
#         })

class StudyStatsAPI(LoginRequiredMixin, View):
    def get(self, request):
        # Thống kê tổng hợp: Môn học (Solo) + Tên phòng (Group)
        # Chúng ta dùng Coalesce để lấy tên môn học, nếu không có thì lấy tên phòng
        from django.db.models.functions import Coalesce
        from django.db.models import F
        
        stats = StudySession.objects.filter(user=request.user, status='completed') \
            .annotate(display_name=Coalesce(F('subject__name'), F('group_room__name'))) \
            .values('display_name') \
            .annotate(total_sec=Sum('duration'))
        
        # Kết quả trả về gồm cả học một mình và học nhóm
        return JsonResponse(list(stats), safe=False)
    
class CreateSubjectView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        if name:
            # Tạo môn học mới gắn với user đang đăng nhập
            Subject.objects.create(user=request.user, name=name)
        return redirect('dashboard')

def group_room_detail(request, room_code):
    # Dùng select_related('host') để lấy thông tin chủ phòng nhanh nhất
    room = get_object_or_404(GroupRoom.objects.select_related('host'), room_code=room_code)
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
    
class CreateRoomView(LoginRequiredMixin, View):
    def post(self, request):
        room_name = request.POST.get('room_name', 'Unnamed Room')
        
        # Sinh room_code duy nhất (8 ký tự)
        def generate_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        code = generate_code()
        while GroupRoom.objects.filter(room_code=code).exists():
            code = generate_code()

        # Lưu vào Database
        room = GroupRoom.objects.create(
            name=room_name,
            room_code=code,
            host=request.user
        )
        
        # Điều hướng thẳng vào phòng vừa tạo
        return redirect('group_room_detail', room_code=code)

class GroupListView(LoginRequiredMixin, View):
    def get(self, request):
        # Lấy các phòng đang hoạt động
        active_rooms = GroupRoom.objects.filter(is_active=True).order_by('-created_at')
        return render(request, 'group_list.html', {'active_rooms': active_rooms})
    
class JoinGroupRoomView(View):
    def post(self, request):
        room_code = request.POST.get('room_code')
        return redirect('group_room_detail', room_code=room_code)
    
class LeaveRoomView(LoginRequiredMixin, View):
    def post(self, request, room_code):
        # 1. Sử dụng StudyService để kết thúc phiên học hiện tại của user
        # Hàm end_session chúng ta đã viết trước đó sẽ tìm session 'active' và đóng nó
        StudyService.end_session(request.user)
        
        # 2. Sau khi đã đóng session và lưu lịch sử, chuyển về dashboard
        return redirect('dashboard')