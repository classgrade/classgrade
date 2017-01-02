from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import django.contrib.postgres.fields as pgfields


def assignment_directory_path(instance, filename):
    """Used in FileField option upload_to, to upload the file to
    MEDIA_ROOT/assignment_<assignmentype_id>/<filename>
    """
    new_filename = 'assignment_1024{0}42.{1}'.format(instance.id,
                                                     filename.split('.')[-1])
    return 'assignment_{0}/{1}'.format(instance.assignmentype.id, new_filename)


class Prof(models.Model):
    """
    :param user: associated django user

    :type user: django.contrib.auth.models.User
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return 'Prof(id {}, name {}, email {})'.format(self.id,
                                                       self.user.username,
                                                       self.user.email)


class Student(models.Model):
    """
    :param user: associated django user

    :type user: django.contrib.auth.models.User
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return 'Student(id {}, name {}, email {})'.format(self.id,
                                                          self.user.username,
                                                          self.user.email)


class Assignmentype(models.Model):
    """
    :param title: assignment title
    :param description: assignment description
    :param nb_grading: number of graders
    :param nb_questions: number of questions in assignment
    :param questions_coeff: coefficient of each question
    :param file_type: file type that can be submitted (e.g. ipynb)
    :param deadline_submission: submission deadline
    :param deadline_grading: grading deadline
    :param prof: prof creating the assignment
    :param list_students: csv with student list (first_name, last_name, email)
    :param archived: if assignment is running or archived

    :type title: CharField(max_length=100)
    :type description: TextField(max_length=500)
    :type nb_graders: IntegerField(default=3)
    :type nb_questions: IntegerField(default=1)
    :type questions_coeff: pgfields.ArrayField(models.FloatField(default=1))
    :type file_type: CharField(max_length=20)
    :type deadline_submission: TextField(max_length=500)
    :type deadline_grading: TextField(max_length=500)
    :type prof: ForeignKey(Prof)
    :type list_students: FileField(max_length=100, null=True, blank=True)
    :type archived: BooleanField(default=False)
    """
    title = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=500,
                                   help_text='Use Markdown')
    nb_grading = models.IntegerField(default=3, help_text='nb of files '
                                     'evaluated by each student')
    file_type = models.CharField(max_length=20, default='ipynb')
    deadline_submission = models.DateTimeField(help_text='DD/MM/YY')
    deadline_grading = models.DateTimeField(help_text='DD/MM/YY')
    nb_questions = models.IntegerField(default=1, help_text='nb of questions '
                                       'in your assignment')
    questions_coeff = pgfields.ArrayField(models.FloatField(default=1),
                                          default=list)
    prof = models.ForeignKey(Prof)
    list_students = models.FileField(max_length=100, null=True, blank=True,
                                     help_text='csv file, each row contains: '
                                               'first_name, last_name, email')
    archived = models.BooleanField(default=False)

    def __str__(self):
        return 'AssignmentType(id {}, prof {}, description {})'.\
            format(self.id, self.prof.user.username, self.description)


class Assignment(models.Model):
    """
    :param assignmentype: associated type of assignment
    :param student: student writing the assignment
    :param document: assignment file uploaded by the student
    :param date_upload: upload time of assignment file

    :type assignmentype: ForeignKey(Assignmentype, on_delete=models.CASCADE)
    :type student: ForeignKey(Student, on_delete=models.CASCADE)
    :type document: FileField(max_length=100, null=True, blank=True)
    :type date_upload: DateTimeField(auto_now=True)
    """
    assignmentype = models.ForeignKey(Assignmentype, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    document = models.FileField(max_length=100, null=True, blank=True,
                                upload_to=assignment_directory_path)
    date_upload = models.DateTimeField(auto_now=True)

    def get_normal_eval(self):
        return self.evalassignment_set.filter(is_supereval=False)

    def get_super_eval(self):
        return self.evalassignment_set.filter(is_supereval=True).first()

    def __str__(self):
        return 'Assignment(id {}, type {},  student {})'.\
            format(self.id, self.assignmentype.id, self.student.user.username)


class Evalassignment(models.Model):
    """
    :param assignment: evaluated assignment
    :param evaluator: student evaluating the assignment
    :param grade_assignment: combination of grades given by the evaluator
    :param grade_evaluation: grade given to the evaluator
    :param grade_assignment_comments: general comments given by the evaluator
    :param grade_evaluation_comments: comments given to the evaluator
    :param is_questions_graded: True if all evalquestion.grade are set
    :param is_supereval: True if evaluation is made by a Prof

    :type assignment: ForeignKey(Assignment, on_delete=models.CASCADE)
    :type evaluator: ForeignKey(Student, on_delete=models.CASCADE)
    :type grade_assignment: FloatField(null=True, blank=True, min=0, max=20)
    :type grade_evaluation: IntegerField(null=True, blank=True, min=-1, max=1)
    :type grade_assignment_comments: TextField(max_length=500, default='')
    :type grade_evaluation_comments: TextField(max_length=300, default='')
    :type is_questions_graded: BooleanField(default=False)
    :type is_supereval: BooleanField(default=False)
    """
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE)
    grade_assignment = models.FloatField(null=True, blank=True, help_text='/20',
                                         validators=[MaxValueValidator(20),
                                                     MinValueValidator(0)])
    grade_assignment_comments = models.TextField(max_length=500, default='',
                                                 blank=True)
    grade_evaluation = models.IntegerField(default=0,
                                           validators=[MaxValueValidator(1),
                                                       MinValueValidator(-1)])
    grade_evaluation_comments = models.TextField(max_length=300, default='',
                                                 blank=True)

    is_questions_graded = models.BooleanField(default=False)
    is_supereval = models.BooleanField(default=False)

    def reset_grade(self):
        self.grade_assignment = None
        self.grade_evaluation = 0
        self.is_questions_graded = False

    def order_question_set(self):
        return self.evalquestion_set.all().order_by('question')

    def __str__(self):
        return 'Evalassignment(id {}, assignment {},  evaluator {})'.\
            format(self.id, self.assignment.id, self.evaluator.username)


class Evalquestion(models.Model):
    """
    :param evalassignment: related evaluation
    :param question: related question
    :param grade: grade for the question
    :param comments: comments for the question

    :type evalassignment: ForeignKey(Evalassignment, on_delete=models.CASCADE)
    :type question: IntegerField
    :type grade: IntegerField(null=True, blank=True, min=0, max=2)
    :type comments: TextField(max_length=500, default='', blank=True)
    """
    evalassignment = models.ForeignKey(Evalassignment,
                                       on_delete=models.CASCADE)
    question = models.IntegerField()
    grade = models.IntegerField(null=True, blank=True, help_text='0, 1, or 2',
                                validators=[MinValueValidator(0),
                                            MaxValueValidator(2)])
    comments = models.TextField(max_length=500, default='', blank=True,
                                help_text='Use Markdown')

    def __str__(self):
        return 'Evalquest(id {}, evalassign {}, assign {},  evaluator {})'.\
            format(self.id, self.evalassignment.id,
                   self.evalassignment.assignment.id,
                   self.evalassignment.evaluator.user.username)
