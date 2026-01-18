from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import DashboardView, StartStudyAction, StatisticsView, StopStudyAction, CreateSubjectView, HistoryListView, RegisterView, StudyStatsAPI, SubjectListView, SubjectCreateView, GroupListView, CreateRoomView, group_room_detail, JoinGroupRoomView, LeaveRoomView
from django.views import View

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),

    # Core
    path('', DashboardView.as_view(), name='dashboard'),
    path('start-study/', StartStudyAction.as_view(), name='start_study'),
    path('stop-study/', StopStudyAction.as_view(), name='stop_study'),
    path('subject/create/', CreateSubjectView.as_view(), name='create_subject'),
    path('history/', HistoryListView.as_view(), name='history'),
    path('subjects/', SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', SubjectCreateView.as_view(), name='subject_create'),
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('api/stats/', StudyStatsAPI.as_view(), name='api_stats'),
    path('groups/', GroupListView.as_view(), name='group_list'),
    path('groups/create/', CreateRoomView.as_view(), name='create_group_room'),
    path('groups/room/<str:room_code>/', group_room_detail, name='group_room_detail'),
    path('groups/join/', JoinGroupRoomView.as_view(), name='join_group_room'),
    path('groups/room/<str:room_code>/leave/', LeaveRoomView.as_view(), name='leave_room'),
]