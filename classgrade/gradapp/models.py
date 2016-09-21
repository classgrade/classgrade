from django.db import models
from django.contrib.auth.models import User


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
    :param description: assigment description
    :param nb_graders: number of graders
    :param file_type: file type that can be submitted (e.g. ipynb)
    :param deadline_submission: submission deadline
    :param deadline_grading: grading deadline

    :type description: TextField(max_length=500)
    :type nb_graders: TextField(max_length=500)
    :type file_type: TextField(max_length=500)
    :type deadline_submission: TextField(max_length=500)
    :type deadline_grading: TextField(max_length=500)
    """
    title = models.CharField(max_length=100, default='')
    description = models.TextField(max_length=500)
    nb_graders = models.IntegerField(default=3)
    file_type = models.CharField(max_length=20, default='ipynb')
    deadline_submission = models.DateTimeField()
    deadline_grading = models.DateTimeField()
    prof = models.ForeignKey(Prof)
    list_students = models.FileField(max_length=100, null=True, blank=True,
                                     help_text='csv file, each row contains'
                                               'first_name, last_name, email')

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
    document = models.FileField(max_length=100, null=True, blank=True)
    date_upload = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Assignment(id {}, type {},  student {})'.\
            format(self.id, self.assignmentype.id, self.student.user.username)


class Evalassignment(models.Model):
    """
    :param assignment: evaluated assignment
    :param student: student evaluating the assignment
    :grade_assignment: grade given by the evaluator
    :grade_evaluation: grade given to the evaluator

    :type assignment: ForeignKey(Assignment, on_delete=models.CASCADE)
    :type evaluator: ForeignKey(Student, on_delete=models.CASCADE)
    :type grade_assignment: FloatField(null=True, blank=True)
    :type grade_evaluation: FloatField(null=True, blank=True)
    """
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    evaluator = models.ForeignKey(Student, on_delete=models.CASCADE)
    grade_assignment = models.FloatField(null=True, blank=True)
    grade_evaluation = models.FloatField(null=True, blank=True)

    def __str__(self):
        return 'Evalassignment(id {}, assignment {},  evaluator {})'.\
            format(self.id, self.assignment.id, self.evaluator.user.username)
