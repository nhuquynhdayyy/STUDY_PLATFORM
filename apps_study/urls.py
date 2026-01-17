from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import DashboardView, StartStudyAction, StopStudyAction, CreateSubjectView, HistoryListView, RegisterView, SubjectListView, SubjectCreateView

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
]