# apps_study/views.py
from django.views.generic import TemplateView, View, ListView, CreateView
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .services import StudyService, RoomService
from .models import Subject, StudySession, GroupRoom, RoomMember
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from django.urls import reverse_lazy, reverse
from .forms import UserRegisterForm, SubjectForm
from django.http import JsonResponse
from datetime import timedelta
from django.db import models
from django.views import View
import random
import string
from django.views.generic.edit import UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q

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
        # 1. Lấy loại history từ URL (?type=solo hoặc group), mặc định là solo
        session_type = self.request.GET.get('type', 'solo')
        
        # 2. Lọc dữ liệu theo User, trạng thái hoàn thành và loại phiên học
        return StudySession.objects.filter(
            user=self.request.user, 
            status='completed',
            session_type=session_type
        ).select_related('subject', 'group_room').order_by('-end_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 3. Gửi 'current_type' về template để active tab tương ứng
        context['current_type'] = self.request.GET.get('type', 'solo')
        return context

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

class StudyStatsAPI(LoginRequiredMixin, View):
    def get(self, request):
        from django.db.models import Sum, Q, F, Value
        from django.db.models.functions import Coalesce

        # 1. Lấy tham số (Thêm tham số 'type')
        stat_type = request.GET.get('type', 'subject')  # 'subject' hoặc 'group'
        preset = request.GET.get('preset', '1week')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # 2. Bộ lọc cơ bản
        now = timezone.now()
        query_filter = Q(user=request.user, status='completed')

        # 3. Phân tách logic gom nhóm theo yêu cầu
        if stat_type == 'group':
            query_filter &= Q(session_type='group')
            group_field = 'group_room__name'
            color_field = Value('#1e293b') # Màu slate-800 đặc trưng cho Group
            label_title = "Phòng học"
        else:
            query_filter &= Q(session_type='solo')
            group_field = 'subject__name'
            color_field = 'subject__color'
            label_title = "Môn học"

        # 4. Lọc thời gian (Giữ nguyên logic cũ)
        if preset == '1day':
            query_filter &= Q(end_time__gte=now - timedelta(days=1))
        elif preset == '1week':
            query_filter &= Q(end_time__gte=now - timedelta(days=7))
        elif preset == '1month':
            query_filter &= Q(end_time__gte=now - timedelta(days=30))
        elif preset == 'custom' and start_date_str and end_date_str:
            query_filter &= Q(end_time__date__range=[start_date_str, end_date_str])

        # 5. Query Aggregation
        stats = StudySession.objects.filter(query_filter) \
            .values(display_name=F(group_field), display_color=Coalesce(color_field, Value('#3b82f6'))) \
            .annotate(total_sec=Sum('duration')) \
            .order_by('-total_sec')

        # 6. Định dạng dữ liệu trả về cho Chart.js và Table
        labels = []
        data_points = []
        colors = []
        table_data = []

        for item in stats:
            name = item['display_name'] or "Chưa đặt tên"
            total_sec = item['total_sec'] or 0
            
            # Quy đổi thời gian
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            s = int(total_sec % 60)
            
            labels.append(name)
            data_points.append(round(total_sec / 60, 1)) # Vẽ biểu đồ theo đơn vị Phút
            colors.append(item['display_color'])
            
            table_data.append({
                'name': name,
                'color': item['display_color'],
                'display_time': f"{h}h {m}m {s}s",
            })

        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'data': data_points,
                'backgroundColor': colors,
            }],
            'table': table_data,
            'type_label': label_title
        })
    
class CreateSubjectView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        if name:
            # Tạo môn học mới gắn với user đang đăng nhập
            Subject.objects.create(user=request.user, name=name)
        return redirect('dashboard')

def group_room_detail(request, room_code):
    room = GroupRoom.objects.filter(room_code=room_code).first()
    if not room:
        from django.contrib import messages
        messages.error(request, "Phòng học không tồn tại!")
        return redirect('dashboard')
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
        # Đếm số member thực tế đang Online trong từng phòng
        active_rooms = GroupRoom.objects.filter(is_active=True).annotate(
            online_count=Count('members', filter=Q(members__leave_time__isnull=True))
        ).order_by('-created_at')
        
        return render(request, 'group_list.html', {'active_rooms': active_rooms})
    
class JoinGroupRoomView(View):
    def post(self, request):
        room_code = request.POST.get('room_code', '').strip()
        
        # 1. Kiểm tra phòng có tồn tại không
        room = GroupRoom.objects.filter(room_code=room_code, is_active=True).first()
        
        if not room:
            # Trả về lỗi JSON thay vì văng trang 404
            return JsonResponse({
                'success': False, 
                'message': f'Mã phòng "{room_code}" không tồn tại hoặc đã bị đóng!'
            }, status=404)
        
        # 2. Nếu tồn tại, trả về URL để Frontend tự chuyển hướng
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('group_room_detail', args=[room_code])
        })

    
class LeaveRoomView(LoginRequiredMixin, View):
    def post(self, request, room_code):
        # 1. Kết thúc session học tập (Logic cũ của bạn)
        StudyService.end_session(request.user)
        
        # 2. BỔ SUNG: Cập nhật leave_time cho thành viên này trong bảng RoomMember
        room = get_object_or_404(GroupRoom, room_code=room_code)
        RoomMember.objects.filter(
            room=room, 
            user=request.user, 
            leave_time__isnull=True
        ).update(leave_time=timezone.now())
        
        # 3. (Tùy chọn) Nếu không còn ai trong phòng, có thể tắt is_active của phòng
        if not RoomMember.objects.filter(room=room, leave_time__isnull=True).exists():
            room.is_active = False # Hoặc giữ True nếu muốn phòng luôn mở
            room.save()

        return redirect('dashboard')
    
class SubjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'subject_edit.html' # Hoặc reuse form nếu muốn
    success_url = reverse_lazy('subject_list')

    def test_func(self):
        # Kiểm tra quyền: subject này phải thuộc về user đang đăng nhập
        subject = self.get_object()
        return subject.user == self.request.user

class SubjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Subject
    success_url = reverse_lazy('subject_list')

    def test_func(self):
        subject = self.get_object()
        return subject.user == self.request.user

    # Khi xóa, Django mặc định sẽ xóa subject. 
    # Do trong model StudySession ta đã đặt on_delete=models.SET_NULL, 
    # nên lịch sử học tập sẽ không bị mất mà chỉ chuyển subject thành NULL (Unknown).

# 1. API lấy thông tin Subject để điền vào Form
@login_required
def subject_detail_api(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    return JsonResponse({
        "id": subject.id,
        "name": subject.name,
        "color": subject.color
    })

# 2. API cập nhật Subject
@login_required
@require_http_methods(["POST"])
def subject_update_api(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    name = request.POST.get('name')
    color = request.POST.get('color')
    
    if name and color:
        subject.name = name
        subject.color = color
        subject.save()
        return JsonResponse({"status": "success", "name": name, "color": color})
    
    return JsonResponse({"status": "error", "message": "Dữ liệu không hợp lệ"}, status=400)

# 1. API Lấy thông tin phòng để điền vào Modal
@login_required
def group_detail_api(request, room_code):
    room = get_object_or_404(GroupRoom, room_code=room_code)
    # Kiểm tra quyền Host
    if room.host != request.user:
        return JsonResponse({"error": "Bạn không có quyền"}, status=403)
    
    return JsonResponse({
        "name": room.name,
        "room_code": room.room_code
    })

# 2. API Cập nhật thông tin phòng
@login_required
@require_http_methods(["POST"])
def group_update_api(request, room_code):
    room = get_object_or_404(GroupRoom, room_code=room_code)
    if room.host != request.user:
        return JsonResponse({"error": "Chỉ Host mới có quyền sửa"}, status=403)
    
    new_name = request.POST.get('name')
    if new_name:
        room.name = new_name
        room.save()
        return JsonResponse({"status": "success", "new_name": new_name})
    return JsonResponse({"status": "error"}, status=400)

# 3. View Xóa phòng (Sử dụng Class-based để tận dụng UserPassesTestMixin)
class GroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = GroupRoom
    slug_field = 'room_code'
    slug_url_kwarg = 'room_code'
    success_url = reverse_lazy('group_list')

    def test_func(self):
        room = self.get_object()
        return room.host == self.request.user
    
    # Do StudySession có group_room = models.SET_NULL, 
    # nên xóa GroupRoom thì lịch sử học tập (duration) vẫn được bảo toàn.