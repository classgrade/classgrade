from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from gradapp.models import Student, Prof, Assignmentype


def create_assignmentype(prof, title='Test', description='test',  nb_grading=3,
                         deadline_submission='2020-02-02 22:59:30+00:00',
                         deadline_grading='2020-02-12 22:59:30+00:00',
                         nb_questions=3, questions_coeff=[2, 1, 1],
                         list_students='test_files/list_students.csv'):
    return Assignmentype.objects.create(
        prof=prof, title=title, description=description,
        nb_grading=nb_grading, deadline_submission=deadline_submission,
        deadline_grading=deadline_grading, nb_questions=nb_questions,
        questions_coeff=questions_coeff, list_students=list_students)

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


class StudentViewTests(TestCase):

    def setUp(self):
        # Create student and log in
        self.user = User.objects.create_user(
            username='babar_ya', email='ya@toto.com', password='top_secret')
        self.student = Student.objects.create(user=self.user)
        self.client.login(username='babar_ya', password='top_secret')
        # Create prod and create an assignment
        u_prof = User.objects.create_user(
            username='tata', email='tata@...', password='tip_secret')
        self.prof = Prof.objects.create(user=u_prof)
        self.assignmentype = create_assignmentype(self.prof)

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
        a_id = self.assignmentype.id
        list_prof_views = ['list_assignmentypes_running/',
                           'list_assignmentypes_archived/',
                           'detail_assignmentype/%s/' % a_id,
                           'show_eval_distrib/%s/' % a_id,
                           'csv_grades/%s/' % a_id,
                           'zip_assignments/%s/' % a_id,
                           'create_assignmentype/',
                           'archive_assignmentype/%s/' % a_id,
                           'delete_assignmentype/%s/1/' % a_id,
                           'reset_assignmentype/%s/' % a_id,
                           'modify_assignmentype/%s/' % a_id,
                           'coeff_assignmentype/%s/' % a_id,
                           'insert_question_assignmentype/%s/1/' % a_id,
                           'validate_assignmentype_students/',
                           'create_assignmentype_students/',
                           'supereval_assignment/%s/' % a_id]
        for prof_view in list_prof_views:
            print(prof_view)
            response = self.client.get(('/%s' % prof_view))
            self.assertEqual(response.status_code, 302)

