# apps_study/tests.py
from django.test import TestCase
from .models import User, Subject
from .services import StudyService

class StudyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.subject = Subject.objects.create(user=self.user, name="Math")

    def test_start_session(self):
        session = StudyService.start_session(self.user, self.subject.id)
        self.assertEqual(session.status, 'active')
        
        # Test không cho phép 2 session active
        with self.assertRaises(Exception):
            StudyService.start_session(self.user, self.subject.id)