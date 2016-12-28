from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from gradapp.models import Student  #, Prof


class LoginViewTests(TestCase):

    def test_user_do_not_exist(self):
        response = self.client.post('/accounts/login/',
                                    {'username': 'john', 'password': 'smith'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Try again!')

    def test_user_exist(self):
        User.objects.create_user('toto', 'toto@zero.com', 'totopassword')
        response = self.client.post('/accounts/login/',
                                    {'username': 'toto',
                                     'password': 'totopassword'})
        self.assertEqual(response.status_code, 302)  # 302: redirection


class DashboardStudentViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='toto', email='toto@...', password='top_secret')
        self.student = Student.objects.create(user=self.user)
        self.client.login(username='toto', password='top_secret')


    def test_dashboard_student_view(self):
        """
        No error when getting the page if student
        """
        response = self.client.get(reverse('gradapp:dashboard_student'))
        self.assertEqual(response.status_code, 200)


    def test_no_access_prof_view(self):
        """
        No access for a student to pages for professors
        """
        list_prof_views = ['list_assignmentypes_running',
                           'list_assignmentypes_archived']
#                           'detail_assignmentype', 'show_eval_distrib',
#                           'generate_csv_grades', 'generate_zip_assignments',
#                           'create_assignmentype', 'archive_assignmentype',
#                           'delete_assignmentype', 'reset_assignmentype',
#                           'modify_assignmentype', 'coeff_assignmentype',
#                           'insert_question', 'validate_assignmentype_students',
#                           'create_assignmentype_students',
#                           'supereval_assignment']
        for prof_view in list_prof_views:
            response = self.client.get(reverse('gradapp:%s' % prof_view))
            self.assertEqual(response.status_code, 302)

