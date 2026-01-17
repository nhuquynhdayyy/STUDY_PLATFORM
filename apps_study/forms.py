# apps_study/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Subject

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-5 py-3 rounded-xl bg-slate-50 border-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ví dụ: Lập trình Python, Tiếng Anh...'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'w-full h-12 p-1 rounded-xl bg-slate-50 border-none cursor-pointer'
            }),
        }