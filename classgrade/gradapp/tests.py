import pandas as pd
from unidecode import unidecode
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from gradapp.models import Student, Prof, Assignmentype, Assignment


file_students = 'test_files/list_students.csv'
list_students = pd.read_csv(file_students, header=None)
username_test_student = '%s_%s' % (list_students.values[0],
                                   list_students.values[1])
pwd_test_student = 'top_secret'
test_assignment_title = 'Test'
username_prof = 'super_prof'
pwd_prof = 'tip_top'


def create_assignmentype(prof, title=test_assignment_title, description='test',
                         nb_grading=2,
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


class ProfViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create prof and log in
        cls.user_prof = User.objects.create_user(
            username=username_prof, email='prof@toto.com', password=pwd_prof)
        cls.prof = Prof.objects.create(user=cls.user_prof)
        cls.assignmentype = create_assignmentype(cls.prof,
                                                 title=test_assignment_title)

    def setUp(self):
        self.client.login(username=username_prof, password=pwd_prof)

    def test_create_assignmentype(self):
        test_title = 'test create'
        with open(file_students) as fs:
            dict_post = {'title': test_title, 'description': 'test',
                         'nb_grading': 2, 'nb_questions': 3,
                         'file_type': 'ipynb',
                         'deadline_submission': '2020-02-02 22:59:30',
                         'deadline_grading': '2020-02-12 22:59:30',
                         'list_students': fs}
            response = self.client.post(reverse('gradapp:create_assignmentype'),
                                        dict_post)
        # Check it is redirected to validate_assignmentype_students
        self.assertEqual(response.status_code, 302)
        # Send validation to create students
        self.client.get(reverse('gradapp:create_assignmentype_students'))
        # Check Assignmentype has been created
        assignmentype = Assignmentype.objects.\
            filter(title=test_title).first()
        self.assertIsNotNone(assignmentype)
        # Check students and their assignments are created
        list_students = pd.read_csv(file_students, header=None)
        for student in list_students.values:
            row = [unidecode(x.strip()) for x in student[:3]]
            username_student = "_".join(row[:2])
            username_student = username_student.replace(" ", "_")
            u_st = User.objects.filter(username=username_student).first()
            self.assertIsNotNone(u_st)
            self.assertTrue(hasattr(u_st, 'student'))
            assignment = Assignment.objects.filter(
                assignmentype=assignmentype,
                student = u_st.student).first()
            self.assertIsNotNone(assignment)


    def test_insert_question(self):
        for cd in [-1, 1]:
            assignmentype = Assignmentype.objects.get(id=self.assignmentype.id)
            nb_questions = assignmentype.nb_questions
            response = self.client.post(
                '/insert_question_assignmentype/%s/%s/' %
                (self.assignmentype.id, cd), {'question': 1})
            self.assertEqual(response.status_code, 302)
            assignmentype = Assignmentype.objects.get(id=self.assignmentype.id)
            self.assertEqual(nb_questions + cd, assignmentype.nb_questions)


    # TODO: test coeff

class StudentViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create student and log in
        cls.user = User.objects.create_user(
            username=username_test_student, email='ya@toto.com',
            password=pwd_test_student)
        cls.student = Student.objects.create(user=cls.user)
        # Create prof and create an assignment
        u_prof = User.objects.create_user(
            username=username_prof, email='tata@...', password=pwd_prof)
        cls.prof = Prof.objects.create(user=u_prof)
        cls.assignmentype = create_assignmentype(cls.prof)

    def setUp(self):
        self.client.login(username=username_test_student,
                          password=pwd_test_student)

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

    # TODO: test submit, grade, get eval
